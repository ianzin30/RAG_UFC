import importlib
import json
from pathlib import Path
import sys
import types


APPLICATION_DIR = Path(__file__).resolve().parents[1] / "application"


class FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class FakeStreamlit:
    def __init__(self):
        self.session_state = FakeSessionState()


def test_shared_chat_sessions_persist_to_local_json_without_active_chat(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    storage = importlib.import_module("presentation.chat_sessions.Storage")
    fake_st = FakeStreamlit()
    fake_st.session_state["active_chat_id"] = "chat_2"
    fake_st.session_state["next_chat_session_id"] = 3
    monkeypatch.setattr(storage, "st", fake_st)
    monkeypatch.setattr(storage, "CHAT_STORAGE_PATH", tmp_path / "local_chat_sessions.json")

    sessions = [
        {
            "id": "chat_1",
            "title": "Benchmark chat",
            "collection": ["google_drive_rag"],
            "model_name": "phi4:latest",
            "messages": [{"role": "user", "content": "Pergunta"}],
        }
    ]
    storage.persist_chat_state(lambda: sessions, user_id="ignored-user")

    payload = json.loads((tmp_path / "local_chat_sessions.json").read_text(encoding="utf-8"))
    assert payload == {
        "chat_sessions": sessions,
        "next_chat_session_id": 3,
    }
    assert "active_chat_id" not in payload
    assert storage.load_persisted_chat_state(user_id="another-ignored-user") == payload


def test_activate_chat_marks_selected_chat_newest_without_touching_previous(monkeypatch):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    operations = importlib.import_module("presentation.chat_sessions.Operations")
    state = importlib.import_module("presentation.chat_sessions.State")
    fake_st = FakeStreamlit()
    fake_st.session_state.update(
        {
            "active_chat_id": "chat_1",
            "messages": [{"role": "user", "content": "old active"}],
            "collection": ["uploaded_files"],
            "model_name": "phi4:latest",
            "chat_sessions": [
                {
                    "id": "chat_1",
                    "title": "Old active",
                    "collection": ["uploaded_files"],
                    "model_name": "phi4:latest",
                    "messages": [],
                    "created_at": "2026-05-13T09:00:00+00:00",
                    "updated_at": "2026-05-13T09:00:00+00:00",
                },
                {
                    "id": "chat_2",
                    "title": "Clicked chat",
                    "collection": ["uploaded_files"],
                    "model_name": "phi4:latest",
                    "messages": [{"role": "user", "content": "clicked"}],
                    "created_at": "2026-05-13T08:00:00+00:00",
                    "updated_at": "2026-05-13T08:00:00+00:00",
                },
            ],
        }
    )

    monkeypatch.setattr(state, "st", fake_st)
    monkeypatch.setattr(operations, "st", fake_st)
    monkeypatch.setattr(state, "persist_chat_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(operations, "persist_chat_state", lambda *args, **kwargs: None)

    operations.activate_chat("chat_2")

    sessions = fake_st.session_state["chat_sessions"]
    assert fake_st.session_state["active_chat_id"] == "chat_2"
    assert sessions[0]["id"] == "chat_2"
    assert sessions[1]["id"] == "chat_1"
    assert sessions[1]["updated_at"] == "2026-05-13T09:00:00+00:00"
    assert sessions[0]["updated_at"] != "2026-05-13T08:00:00+00:00"


def test_upload_service_uses_shared_collections_root(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    uploads = importlib.import_module("service.LocalUploads")

    class FakeDriveService:
        def __init__(self):
            self.collections_root = tmp_path / "data" / "collections"

        def _safe_filename(self, value):
            return value

    class FakeUploadedFile:
        name = "notes.txt"

        def getvalue(self):
            return b"shared benchmark text"

    monkeypatch.setattr(uploads, "GoogleDriveService", FakeDriveService)

    service = uploads.LocalUploadService()
    result = service.ingest_uploaded_files([FakeUploadedFile()])

    output_path = Path(result["files"][0]["output_path"])
    assert output_path == tmp_path / "data" / "collections" / "uploaded_files" / "01_notes.md"
    assert output_path.exists()
    assert "shared benchmark text" in output_path.read_text(encoding="utf-8")


def test_upload_service_emits_progress_for_saved_files(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    uploads = importlib.import_module("service.LocalUploads")

    class FakeDriveService:
        def __init__(self):
            self.collections_root = tmp_path / "data" / "collections"

        def _safe_filename(self, value):
            return value

    class FakeUploadedFile:
        name = "notes.txt"

        def getvalue(self):
            return b"shared benchmark text"

    monkeypatch.setattr(uploads, "GoogleDriveService", FakeDriveService)
    progress = []

    service = uploads.LocalUploadService()
    result = service.ingest_uploaded_files([FakeUploadedFile()], progress_callback=progress.append)

    assert result["files"][0]["name"] == "notes.txt"
    assert [item["status"] for item in progress] == ["queued", "extracting", "saved", "completed"]
    assert progress[-1]["processed"] == 1
    assert progress[-1]["saved"] == 1
    assert progress[-1]["skipped"] == 0


def test_upload_service_emits_skipped_progress_with_reason(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    uploads = importlib.import_module("service.LocalUploads")

    class FakeDriveService:
        def __init__(self):
            self.collections_root = tmp_path / "data" / "collections"

    class EmptyUploadedFile:
        name = "empty.txt"

        def getvalue(self):
            return b""

    monkeypatch.setattr(uploads, "GoogleDriveService", FakeDriveService)
    progress = []

    service = uploads.LocalUploadService()
    try:
        service.ingest_uploaded_files([EmptyUploadedFile()], progress_callback=progress.append)
    except RuntimeError:
        pass

    assert [item["status"] for item in progress] == ["queued", "skipped", "error"]
    assert progress[1]["file_name"] == "empty.txt"
    assert progress[1]["reason"] == "empty file"
    assert progress[-1]["skipped"] == 1


def test_upload_progress_helpers_describe_processing(monkeypatch):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    sidebar_uploads = importlib.import_module("presentation.sidebar.Uploads")

    title, subtitle = sidebar_uploads._format_upload_progress(
        {
            "status": "extracting",
            "processed": 2,
            "total": 6,
            "saved": 2,
            "skipped": 0,
            "file_name": "Ata.pdf",
        }
    )

    assert title == "Extraindo texto de Ata.pdf"
    assert subtitle == "2/6 arquivos processados. 2 salvo(s), 0 ignorado(s)."
    assert sidebar_uploads._upload_progress_percent({"processed": 2, "total": 6}) == 33


def test_drag_only_ui_hides_visible_drive_entrypoints():
    chat_source = (APPLICATION_DIR / "presentation" / "chat" / "Chat.py").read_text(encoding="utf-8")
    files_source = (APPLICATION_DIR / "presentation" / "sidebar" / "FilesPanel.py").read_text(encoding="utf-8")
    upload_source = (APPLICATION_DIR / "presentation" / "sidebar" / "Uploads.py").read_text(encoding="utf-8")

    visible_source = "\n".join([chat_source, files_source])
    assert "Conectar ao Google Drive" not in visible_source
    assert "Reimportar pasta RAG" not in visible_source
    assert "Desconectar" not in visible_source
    assert "render_connect_button" not in visible_source
    assert "Loading files" not in upload_source
    assert "Extraindo texto" in upload_source


def test_google_drive_backend_still_imports(monkeypatch):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    drive_integration = importlib.import_module("presentation.integrations.GoogleDrive")
    drive_service = importlib.import_module("service.GoogleDrive")

    assert hasattr(drive_integration, "render_connect_button")
    assert hasattr(drive_service, "GoogleDriveService")


def test_collection_discovery_reads_shared_global_root(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    collections = importlib.import_module("presentation.sidebar.Collections")
    monkeypatch.setattr(collections, "PROJECT_ROOT", tmp_path)
    collections_root = tmp_path / "data" / "collections"
    upload_path = collections_root / "uploaded_files"
    drive_path = collections_root / "google_drive_rag"
    upload_path.mkdir(parents=True)
    drive_path.mkdir(parents=True)
    (collections_root / "01_root.md").write_text("# Root\n\ntexto", encoding="utf-8")
    (upload_path / "02_uploaded.md").write_text("# Uploaded\n\ntexto", encoding="utf-8")
    (drive_path / "03_drive.md").write_text("# Drive\n\ntexto", encoding="utf-8")

    assert collections.list_collection_documents(user_id="ignored") == [
        {
            "collection": "uploaded_files",
            "file_name": "01_root.md",
            "relative_path": "01_root.md",
            "label": "root",
        },
        {
            "collection": "uploaded_files",
            "file_name": "03_drive.md",
            "relative_path": "google_drive_rag/03_drive.md",
            "label": "drive",
        },
        {
            "collection": "uploaded_files",
            "file_name": "02_uploaded.md",
            "relative_path": "uploaded_files/02_uploaded.md",
            "label": "uploaded",
        },
    ]
    assert collections.list_available_collections(collections.list_collection_documents()) == ["uploaded_files"]
    assert collections.format_collection_label("uploaded_files") == "Uploaded files"


def test_upload_service_appends_files_until_deleted(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    uploads = importlib.import_module("service.LocalUploads")

    class FakeDriveService:
        def __init__(self):
            self.collections_root = tmp_path / "data" / "collections"

        def _safe_filename(self, value):
            return value

    class FakeUploadedFile:
        name = "notes.txt"

        def __init__(self, content):
            self.content = content

        def getvalue(self):
            return self.content

    monkeypatch.setattr(uploads, "GoogleDriveService", FakeDriveService)

    service = uploads.LocalUploadService()
    first = service.ingest_uploaded_files([FakeUploadedFile(b"first text")])
    second = service.ingest_uploaded_files([FakeUploadedFile(b"second text")])

    first_path = Path(first["files"][0]["output_path"])
    second_path = Path(second["files"][0]["output_path"])
    assert first_path.name == "01_notes.md"
    assert second_path.name == "02_notes.md"
    assert first_path.exists()
    assert second_path.exists()


def test_files_panel_has_delete_only_file_rows():
    source = (APPLICATION_DIR / "presentation" / "sidebar" / "FilesPanel.py").read_text(encoding="utf-8")

    assert "toggle_collection" not in source
    assert "is_collection_selected" not in source
    assert "Excluir" in source
    assert "file-row-preview-link" in source
    assert 'close_href="#sidebar-files-panel"' in source
    assert "st.button(\n                        document[\"label\"]" not in source


def test_markdown_preview_resolves_only_safe_markdown(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    preview = importlib.import_module("presentation.shared.MarkdownPreview")
    monkeypatch.setattr(preview, "PROJECT_ROOT", tmp_path)

    collections_root = tmp_path / "data" / "collections"
    collection_path = collections_root / "uploaded_files"
    collection_path.mkdir(parents=True)
    markdown_path = collection_path / "01_notes.md"
    markdown_path.write_text("# Notes\n\nBody", encoding="utf-8")
    (tmp_path / "secret.md").write_text("# Secret", encoding="utf-8")
    (collection_path / "notes.txt").write_text("not markdown", encoding="utf-8")

    assert preview.resolve_markdown_preview_path({"relative_path": "uploaded_files/01_notes.md"}) == markdown_path
    assert preview.resolve_markdown_preview_path({"relative_path": "../secret.md"}) is None
    assert preview.resolve_markdown_preview_path({"relative_path": "uploaded_files/notes.txt"}) is None


def test_markdown_preview_link_renders_anchor_and_modal(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    preview = importlib.import_module("presentation.shared.MarkdownPreview")
    monkeypatch.setattr(preview, "PROJECT_ROOT", tmp_path)

    markdown_path = tmp_path / "data" / "collections" / "uploaded_files" / "01_notes.md"
    markdown_path.parent.mkdir(parents=True)
    markdown_path.write_text("# Notes\n\n**Body**", encoding="utf-8")

    html = preview.render_markdown_preview_link(
        label="Notes",
        document={"relative_path": "uploaded_files/01_notes.md"},
        prefix="test",
    )

    assert 'href="#markdown-preview-test-' in html
    assert 'href="#markdown-preview-closed"' in html
    assert 'class="markdown-preview-modal"' in html
    assert "<h1>Notes</h1>" in html
    assert "<strong>Body</strong>" in html
    assert "\n    <a" not in html
    assert "\n    <div" not in html


def test_render_sources_uses_clickable_preview_links():
    source = (APPLICATION_DIR / "presentation" / "chat" / "Chat.py").read_text(encoding="utf-8")

    assert "source-preview-title" in source
    assert "render_markdown_preview_link" in source
    assert "source_row =" in source
    assert "Fontes:" in source


def test_files_panel_does_not_render_chat_action_popover():
    chat_history_source = (APPLICATION_DIR / "presentation" / "sidebar" / "ChatHistory.py").read_text(
        encoding="utf-8"
    )
    chat_source = (APPLICATION_DIR / "presentation" / "chat" / "Chat.py").read_text(encoding="utf-8")

    assert "st.popover" not in chat_history_source
    assert "Renomear chat" not in chat_history_source
    assert "delete_chat_" in chat_history_source
    assert "Trabalhando..." not in chat_source
    assert "format_collection_progress_label" in chat_source


def test_sidebar_tabs_are_hash_links_without_streamlit_nav_buttons():
    nav_source = (APPLICATION_DIR / "presentation" / "nav_rail" / "Navigation.py").read_text(encoding="utf-8")
    sidebar_source = (APPLICATION_DIR / "presentation" / "sidebar" / "Sidebar.py").read_text(encoding="utf-8")
    constants_source = (APPLICATION_DIR / "presentation" / "chat_sessions" / "Constants.py").read_text(
        encoding="utf-8"
    )
    css_source = (APPLICATION_DIR / "assets" / "app.css").read_text(encoding="utf-8")

    assert "st.button" not in nav_source
    assert "#sidebar-chat-panel" in nav_source
    assert "#sidebar-files-panel" in nav_source
    assert "sidebar_chat_panel_view" in sidebar_source
    assert "sidebar_files_panel_view" in sidebar_source
    assert ".st-key-sidebar_files_panel_view .markdown-preview-modal:target" in css_source
    assert "MAX_CHAT_SESSIONS = 6" in constants_source


def test_uploaded_files_rag_collection_enumerates_all_markdown(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    loaders_module = types.ModuleType("langchain_community.document_loaders")
    loaders_module.DirectoryLoader = object
    loaders_module.TextLoader = object
    vectorstores_module = types.ModuleType("langchain_community.vectorstores")
    vectorstores_module.FAISS = object
    monkeypatch.setitem(sys.modules, "langchain_community", types.ModuleType("langchain_community"))
    monkeypatch.setitem(sys.modules, "langchain_community.document_loaders", loaders_module)
    monkeypatch.setitem(sys.modules, "langchain_community.vectorstores", vectorstores_module)
    loading = importlib.import_module("service.rag.parts.CollectionLoading")
    cache = importlib.import_module("service.rag.Cache")

    class Harness(loading.RAGServiceCollectionLoadingMixin):
        pass

    collections_root = tmp_path / "data" / "collections"
    upload_path = collections_root / "uploaded_files"
    legacy_path = collections_root / "google_drive_rag"
    upload_path.mkdir(parents=True)
    legacy_path.mkdir(parents=True)
    (upload_path / "01_uploaded.md").write_text("# Uploaded\n\ntexto", encoding="utf-8")
    legacy_file = legacy_path / "02_legacy.md"
    legacy_file.write_text("# Legacy\n\ntexto", encoding="utf-8")

    harness = Harness()
    harness.collections_root = collections_root

    before = harness._enumerate_collection_markdown_files(["uploaded_files"])
    before_fingerprint = cache.build_rag_index_fingerprint(
        {"files": before, "selected_collections": ["uploaded_files"]}
    )
    legacy_file.unlink()
    after = harness._enumerate_collection_markdown_files(["uploaded_files"])
    after_fingerprint = cache.build_rag_index_fingerprint(
        {"files": after, "selected_collections": ["uploaded_files"]}
    )

    assert [item["relative_path"] for item in before] == [
        "google_drive_rag/02_legacy.md",
        "uploaded_files/01_uploaded.md",
    ]
    assert [item["relative_path"] for item in after] == ["uploaded_files/01_uploaded.md"]
    assert before_fingerprint != after_fingerprint


def test_chat_source_normalization_preserves_preview_paths(monkeypatch):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    normalization = importlib.import_module("presentation.chat_sessions.Normalization")

    messages = normalization.coerce_messages(
        [
            {
                "role": "assistant",
                "content": "Resposta",
                "route": "retrieval",
                "sources": [
                    {
                        "document_name": "fortal.pdf",
                        "chunk_kind": "text",
                        "excerpt": "Trecho",
                        "source": "data/collections/uploaded_files/01_fortal.md",
                        "source_name": "01_fortal.md",
                        "relative_path": "uploaded_files/01_fortal.md",
                    }
                ],
            }
        ]
    )

    assert messages[0]["sources"][0]["source"] == "data/collections/uploaded_files/01_fortal.md"
    assert messages[0]["sources"][0]["source_name"] == "01_fortal.md"
    assert messages[0]["sources"][0]["relative_path"] == "uploaded_files/01_fortal.md"
