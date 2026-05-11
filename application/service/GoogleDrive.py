"""Public facade for Google Drive ingestion."""
# Simple: Download and process files from Google Drive

from .google_drive.Auth import (
    build_auth_flow,
    build_authorization_url,
    build_drive_service,
    credentials_from_json,
    credentials_to_json,
    exchange_code_for_credentials,
    login_with_google_drive,
    refresh_if_needed,
)
from .google_drive.Configuration import build_google_drive_paths
from .google_drive.Constants import (
    DOCX_MIME_TYPE,
    DOCLING_BINARY_MIME_TYPES,
    DOCLING_EXPORT_MIME_TYPES,
    EXTRACTION_METHOD_DOCLING,
    EXTRACTION_METHOD_PYPDF,
    PDF_MIME_TYPE,
    PPTX_MIME_TYPE,
    SCOPES,
    SPREADSHEET_SUFFIXES,
    SUPPORTED_EXTRACTION_METHODS,
    XLSX_MIME_TYPE,
)
from .google_drive.Extraction import (
    download_request_bytes,
    download_drive_file_bytes,
    export_google_workspace_file_bytes,
    extract_drive_file_text,
    extract_file_text_with_docling,
    extract_pdf_text_with_pypdf,
    get_docling_converter,
    safe_filename,
)
from .google_drive.Ingestion import ingest_folder_to_collection
from .google_drive.Listing import (
    build_docling_file_plan,
    list_supported_files,
    normalize_extraction_method,
)


class GoogleDriveService:
    def __init__(self):
        paths = build_google_drive_paths()
        self.credentials_file = paths.credentials_file
        self.collections_root = paths.collections_root
        self.token_file = paths.token_file
        self.redirect_uri = paths.redirect_uri
        self._docling_converter = None

    # --- Web OAuth flow (used by the Streamlit app) -----------------------
    def start_login(self, redirect_uri: str | None = None) -> tuple[str, str]:
        """Build the Google authorize URL. Returns ``(auth_url, state)``."""
        flow = build_auth_flow(self.credentials_file, redirect_uri or self.redirect_uri)
        return build_authorization_url(flow)

    def complete_login(self, state: str, code: str, redirect_uri: str | None = None):
        """Exchange the auth code for credentials and persist them."""
        flow = build_auth_flow(
            self.credentials_file,
            redirect_uri or self.redirect_uri,
            state=state,
        )
        credentials = exchange_code_for_credentials(flow, code)
        self._save_token(credentials)
        return credentials

    def load_persisted_credentials(self):
        """Return cached credentials, refreshing if needed; ``None`` if absent/invalid."""
        if not self.token_file.exists():
            return None
        try:
            credentials = credentials_from_json(self.token_file.read_text(encoding="utf-8"))
            credentials = refresh_if_needed(credentials)
        except Exception:
            return None
        if not credentials.valid:
            return None
        self._save_token(credentials)
        return credentials

    def forget_persisted_credentials(self) -> None:
        try:
            self.token_file.unlink()
        except FileNotFoundError:
            pass

    def _save_token(self, credentials) -> None:
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(credentials_to_json(credentials), encoding="utf-8")

    # --- Desktop OAuth flow (used by the Telegram bot) --------------------
    def login(self):
        return login_with_google_drive(self.credentials_file)

    def credentials_from_json(self, raw_json: str):
        return credentials_from_json(raw_json)

    def _get_drive_service(self, credentials):
        return build_drive_service(credentials)

    def _build_docling_file_plan(self, drive_file: dict):
        plan = build_docling_file_plan(drive_file)
        if not plan:
            return None
        return {
            "mode": plan.mode,
            "suffix": plan.suffix,
            "export_mime_type": plan.export_mime_type,
        }

    def list_supported_files(self, folder_name="rag", extraction_method=EXTRACTION_METHOD_DOCLING, credentials=None):
        service = self._get_drive_service(credentials or self.login())
        normalized_method = normalize_extraction_method(extraction_method)
        return list_supported_files(service, folder_name, normalized_method).to_dict()

    def list_pdfs(self, folder_name="rag", credentials=None):
        return self.list_supported_files(
            folder_name=folder_name,
            extraction_method=EXTRACTION_METHOD_DOCLING,
            credentials=credentials,
        )

    def _normalize_extraction_method(self, extraction_method: str | None) -> str:
        return normalize_extraction_method(extraction_method)

    def _download_request_bytes(self, request) -> bytes:
        return download_request_bytes(request)

    def _download_drive_file_bytes(self, service, file_id: str) -> bytes:
        return download_drive_file_bytes(service, file_id)

    def _export_google_workspace_file_bytes(self, service, file_id: str, export_mime_type: str) -> bytes:
        return export_google_workspace_file_bytes(service, file_id, export_mime_type)

    def _extract_pdf_text_with_pypdf(self, pdf_bytes: bytes) -> str:
        return extract_pdf_text_with_pypdf(pdf_bytes)

    def _get_docling_converter(self):
        return get_docling_converter(self)

    def _extract_file_text_with_docling(self, file_bytes: bytes, suffix: str) -> str:
        return extract_file_text_with_docling(self, file_bytes, suffix)

    def _extract_drive_file_text(self, service, drive_file: dict, extraction_method: str) -> str:
        return extract_drive_file_text(self, service, drive_file, extraction_method)

    def _safe_filename(self, name: str) -> str:
        return safe_filename(name)

    def ingest_folder_to_collection(
        self,
        folder_name="rag",
        collection_name="google_drive_rag",
        credentials=None,
        extraction_method=EXTRACTION_METHOD_DOCLING,
    ):
        service = self._get_drive_service(credentials or self.login())
        result = ingest_folder_to_collection(
            owner=self,
            service=service,
            collections_root=self.collections_root,
            folder_name=folder_name,
            collection_name=collection_name,
            extraction_method=extraction_method,
        )
        return result.to_dict()
