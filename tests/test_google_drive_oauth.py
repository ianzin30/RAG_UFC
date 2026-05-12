import json
from contextlib import contextmanager
import importlib
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from application.service.google_drive import Auth


APPLICATION_DIR = Path(__file__).resolve().parents[1] / "application"


WEB_CLIENT_CONFIG = {
    "web": {
        "client_id": "client-id.apps.googleusercontent.com",
        "project_id": "rag-ufc",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "client-secret",
        "redirect_uris": ["https://rag.example.com/"],
    }
}


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_authorization_request_includes_redirect_state_and_pkce(tmp_path):
    credentials_file = _write_json(tmp_path / "web-client.json", WEB_CLIENT_CONFIG)

    request = Auth.build_google_drive_authorization_request(
        credentials_file,
        "https://rag.example.com/",
        "state-123",
    )

    parsed = urlparse(request.authorization_url)
    query = parse_qs(parsed.query)
    assert parsed.netloc == "accounts.google.com"
    assert query["client_id"] == ["client-id.apps.googleusercontent.com"]
    assert query["redirect_uri"] == ["https://rag.example.com/"]
    assert query["state"] == ["state-123"]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent select_account"]
    assert query["scope"] == ["https://www.googleapis.com/auth/drive.readonly"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"]
    assert len(request.code_verifier) >= 43


def test_authorization_request_rejects_installed_client(tmp_path):
    credentials_file = _write_json(
        tmp_path / "installed-client.json",
        {"installed": {"client_id": "desktop-client", "client_secret": "secret"}},
    )

    with pytest.raises(Auth.GoogleDriveWebOAuthSetupError, match="desktop/installed OAuth client"):
        Auth.build_google_drive_authorization_request(
            credentials_file,
            "https://rag.example.com/",
            "state-123",
        )


def test_callback_flow_keeps_exact_code_verifier(monkeypatch, tmp_path):
    credentials_file = _write_json(tmp_path / "web-client.json", WEB_CLIENT_CONFIG)
    flow = Auth.build_auth_flow(
        credentials_file,
        "https://rag.example.com/",
        state="state-123",
        code_verifier="stored-verifier",
    )
    captured = {}

    def fake_fetch_token(self, **kwargs):
        captured["code"] = kwargs["code"]
        captured["code_verifier"] = self.code_verifier
        self.oauth2session.token = {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": "client-secret",
            "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
            "expires_at": 4_102_444_800,
        }

    monkeypatch.setattr(Auth.Flow, "fetch_token", fake_fetch_token)

    credentials = Auth.exchange_code_for_credentials(flow, "callback-code")

    assert captured == {
        "code": "callback-code",
        "code_verifier": "stored-verifier",
    }
    assert credentials.token == "access-token"
    assert credentials.refresh_token == "refresh-token"


def test_credentials_from_json_accepts_access_token_without_refresh_token():
    credentials = Auth.credentials_from_json(
        json.dumps(
            {
                "token": "access-token",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "client-id.apps.googleusercontent.com",
                "client_secret": "client-secret",
                "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
                "expiry": "2099-01-01T00:00:00Z",
            }
        )
    )

    assert credentials.token == "access-token"
    assert credentials.refresh_token is None
    assert credentials.valid


@pytest.fixture
def drive_integration(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(APPLICATION_DIR))
    module = importlib.import_module("presentation.integrations.GoogleDrive")
    monkeypatch.setattr(module, "OAUTH_STORE_DIR", tmp_path / "oauth")
    module._IMPORT_JOBS.clear()
    yield module
    module._IMPORT_JOBS.clear()


class FakeQueryParams(dict):
    def clear(self):
        super().clear()


class FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class RerunCalled(RuntimeError):
    pass


class FakeProgress:
    def __init__(self, parent, value):
        self.parent = parent
        self.parent.progress_values.append(value)


class FakeStreamlit:
    def __init__(self, query_params=None, session_state=None):
        self.query_params = FakeQueryParams(query_params or {})
        self.session_state = FakeSessionState(session_state or {})
        self.errors = []
        self.infos = []
        self.progress_values = []
        self.successes = []
        self.markdown_calls = []
        self.captions = []

    def error(self, message):
        self.errors.append(message)

    def info(self, message):
        self.infos.append(message)

    def success(self, message):
        self.successes.append(message)

    def markdown(self, message, **kwargs):
        self.markdown_calls.append((message, kwargs))

    def caption(self, message):
        self.captions.append(message)

    def progress(self, value):
        return FakeProgress(self, value)

    @contextmanager
    def spinner(self, _message):
        yield

    def rerun(self):
        raise RerunCalled()


class FakeCredentials:
    def to_json(self):
        return '{"token": "access-token"}'


class FakeDriveService:
    def __init__(self):
        self.completed = []
        self.collections_root = Path("shared-collections")

    def start_login(self):
        return (
            "https://accounts.google.com/o/oauth2/auth?state=expected&code_challenge=challenge&client_id=client",
            "expected",
            "verifier-123",
        )

    def complete_login(self, *, code, code_verifier, state):
        self.completed.append((code, code_verifier, state))
        return FakeCredentials()

    def credentials_from_json(self, raw_json):
        assert raw_json == '{"token": "access-token"}'
        return "credentials"

    def ingest_folder_to_collection(self, **kwargs):
        assert kwargs["folder_name"] == "rag"
        assert kwargs["collection_name"] == "google_drive_rag"
        assert kwargs["credentials"] == "credentials"
        progress_callback = kwargs.get("progress_callback")
        if progress_callback:
            progress_callback({"processed": 0, "total": 1, "status": "starting"})
            progress_callback(
                {
                    "processed": 1,
                    "total": 1,
                    "status": "processed",
                    "file_name": "doc.pdf",
                }
            )
        return {
            "collection_name": "google_drive_rag",
            "files": [{"name": "doc.pdf"}],
        }


def test_start_oauth_flow_persists_state_and_verifier_only(monkeypatch, drive_integration):
    fake_st = FakeStreamlit(
        session_state={
            "firebase_id_token": "legacy-token-that-should-not-be-persisted",
            "user": object(),
        },
    )
    monkeypatch.setattr(drive_integration, "st", fake_st)

    auth_url = drive_integration._start_oauth_flow(FakeDriveService())
    flow_record = drive_integration._read_oauth_flow("expected")

    assert auth_url.startswith("https://accounts.google.com/")
    assert flow_record["state"] == "expected"
    assert flow_record["code_verifier"] == "verifier-123"
    assert "firebase_id_token" not in flow_record
    assert "user_snapshot" not in flow_record


def test_oauth_return_rejects_state_mismatch_and_clears_query(monkeypatch, drive_integration):
    fake_st = FakeStreamlit(
        query_params={"code": "code-123", "state": "wrong"},
        session_state={
            "gdrive_status": "idle",
            drive_integration.OAUTH_STATE_KEY: "expected",
            drive_integration.OAUTH_CODE_VERIFIER_KEY: "verifier-123",
        },
    )
    monkeypatch.setattr(drive_integration, "st", fake_st)

    with pytest.raises(RerunCalled):
        drive_integration._handle_oauth_return(FakeDriveService())

    assert fake_st.query_params == {}
    assert fake_st.session_state.gdrive_status == "error"
    assert "Estado OAuth invalido" in fake_st.session_state.gdrive_error


def test_oauth_return_sets_importing_with_stored_code_verifier(monkeypatch, drive_integration):
    fake_st = FakeStreamlit(
        query_params={"code": "code-123", "state": "expected"},
        session_state={
            "gdrive_status": "idle",
            drive_integration.OAUTH_STATE_KEY: "expected",
            drive_integration.OAUTH_CODE_VERIFIER_KEY: "verifier-123",
            drive_integration.OAUTH_AUTH_URL_KEY: "https://accounts.google.com/o/oauth2/auth",
        },
    )
    service = FakeDriveService()
    monkeypatch.setattr(drive_integration, "st", fake_st)

    with pytest.raises(RerunCalled):
        drive_integration._handle_oauth_return(service)

    assert service.completed == [("code-123", "verifier-123", "expected")]
    assert fake_st.query_params == {}
    assert fake_st.session_state.gdrive_credentials_json == '{"token": "access-token"}'
    assert fake_st.session_state.gdrive_status == "importing"
    assert fake_st.session_state[drive_integration.OAUTH_CODE_VERIFIER_KEY] is None


def test_oauth_callback_uses_server_store_without_app_auth(monkeypatch, drive_integration):
    drive_integration._register_oauth_flow("expected", "stored-file-verifier")
    fake_st = FakeStreamlit(
        query_params={"code": "code-123", "state": "expected"},
        session_state={"gdrive_status": "idle"},
    )
    service = FakeDriveService()
    monkeypatch.setattr(drive_integration, "st", fake_st)

    with pytest.raises(RerunCalled):
        drive_integration.handle_google_drive_oauth_callback(service=service)

    assert service.completed == [("code-123", "stored-file-verifier", "expected")]
    assert drive_integration._read_oauth_flow("expected") is None
    assert fake_st.session_state.gdrive_status == "importing"


def test_same_tab_form_has_no_popup_or_new_tab(monkeypatch, drive_integration):
    fake_st = FakeStreamlit()
    monkeypatch.setattr(drive_integration, "st", fake_st)

    drive_integration._render_same_tab_auth_form(
        "https://accounts.google.com/o/oauth2/auth?state=abc&code_challenge=xyz&client_id=client",
        "Conectar ao Google Drive",
        None,
    )

    html = fake_st.markdown_calls[0][0]
    assert '<form method="get" target="_self"' in html
    assert 'target="_blank"' not in html
    assert "window.open" not in html
    assert 'name="state" value="abc"' in html
    assert 'name="code_challenge" value="xyz"' in html


def test_pending_import_reuses_background_job_on_rerun(monkeypatch, drive_integration):
    fake_st = FakeStreamlit(
        session_state={
            "gdrive_status": "importing",
            "gdrive_credentials_json": '{"token": "access-token"}',
            "collection": None,
        },
    )
    monkeypatch.setattr(drive_integration, "st", fake_st)
    started_roots = []

    def fake_start_import_job(credentials_json, collections_root):
        started_roots.append(collections_root)
        job = drive_integration.GoogleDriveImportJob(
            job_id="job-1",
            credentials_json=credentials_json,
            collections_root=str(collections_root),
        )
        job.update_progress(
            {
                "processed": 57,
                "total": 88,
                "status": "processing",
                "file_name": "Ata.pdf",
            }
        )
        drive_integration._register_import_job(job)
        return job

    monkeypatch.setattr(drive_integration, "_start_import_job", fake_start_import_job)

    assert drive_integration.run_pending_google_drive_import(FakeDriveService()) is True
    assert drive_integration.run_pending_google_drive_import(FakeDriveService()) is True

    assert len(started_roots) == 1
    assert fake_st.session_state.gdrive_import_job_id == "job-1"
    assert any("57/88 processados" in message for message in fake_st.infos)


def test_import_progress_formatting_explains_listing_phase(drive_integration):
    assert (
        drive_integration._format_import_progress(None)
        == "Conectando ao Google Drive e listando a pasta rag..."
    )
    job = drive_integration.GoogleDriveImportJob(
        job_id="job-listing",
        credentials_json="{}",
        collections_root="data/collections",
    )

    assert job.snapshot()["progress_status"] == "listing"
    assert (
        drive_integration._format_import_progress(job.snapshot())
        == "Conectando ao Google Drive e listando a pasta rag..."
    )


def test_import_progress_formatting_explains_cache_check(drive_integration):
    message = drive_integration._format_import_progress(
        {
            "status": "running",
            "progress_status": "queued",
            "checked": 57,
            "total": 88,
            "cached": 50,
            "new": 4,
            "changed": 3,
            "deleted": 2,
            "to_process": 7,
        }
    )

    assert message == (
        "Verificando cache... 57/88 verificados, 50 em cache, "
        "7 para importar, 2 removidos."
    )


def test_import_progress_formatting_explains_change_import(drive_integration):
    message = drive_integration._format_import_progress(
        {
            "status": "running",
            "progress_status": "processing",
            "processed": 7,
            "total": 88,
            "checked": 88,
            "cached": 67,
            "new": 5,
            "changed": 16,
            "to_process": 21,
            "file_name": "12-2020_Ata_de_Reuniao.pdf",
        }
    )

    assert message == (
        "Importando alteracoes... 7/21 processados, 67 em cache. "
        "Processando: 12-2020_Ata_de_Reuniao.pdf"
    )


def test_import_progress_formatting_explains_cache_only_completion(drive_integration):
    message = drive_integration._format_import_progress(
        {
            "status": "completed",
            "progress_status": "completed",
            "processed": 0,
            "total": 88,
            "checked": 88,
            "cached": 88,
            "to_process": 0,
        }
    )

    assert message == "Google Drive verificado. 88/88 arquivos em cache, nenhum arquivo alterado."


def test_import_progress_overall_percent_does_not_reset_between_phases(drive_integration):
    checking = drive_integration._overall_progress_percent(
        {
            "status": "running",
            "progress_status": "queued",
            "checked": 88,
            "total": 88,
            "cached": 67,
            "new": 5,
            "changed": 16,
            "to_process": 21,
        }
    )
    importing = drive_integration._overall_progress_percent(
        {
            "status": "running",
            "progress_status": "processing",
            "checked": 88,
            "total": 88,
            "cached": 67,
            "processed": 0,
            "new": 5,
            "changed": 16,
            "to_process": 21,
        }
    )

    assert checking > 0
    assert importing >= checking


def test_render_import_progress_shows_phase_details(monkeypatch, drive_integration):
    fake_st = FakeStreamlit()
    monkeypatch.setattr(drive_integration, "st", fake_st)

    drive_integration._render_import_progress(
        {
            "status": "running",
            "progress_status": "processing",
            "processed": 7,
            "total": 88,
            "checked": 88,
            "cached": 67,
            "new": 5,
            "changed": 16,
            "to_process": 21,
            "file_name": "doc.pdf",
        }
    )

    assert "Importando alteracoes... 7/21 processados" in fake_st.infos[0]
    assert any("Cache: 88/88 verificados" in message for message in fake_st.captions)
    assert any("Alteracoes: 7/21 processados" in message for message in fake_st.captions)
    assert len(fake_st.progress_values) == 3


def test_pending_import_completion_updates_session_and_reruns(monkeypatch, drive_integration):
    fake_st = FakeStreamlit(
        session_state={
            "gdrive_status": "importing",
            "gdrive_credentials_json": '{"token": "access-token"}',
            "collection": None,
        },
    )
    monkeypatch.setattr(drive_integration, "st", fake_st)
    job = drive_integration.GoogleDriveImportJob(
        job_id="job-complete",
        credentials_json='{"token": "access-token"}',
        collections_root="data/collections",
    )
    job.update_progress({"processed": 1, "total": 1, "status": "processed", "file_name": "doc.pdf"})
    job.mark_completed(
        {
            "collection_name": "google_drive_rag",
            "files": [{"name": "doc.pdf"}],
        }
    )
    drive_integration._register_import_job(job)
    fake_st.session_state.gdrive_import_job_id = "job-complete"

    with pytest.raises(RerunCalled):
        drive_integration.run_pending_google_drive_import(FakeDriveService())

    assert fake_st.session_state.gdrive_status == "connected"
    assert fake_st.session_state.collection == ["google_drive_rag"]
    assert fake_st.session_state.messages == []
    assert "1 arquivo(s) novo(s)/alterado(s)" in fake_st.session_state.drive_feedback
    assert fake_st.session_state.gdrive_import_job_id is None
    assert fake_st.session_state.gdrive_import_progress is None


def test_pending_import_uses_shared_collection_root(monkeypatch, tmp_path, drive_integration):
    fake_st = FakeStreamlit(
        session_state={
            "gdrive_status": "importing",
            "gdrive_credentials_json": '{"token": "access-token"}',
            "collection": None,
        },
    )
    service = FakeDriveService()
    service.collections_root = tmp_path / "collections"
    monkeypatch.setattr(drive_integration, "st", fake_st)
    captured_roots = []

    def fake_start_import_job(credentials_json, collections_root):
        captured_roots.append(collections_root)
        job = drive_integration.GoogleDriveImportJob(
            job_id="job-shared-root",
            credentials_json=credentials_json,
            collections_root=str(collections_root),
        )
        drive_integration._register_import_job(job)
        return job

    monkeypatch.setattr(drive_integration, "_start_import_job", fake_start_import_job)

    assert drive_integration.run_pending_google_drive_import(service) is True
    assert captured_roots == [tmp_path / "collections"]


def test_files_panel_lists_partially_imported_shared_drive_files(monkeypatch, tmp_path, drive_integration):
    collections = importlib.import_module("presentation.sidebar.Collections")
    monkeypatch.setattr(collections, "PROJECT_ROOT", tmp_path)
    drive_collection = tmp_path / "data" / "collections" / "google_drive_rag"
    drive_collection.mkdir(parents=True)
    (drive_collection / "57_Ata.md").write_text("# Ata\n\ntexto", encoding="utf-8")

    documents = collections.list_collection_documents(user_id="ignored")

    assert documents == [
        {
            "collection": "google_drive_rag",
            "file_name": "57_Ata.md",
            "label": "Ata",
        }
    ]


def test_connect_button_does_not_run_import_in_button_renderer(monkeypatch, drive_integration):
    fake_st = FakeStreamlit(
        session_state={
            "gdrive_status": "importing",
        },
    )
    monkeypatch.setattr(drive_integration, "st", fake_st)
    monkeypatch.setattr(drive_integration, "GoogleDriveService", FakeDriveService)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("import should run from the app body, not the button")

    monkeypatch.setattr(drive_integration, "run_pending_google_drive_import", fail_if_called)

    assert drive_integration.render_connect_button() is False
    assert fake_st.infos == ["Conectando ao Google Drive e listando a pasta rag..."]


def test_manual_callback_page_and_popup_ui_were_removed():
    source = (APPLICATION_DIR / "presentation" / "integrations" / "GoogleDrive.py").read_text(
        encoding="utf-8"
    )
    assert "handle_oauth_callback_page" not in source
    assert "Ja autorizei" not in source
    assert "Já autorizei" not in source
    assert "st.link_button" not in source
    assert "window.open" not in source
    assert 'target="_blank"' not in source
    assert "firebase_id_token" not in source
    assert "user_snapshot" not in source
