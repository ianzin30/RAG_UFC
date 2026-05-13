"""Google Drive integration for importing the Drive folder named ``rag``.

The Streamlit flow is same-tab OAuth:
1. The app renders "Conectar ao Google Drive" as a same-tab HTML form to Google.
2. The current tab leaves Streamlit, completes Google sign-in, and redirects
   back to Streamlit with ``?code=...&state=...``.
3. This module exchanges the code immediately, imports Drive files, clears the
   OAuth query params, and reruns the normal app.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from html import escape
import json
import logging
from pathlib import Path
import threading
import time
from typing import Callable
from urllib.parse import parse_qsl, urlparse, urlunparse
from uuid import uuid4

import streamlit as st

from presentation.shared.Config import PROJECT_ROOT, UPLOAD_COLLECTION_NAME
from service.GoogleDrive import GoogleDriveService


logger = logging.getLogger(__name__)


_DRIVE_FOLDER_NAME = "rag"
_COLLECTION_NAME = "google_drive_rag"

OAUTH_STATE_KEY = "gdrive_oauth_state"
OAUTH_CODE_VERIFIER_KEY = "gdrive_code_verifier"
OAUTH_AUTH_URL_KEY = "gdrive_auth_url"
OAUTH_STORE_DIR = PROJECT_ROOT / "data" / "cache" / "google_drive_oauth"
OAUTH_FLOW_TTL_SECONDS = 20 * 60
IMPORT_JOB_ID_KEY = "gdrive_import_job_id"


@dataclass
class GoogleDriveImportJob:
    job_id: str
    credentials_json: str
    collections_root: str
    status: str = "running"
    processed: int = 0
    total: int = 0
    checked: int = 0
    cached: int = 0
    changed: int = 0
    new: int = 0
    deleted: int = 0
    to_process: int = 0
    current_file: str | None = None
    progress_status: str | None = "listing"
    result: dict | None = None
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def update_progress(self, progress: dict[str, object]) -> None:
        with self.lock:
            self.processed = _progress_int(progress.get("processed"), self.processed)
            self.total = _progress_int(progress.get("total"), self.total)
            self.checked = _progress_int(progress.get("checked"), self.checked)
            self.cached = _progress_int(progress.get("cached"), self.cached)
            self.changed = _progress_int(progress.get("changed"), self.changed)
            self.new = _progress_int(progress.get("new"), self.new)
            self.deleted = _progress_int(progress.get("deleted"), self.deleted)
            self.to_process = _progress_int(progress.get("to_process"), self.to_process)
            current_file = progress.get("file_name")
            self.current_file = str(current_file) if current_file else None
            progress_status = progress.get("status")
            self.progress_status = str(progress_status) if progress_status else None
            self.updated_at = time.time()

    def mark_completed(self, result: dict) -> None:
        with self.lock:
            fallback_file_count = len(result.get("files") or [])
            self.status = "completed"
            self.error = None
            self.processed = _progress_int(result.get("processed_count"), self.processed or fallback_file_count)
            self.total = _progress_int(result.get("total_count"), self.total or fallback_file_count)
            self.checked = _progress_int(result.get("checked_count"), self.checked or self.total)
            self.cached = _progress_int(result.get("cached_count"), self.cached)
            self.changed = _progress_int(result.get("changed_count"), self.changed)
            self.new = _progress_int(result.get("new_count"), self.new)
            self.deleted = _progress_int(result.get("deleted_count"), self.deleted)
            self.to_process = self.new + self.changed
            self.result = {
                **result,
                "processed_count": self.processed,
                "total_count": self.total,
                "checked_count": self.checked,
                "cached_count": self.cached,
                "changed_count": self.changed,
                "new_count": self.new,
                "deleted_count": self.deleted,
            }
            self.updated_at = time.time()

    def mark_error(self, error: str) -> None:
        with self.lock:
            self.status = "error"
            self.error = error
            self.updated_at = time.time()

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            return {
                "job_id": self.job_id,
                "status": self.status,
                "processed": self.processed,
                "total": self.total,
                "checked": self.checked,
                "cached": self.cached,
                "changed": self.changed,
                "new": self.new,
                "deleted": self.deleted,
                "to_process": self.to_process,
                "file_name": self.current_file,
                "progress_status": self.progress_status,
                "result": self.result,
                "error": self.error,
                "collections_root": self.collections_root,
                "started_at": self.started_at,
                "updated_at": self.updated_at,
            }


_IMPORT_JOBS: dict[str, GoogleDriveImportJob] = {}
_IMPORT_JOBS_LOCK = threading.Lock()


def _oauth_flow_path(state: str):
    import hashlib

    digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
    return OAUTH_STORE_DIR / f"{digest}.json"


def _register_oauth_flow(
    state: str,
    code_verifier: str,
) -> None:
    payload = {
        "state": state,
        "code_verifier": code_verifier,
        "created_at": time.time(),
    }
    try:
        OAUTH_STORE_DIR.mkdir(parents=True, exist_ok=True)
        _oauth_flow_path(state).write_text(json.dumps(payload), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not persist Google Drive OAuth state: %s", exc)


def _read_oauth_flow(state: str) -> dict | None:
    path = _oauth_flow_path(state)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    created_at = float(payload.get("created_at") or 0)
    if time.time() - created_at > OAUTH_FLOW_TTL_SECONDS:
        with suppress(OSError):
            path.unlink()
        return None
    if payload.get("state") != state:
        return None
    return payload


def _delete_oauth_flow(state: str | None) -> None:
    if not state:
        return
    with suppress(OSError):
        _oauth_flow_path(state).unlink()


def _query_param_value(name: str) -> str:
    value = st.query_params.get(name)
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "")


def _clear_oauth_query_params() -> None:
    with suppress(Exception):
        st.query_params.clear()


def _clear_oauth_transient_state(*, delete_flow: bool = True) -> None:
    state = st.session_state.get(OAUTH_STATE_KEY)
    if delete_flow:
        _delete_oauth_flow(state)
    st.session_state[OAUTH_STATE_KEY] = None
    st.session_state[OAUTH_CODE_VERIFIER_KEY] = None
    st.session_state[OAUTH_AUTH_URL_KEY] = None


def _reset_state(*, keep_error: bool = False) -> None:
    st.session_state.gdrive_status = "idle"
    _clear_oauth_transient_state()
    st.session_state.gdrive_import_progress = None
    st.session_state[IMPORT_JOB_ID_KEY] = None
    if not keep_error:
        st.session_state.gdrive_error = None


def _bootstrap_from_persisted(service: GoogleDriveService) -> None:
    """If a token file already exists, hydrate the session as connected."""
    if st.session_state.gdrive_status != "idle":
        return
    if st.session_state.gdrive_credentials_json:
        return
    credentials = service.load_persisted_credentials()
    if credentials is None:
        return
    st.session_state.gdrive_credentials_json = credentials.to_json()
    st.session_state.gdrive_status = "connected"


def _start_oauth_flow(service: GoogleDriveService) -> str:
    auth_url = st.session_state.get(OAUTH_AUTH_URL_KEY)
    state = st.session_state.get(OAUTH_STATE_KEY)
    code_verifier = st.session_state.get(OAUTH_CODE_VERIFIER_KEY)
    if auth_url and state and code_verifier:
        return str(auth_url)

    auth_url, state, code_verifier = service.start_login()
    st.session_state[OAUTH_AUTH_URL_KEY] = auth_url
    st.session_state[OAUTH_STATE_KEY] = state
    st.session_state[OAUTH_CODE_VERIFIER_KEY] = code_verifier
    _register_oauth_flow(state, code_verifier)
    return auth_url


def _credentials_from_oauth_return(
    service: GoogleDriveService,
    *,
    code: str,
    returned_state: str,
):
    expected_state = st.session_state.get(OAUTH_STATE_KEY)
    flow_record = _read_oauth_flow(returned_state)

    if expected_state and returned_state != expected_state:
        raise RuntimeError("Estado OAuth invalido. Clique em Conectar ao Google Drive novamente.")
    if not expected_state and flow_record is None:
        raise RuntimeError("Sessao OAuth expirada. Clique em Conectar ao Google Drive novamente.")

    code_verifier = st.session_state.get(OAUTH_CODE_VERIFIER_KEY)
    if not code_verifier and flow_record:
        code_verifier = flow_record.get("code_verifier")
    if not code_verifier:
        raise RuntimeError("Verificador PKCE ausente. Clique em Conectar ao Google Drive novamente.")

    credentials = service.complete_login(
        code=code,
        code_verifier=str(code_verifier),
        state=returned_state,
    )
    _delete_oauth_flow(returned_state)
    return credentials


def _handle_oauth_return(service: GoogleDriveService) -> bool:
    """Handle Google ``?code=&state=`` inside the normal app route."""
    code = _query_param_value("code")
    returned_state = _query_param_value("state")
    oauth_error = _query_param_value("error")
    if not code and not oauth_error:
        return False

    try:
        if oauth_error:
            description = _query_param_value("error_description")
            detail = f"{oauth_error}: {description}" if description else oauth_error
            raise RuntimeError(f"Google recusou a autorizacao: {detail}")
        if not code:
            raise RuntimeError("Callback do Google sem codigo de autorizacao.")
        if not returned_state:
            raise RuntimeError("Callback do Google sem estado OAuth.")

        credentials = _credentials_from_oauth_return(
            service,
            code=code,
            returned_state=returned_state,
        )
        st.session_state.gdrive_credentials_json = credentials.to_json()
        st.session_state.gdrive_import_result = None
        st.session_state.gdrive_import_progress = None
        st.session_state[IMPORT_JOB_ID_KEY] = None
        st.session_state.gdrive_error = None
        st.session_state.gdrive_status = "importing"
        _clear_oauth_transient_state(delete_flow=False)
    except Exception as exc:
        logger.warning("Google Drive OAuth callback failed: %s", exc)
        st.session_state.gdrive_status = "error"
        st.session_state.gdrive_error = f"Falha ao conectar ao Google Drive: {exc}"
        _delete_oauth_flow(returned_state)
        _clear_oauth_transient_state()
    finally:
        _clear_oauth_query_params()

    st.rerun()
    return True


def handle_google_drive_oauth_callback(service: GoogleDriveService | None = None) -> bool:
    """Consume a Drive OAuth callback before rendering the normal app."""
    return _handle_oauth_return(service or GoogleDriveService())


def handle_google_drive_oauth_callback_before_login(
    *,
    service: GoogleDriveService | None = None,
) -> bool:
    """Backward-compatible alias for the auth-free Drive callback handler."""
    return handle_google_drive_oauth_callback(service=service)


def _current_import_collections_root(service: GoogleDriveService) -> Path:
    return Path(getattr(service, "collections_root", PROJECT_ROOT / "data" / "collections"))


def _ingest_drive_folder(
    *,
    service: GoogleDriveService,
    credentials_json: str,
    collections_root: Path,
    progress_callback: Callable[[dict[str, object]], None] | None = None,
) -> dict:
    credentials = service.credentials_from_json(credentials_json)
    return service.ingest_folder_to_collection(
        folder_name=_DRIVE_FOLDER_NAME,
        collection_name=_COLLECTION_NAME,
        credentials=credentials,
        progress_callback=progress_callback,
        collections_root=collections_root,
    )


def _apply_import_result_to_session(result: dict) -> None:
    st.session_state.collection = [UPLOAD_COLLECTION_NAME]
    st.session_state.current_collection = None
    st.session_state.messages = []
    st.session_state.rag_service = None
    file_count = len(result["files"])
    processed_count = _progress_int(result.get("processed_count"))
    cached_count = _progress_int(result.get("cached_count"))
    deleted_count = _progress_int(result.get("deleted_count"))
    st.session_state.gdrive_import_result = {
        "collection_name": result["collection_name"],
        "file_count": file_count,
        "processed_count": processed_count,
        "cached_count": cached_count,
        "deleted_count": deleted_count,
    }
    if processed_count:
        st.session_state.drive_feedback = (
            f"{processed_count} arquivo(s) novo(s)/alterado(s) importado(s), "
            f"{cached_count} em cache"
            f"{f', {deleted_count} removido(s)' if deleted_count else ''}."
        )
    else:
        st.session_state.drive_feedback = (
            f"Google Drive verificado. {cached_count or file_count} arquivo(s) em cache, "
            f"nenhum arquivo alterado{f', {deleted_count} removido(s)' if deleted_count else ''}."
        )
    st.session_state.gdrive_status = "connected"
    st.session_state.gdrive_import_progress = None
    st.session_state[IMPORT_JOB_ID_KEY] = None


def _run_import(
    service: GoogleDriveService,
    progress_callback: Callable[[dict[str, object]], None] | None = None,
) -> None:
    raw = st.session_state.gdrive_credentials_json
    if not raw:
        st.session_state.gdrive_status = "error"
        st.session_state.gdrive_error = "Credenciais do Google Drive nao encontradas."
        st.session_state.gdrive_import_progress = None
        st.session_state[IMPORT_JOB_ID_KEY] = None
        return
    try:
        result = _ingest_drive_folder(
            service=service,
            credentials_json=raw,
            collections_root=_current_import_collections_root(service),
            progress_callback=progress_callback,
        )
    except Exception as exc:
        logger.warning("Google Drive import failed: %s", exc)
        st.session_state.gdrive_status = "error"
        st.session_state.gdrive_error = f"Falha ao importar arquivos: {exc}"
        st.session_state.gdrive_import_progress = None
        st.session_state[IMPORT_JOB_ID_KEY] = None
        return

    _apply_import_result_to_session(result)


def _progress_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _short_file_name(value: object, *, limit: int = 80) -> str:
    file_name = str(value or "").strip()
    if len(file_name) > limit:
        return f"{file_name[: limit - 3]}..."
    return file_name


def _import_phase(progress: dict[str, object] | None) -> str:
    if not progress:
        return "listing"
    job_status = str(progress.get("status") or "").strip()
    if job_status in {"completed", "error"}:
        return job_status
    raw_status = str(progress.get("progress_status") or "").strip()
    if raw_status in {"checking", "cached", "queued"}:
        return "checking_cache"
    if raw_status in {"processing", "processed"}:
        return "importing_changes"
    if raw_status == "completed":
        return "completed"
    if raw_status == "finalizing":
        return "finalizing"
    return "listing"


def _phase_metrics(progress: dict[str, object] | None) -> dict[str, object]:
    progress = progress or {}
    checked = max(0, _progress_int(progress.get("checked")))
    total = max(0, _progress_int(progress.get("total")))
    processed = max(0, _progress_int(progress.get("processed")))
    cached = max(0, _progress_int(progress.get("cached")))
    changed = max(0, _progress_int(progress.get("changed")))
    new = max(0, _progress_int(progress.get("new")))
    deleted = max(0, _progress_int(progress.get("deleted")))
    to_process = max(0, _progress_int(progress.get("to_process")))
    changed_or_new = changed + new
    if changed_or_new > to_process:
        to_process = changed_or_new
    return {
        "phase": _import_phase(progress),
        "processed": processed,
        "total": total,
        "checked": checked,
        "cached": cached,
        "changed": changed,
        "new": new,
        "deleted": deleted,
        "to_process": to_process,
        "changed_or_new": changed_or_new,
        "file_name": _short_file_name(progress.get("file_name")),
    }


def _format_import_progress(progress: dict[str, object] | None, *, compact: bool = False) -> str:
    if not progress:
        return "Conectando ao Google Drive e listando a pasta rag..."

    metrics = _phase_metrics(progress)
    phase = str(metrics["phase"])
    processed = int(metrics["processed"])
    total = int(metrics["total"])
    checked = int(metrics["checked"])
    cached = int(metrics["cached"])
    deleted = int(metrics["deleted"])
    to_process = int(metrics["to_process"])
    changed_or_new = int(metrics["changed_or_new"])
    file_name = str(metrics["file_name"])

    if phase == "listing":
        return "Conectando ao Google Drive e listando a pasta rag..."

    if phase == "checking_cache":
        return (
            f"Verificando cache... {checked}/{total} verificados, "
            f"{cached} em cache, {changed_or_new} para importar"
            f"{f', {deleted} removidos' if deleted else ''}."
        )

    if phase == "importing_changes" and to_process > 0:
        suffix = f" Processando: {file_name}" if file_name and not compact else ""
        return (
            f"Importando alteracoes... {processed}/{to_process} processados, "
            f"{cached} em cache{f', {deleted} removidos' if deleted else ''}.{suffix}"
        )

    if phase == "completed":
        if to_process <= 0:
            return (
                f"Google Drive verificado. {cached}/{total} arquivos em cache, "
                f"nenhum arquivo alterado{f', {deleted} removidos' if deleted else ''}."
            )
        return (
            f"Importacao concluida. {processed} alterados/importados, "
            f"{cached} em cache{f', {deleted} removidos' if deleted else ''}."
        )

    if phase == "finalizing":
        return "Finalizando importacao do Google Drive e atualizando o app..."

    if total <= 0:
        return "Conectando ao Google Drive e listando a pasta rag..."
    processed = min(processed, total)
    if file_name and phase == "importing_changes":
        return (
            f"Importando arquivos do Google Drive... {processed}/{total} processados. "
            f"Processando: {file_name}"
        )
    return f"Importando arquivos do Google Drive... {processed}/{total} processados."


def _overall_progress_percent(progress: dict[str, object] | None) -> int:
    if not progress:
        return 0
    metrics = _phase_metrics(progress)
    phase = str(metrics["phase"])
    checked = int(metrics["checked"])
    total = int(metrics["total"])
    processed = int(metrics["processed"])
    to_process = int(metrics["to_process"])
    if phase == "completed":
        return 100
    if phase == "importing_changes" and total > 0:
        denominator = max(total + to_process, 1)
        return min(99, int(((total + processed) / denominator) * 100))
    if phase == "checking_cache" and total > 0:
        denominator = max(total + to_process, total, 1)
        return min(99, int((checked / denominator) * 100))
    if total <= 0:
        return 0
    return min(99, int((checked / total) * 100))


def _cache_check_percent(progress: dict[str, object] | None) -> int:
    metrics = _phase_metrics(progress)
    total = int(metrics["total"])
    if total <= 0:
        return 0
    return min(100, int((int(metrics["checked"]) / total) * 100))


def _change_import_percent(progress: dict[str, object] | None) -> int:
    metrics = _phase_metrics(progress)
    to_process = int(metrics["to_process"])
    if to_process <= 0:
        return 100 if str(metrics["phase"]) == "completed" else 0
    return min(100, int((int(metrics["processed"]) / to_process) * 100))


def _progress_percent(progress: dict[str, object] | None) -> int:
    return _overall_progress_percent(progress)


def _register_import_job(job: GoogleDriveImportJob) -> None:
    with _IMPORT_JOBS_LOCK:
        _IMPORT_JOBS[job.job_id] = job


def _get_import_job(job_id: str | None) -> GoogleDriveImportJob | None:
    if not job_id:
        return None
    with _IMPORT_JOBS_LOCK:
        return _IMPORT_JOBS.get(str(job_id))


def _delete_import_job(job_id: str | None) -> None:
    if not job_id:
        return
    with _IMPORT_JOBS_LOCK:
        _IMPORT_JOBS.pop(str(job_id), None)


def _run_import_worker(job_id: str) -> None:
    job = _get_import_job(job_id)
    if job is None:
        return
    try:
        service = GoogleDriveService()
        result = _ingest_drive_folder(
            service=service,
            credentials_json=job.credentials_json,
            collections_root=Path(job.collections_root),
            progress_callback=job.update_progress,
        )
    except Exception as exc:
        logger.warning("Google Drive background import failed: %s", exc)
        job.mark_error(str(exc))
        return
    job.mark_completed(result)


def _start_import_job(credentials_json: str, collections_root: Path) -> GoogleDriveImportJob:
    job = GoogleDriveImportJob(
        job_id=uuid4().hex,
        credentials_json=credentials_json,
        collections_root=str(collections_root),
    )
    _register_import_job(job)
    thread = threading.Thread(
        target=_run_import_worker,
        args=(job.job_id,),
        name=f"google-drive-import-{job.job_id[:8]}",
        daemon=True,
    )
    thread.start()
    return job


def _ensure_import_job(service: GoogleDriveService) -> GoogleDriveImportJob:
    job_id = st.session_state.get(IMPORT_JOB_ID_KEY)
    job = _get_import_job(job_id)
    if job is not None:
        return job

    raw = st.session_state.get("gdrive_credentials_json")
    if not raw:
        raise RuntimeError("Credenciais do Google Drive nao encontradas.")

    job = _start_import_job(
        str(raw),
        _current_import_collections_root(service),
    )
    st.session_state[IMPORT_JOB_ID_KEY] = job.job_id
    return job


def _clear_completed_import_job(job_id: str | None) -> None:
    _delete_import_job(job_id)
    st.session_state[IMPORT_JOB_ID_KEY] = None


def _render_import_detail(message: str) -> None:
    caption = getattr(st, "caption", None)
    if callable(caption):
        caption(message)
        return
    st.info(message)


def _render_import_progress(snapshot: dict[str, object]) -> None:
    st.info(_format_import_progress(snapshot))
    st.progress(_overall_progress_percent(snapshot))

    metrics = _phase_metrics(snapshot)
    phase = str(metrics["phase"])
    total = int(metrics["total"])
    checked = int(metrics["checked"])
    cached = int(metrics["cached"])
    deleted = int(metrics["deleted"])
    to_process = int(metrics["to_process"])
    processed = int(metrics["processed"])
    changed_or_new = int(metrics["changed_or_new"])
    file_name = str(metrics["file_name"])

    if phase == "listing":
        _render_import_detail("Fase atual: conectando ao Drive e buscando a lista de arquivos.")
        return

    if total > 0:
        cache_detail = (
            f"Cache: {checked}/{total} verificados, {cached} em cache, "
            f"{changed_or_new} novo(s)/alterado(s)"
            f"{f', {deleted} removido(s)' if deleted else ''}."
        )
        _render_import_detail(cache_detail)
        st.progress(_cache_check_percent(snapshot))

    if to_process > 0:
        import_detail = f"Alteracoes: {processed}/{to_process} processados."
        if file_name and phase == "importing_changes":
            import_detail = f"{import_detail} Arquivo atual: {file_name}"
        _render_import_detail(import_detail)
        st.progress(_change_import_percent(snapshot))
    elif phase == "completed" and total > 0:
        _render_import_detail("Alteracoes: nenhum arquivo novo ou alterado para importar.")


def _fragment_decorator(*, run_every):
    fragment = getattr(st, "fragment", None)
    if callable(fragment):
        return fragment(run_every=run_every)

    def decorator(func):
        return func

    return decorator


def _render_import_progress_fragment(job_id: str) -> None:
    @_fragment_decorator(run_every=1)
    def poll_import_job() -> None:
        job = _get_import_job(job_id)
        if job is None:
            st.info(_format_import_progress(None))
            return
        snapshot = job.snapshot()
        st.session_state.gdrive_import_progress = snapshot
        if snapshot.get("status") in {"completed", "error"}:
            st.rerun()
        _render_import_progress(snapshot)

    poll_import_job()


def run_pending_google_drive_import(service: GoogleDriveService | None = None) -> bool:
    """Import Drive files when OAuth just completed, independent of visible panels."""
    if st.session_state.get("gdrive_status") != "importing":
        return False
    service = service or GoogleDriveService()
    try:
        job = _ensure_import_job(service)
    except Exception as exc:
        st.session_state.gdrive_status = "error"
        st.session_state.gdrive_error = f"Falha ao importar arquivos: {exc}"
        st.session_state.gdrive_import_progress = None
        st.session_state[IMPORT_JOB_ID_KEY] = None
        st.rerun()
        return True

    snapshot = job.snapshot()
    st.session_state.gdrive_import_progress = snapshot

    if snapshot.get("status") == "completed":
        result = snapshot.get("result")
        if not isinstance(result, dict):
            st.session_state.gdrive_status = "error"
            st.session_state.gdrive_error = "Importacao do Google Drive terminou sem resultado."
        else:
            _apply_import_result_to_session(result)
        _clear_completed_import_job(str(snapshot.get("job_id") or ""))
        st.rerun()
        return True

    if snapshot.get("status") == "error":
        st.session_state.gdrive_status = "error"
        st.session_state.gdrive_error = f"Falha ao importar arquivos: {snapshot.get('error')}"
        st.session_state.gdrive_import_progress = None
        _clear_completed_import_job(str(snapshot.get("job_id") or ""))
        st.rerun()
        return True

    _render_import_progress_fragment(job.job_id)
    return True


def _render_same_tab_auth_form(auth_url: str, label: str, help_text: str | None) -> None:
    parsed = urlparse(auth_url)
    action = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    hidden_inputs = "\n".join(
        f'<input type="hidden" name="{escape(name, quote=True)}" value="{escape(value, quote=True)}">'
        for name, value in parse_qsl(parsed.query, keep_blank_values=True)
    )
    title = help_text or label
    style = (
        "align-items:center;background:#152238;border:1px solid #334766;"
        "border-radius:8px;color:#f8fbff;display:flex;font-weight:700;"
        "justify-content:center;min-height:40px;padding:0 16px;text-align:center;"
        "width:100%;"
    )
    st.markdown(
        '<form method="get" target="_self" '
        f'action="{escape(action, quote=True)}" style="margin:0;width:100%;">'
        f"{hidden_inputs}"
        f'<button type="submit" title="{escape(title, quote=True)}" style="{style}">'
        f"{escape(label)}</button></form>",
        unsafe_allow_html=True,
    )


def render_connect_button(
    button_label: str = "Conectar ao Google Drive",
    help_text: str | None = None,
    key: str = "google_drive_connect",
) -> bool:
    """Render the Google Drive connection UI as a same-tab OAuth flow."""
    service = GoogleDriveService()

    if _handle_oauth_return(service):
        return True

    _bootstrap_from_persisted(service)

    status = st.session_state.gdrive_status

    if status == "importing":
        job = _get_import_job(st.session_state.get(IMPORT_JOB_ID_KEY))
        progress = job.snapshot() if job else st.session_state.get("gdrive_import_progress")
        st.info(_format_import_progress(progress, compact=True))
        return False

    if status == "idle":
        try:
            auth_url = _start_oauth_flow(service)
        except FileNotFoundError as exc:
            st.session_state.gdrive_status = "error"
            st.session_state.gdrive_error = str(exc)
            st.rerun()
            return False
        except Exception as exc:
            logger.warning("Failed to start Google Drive auth flow: %s", exc)
            st.session_state.gdrive_status = "error"
            st.session_state.gdrive_error = f"Falha ao iniciar autenticacao: {exc}"
            st.rerun()
            return False

        _render_same_tab_auth_form(auth_url, button_label, help_text)
        return False

    if status == "connected":
        result = st.session_state.gdrive_import_result
        if result:
            processed_count = _progress_int(result.get("processed_count"))
            cached_count = _progress_int(result.get("cached_count"))
            st.success(
                f"Google Drive conectado. {result['file_count']} arquivo(s) na colecao "
                f"'{result['collection_name']}' "
                f"({processed_count} novo(s)/alterado(s), {cached_count} em cache)."
            )
        else:
            st.success("Google Drive conectado.")
        reimport_col, disconnect_col = st.columns(2)
        with reimport_col:
            if st.button(
                "Reimportar pasta RAG",
                key=f"{key}_reimport",
                use_container_width=True,
            ):
                st.session_state.gdrive_status = "importing"
                st.session_state.gdrive_error = None
                st.rerun()
        with disconnect_col:
            if st.button(
                "Desconectar",
                key=f"{key}_disconnect",
                use_container_width=True,
            ):
                service.forget_persisted_credentials()
                st.session_state.gdrive_credentials_json = None
                st.session_state.gdrive_import_result = None
                _reset_state()
                st.rerun()
        return False

    if status == "error":
        message = st.session_state.gdrive_error or "Falha ao conectar ao Google Drive."
        st.error(message)
        if st.button("Tentar novamente", key=f"{key}_retry", use_container_width=True):
            if st.session_state.get("gdrive_credentials_json"):
                st.session_state.gdrive_status = "importing"
                st.session_state.gdrive_error = None
            else:
                _reset_state()
            st.rerun()
        return False

    return False
