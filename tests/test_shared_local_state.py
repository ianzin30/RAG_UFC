import importlib
import json
from pathlib import Path


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


def test_collection_discovery_reads_shared_global_root(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    collections = importlib.import_module("presentation.sidebar.Collections")
    monkeypatch.setattr(collections, "PROJECT_ROOT", tmp_path)
    collection_path = tmp_path / "data" / "collections" / "shared_rag"
    collection_path.mkdir(parents=True)
    (collection_path / "02_documento.md").write_text("# Documento\n\ntexto", encoding="utf-8")

    assert collections.list_collection_documents(user_id="ignored") == [
        {
            "collection": "shared_rag",
            "file_name": "02_documento.md",
            "label": "documento",
        }
    ]
