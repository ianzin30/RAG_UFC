import json
import os
import re
import tempfile
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pypdf import PdfReader

try:
    from .spreadsheet_markdown import extract_spreadsheet_markdown
except ImportError:
    from spreadsheet_markdown import extract_spreadsheet_markdown

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

# Permissões que pedimos ao Google: apenas leitura do Drive
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
EXTRACTION_METHOD_PYPDF = "pypdf"
EXTRACTION_METHOD_DOCLING = "docling"
SUPPORTED_EXTRACTION_METHODS = {
    EXTRACTION_METHOD_PYPDF,
    EXTRACTION_METHOD_DOCLING,
}
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_MIME_TYPE = "application/pdf"
SPREADSHEET_SUFFIXES = {".xlsx", ".csv"}

DOCLING_BINARY_MIME_TYPES = {
    PDF_MIME_TYPE: ".pdf",
    DOCX_MIME_TYPE: ".docx",
    PPTX_MIME_TYPE: ".pptx",
    XLSX_MIME_TYPE: ".xlsx",
    "text/csv": ".csv",
    "text/html": ".html",
    "text/markdown": ".md",
    "text/x-markdown": ".md",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/tiff": ".tiff",
    "image/bmp": ".bmp",
}

DOCLING_EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": (DOCX_MIME_TYPE, ".docx"),
    "application/vnd.google-apps.spreadsheet": (XLSX_MIME_TYPE, ".xlsx"),
    "application/vnd.google-apps.presentation": (PPTX_MIME_TYPE, ".pptx"),
    "application/vnd.google-apps.drawing": ("image/png", ".png"),
}


class GoogleDriveService:

    def __init__(self):
        # Caminho raiz do projeto (3 níveis acima deste arquivo)
        root_dir = Path(__file__).resolve().parents[2]
        # Arquivo com as credenciais OAuth do Google Cloud Console
        credentials_override = os.getenv("GOOGLE_OAUTH_CREDENTIALS_FILE")
        self.credentials_file = (
            Path(credentials_override).expanduser()
            if credentials_override
            else root_dir / "config" / "google-oauth-credentials.json"
        )
        # Pasta onde as coleções de documentos são salvas
        self.collections_root = root_dir / "data" / "collections"
        self._docling_converter = None

    # ------------------------------------------------------------------ #
    # AUTENTICAÇÃO
    # ------------------------------------------------------------------ #

    def login(self):
        """Abre o navegador para o usuário fazer login com a conta Google."""
        if not self.credentials_file.exists():
            raise FileNotFoundError(
                f"Google OAuth credentials file not found: '{self.credentials_file}'."
            )
        config = json.loads(self.credentials_file.read_text(encoding="utf-8"))
        flow = InstalledAppFlow.from_client_config(config, SCOPES)
        return flow.run_local_server(
            port=0,
            open_browser=True,
            prompt="select_account",
            access_type="offline",
            include_granted_scopes="false",
        )

    def credentials_from_json(self, raw_json: str):
        """Reconstrói as credenciais a partir de uma string JSON salva anteriormente."""
        return Credentials.from_authorized_user_info(json.loads(raw_json), SCOPES)

    def _get_drive_service(self, credentials):
        """Cria o cliente da API do Google Drive."""
        return build("drive", "v3", credentials=credentials)

    # ------------------------------------------------------------------ #
    # BUSCA DE ARQUIVOS NO DRIVE
    # ------------------------------------------------------------------ #

    def _find_folder(self, service, folder_name: str):
        """Procura uma pasta pelo nome no Google Drive. Retorna None se não encontrar."""
        query = (
            f"mimeType = 'application/vnd.google-apps.folder' "
            f"and name = '{folder_name}' and trashed = false"
        )
        result = service.files().list(q=query, fields="files(id, name)", pageSize=10).execute()
        folders = result.get("files", [])
        return folders[0] if folders else None

    def _list_folder_files(self, service, folder_id: str):
        query = f"'{folder_id}' in parents and trashed = false"
        result = service.files().list(q=query, fields="files(id, name, mimeType)", pageSize=200).execute()
        return result.get("files", [])

    def _build_docling_file_plan(self, drive_file: dict):
        mime_type = (drive_file.get("mimeType") or "").lower()
        file_suffix = Path(drive_file.get("name") or "").suffix.lower()

        if mime_type in DOCLING_BINARY_MIME_TYPES:
            return {
                "mode": "download",
                "suffix": file_suffix or DOCLING_BINARY_MIME_TYPES[mime_type],
            }

        if mime_type in DOCLING_EXPORT_MIME_TYPES:
            export_mime_type, export_suffix = DOCLING_EXPORT_MIME_TYPES[mime_type]
            return {
                "mode": "export",
                "export_mime_type": export_mime_type,
                "suffix": export_suffix,
            }

        return None

    def list_supported_files(self, folder_name="rag", extraction_method=EXTRACTION_METHOD_PYPDF, credentials=None):
        """
        Lista os arquivos suportados pelo extrator escolhido dentro de uma pasta do Drive.
        Retorna um dicionário com o nome da pasta e a lista de arquivos.
        """
        extraction_method = self._normalize_extraction_method(extraction_method)
        service = self._get_drive_service(credentials or self.login())

        folder = self._find_folder(service, folder_name)
        if not folder:
            return {"folder_name": folder_name, "files": [], "message": f"Pasta '{folder_name}' não encontrada."}

        files = self._list_folder_files(service, folder["id"])
        if extraction_method == EXTRACTION_METHOD_DOCLING:
            supported_files = [drive_file for drive_file in files if self._build_docling_file_plan(drive_file)]
        else:
            supported_files = [drive_file for drive_file in files if drive_file.get("mimeType") == PDF_MIME_TYPE]

        return {
            "folder_name": folder["name"],
            "files": supported_files,
            "message": None,
        }

    def list_pdfs(self, folder_name="rag", credentials=None):
        """
        Compatibilidade com o fluxo antigo: lista apenas PDFs da pasta.
        """
        return self.list_supported_files(
            folder_name=folder_name,
            extraction_method=EXTRACTION_METHOD_PYPDF,
            credentials=credentials,
        )

    # ------------------------------------------------------------------ #
    # DOWNLOAD E EXTRAÇÃO DE TEXTO
    # ------------------------------------------------------------------ #

    def _normalize_extraction_method(self, extraction_method: str | None) -> str:
        normalized = (extraction_method or EXTRACTION_METHOD_PYPDF).strip().lower()
        if normalized not in SUPPORTED_EXTRACTION_METHODS:
            supported = ", ".join(sorted(SUPPORTED_EXTRACTION_METHODS))
            raise ValueError(f"Método de extração inválido: '{extraction_method}'. Use um destes: {supported}.")
        return normalized

    def _download_request_bytes(self, request) -> bytes:
        buffer = BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        buffer.seek(0)
        return buffer.read()

    def _download_drive_file_bytes(self, service, file_id: str) -> bytes:
        """Baixa um arquivo binário do Drive para a memória."""
        request = service.files().get_media(fileId=file_id)
        return self._download_request_bytes(request)

    def _export_google_workspace_file_bytes(self, service, file_id: str, export_mime_type: str) -> bytes:
        """Exporta um arquivo nativo do Google Workspace para um formato compatível."""
        request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
        return self._download_request_bytes(request)

    def _extract_pdf_text_with_pypdf(self, pdf_bytes: bytes) -> str:
        """Extrai o texto da camada textual do PDF com pypdf."""
        buffer = BytesIO(pdf_bytes)
        buffer.seek(0)
        reader = PdfReader(buffer)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(p.strip() for p in pages if p.strip())

    def _get_docling_converter(self):
        if self._docling_converter is None:
            try:
                from docling.document_converter import DocumentConverter
            except ImportError as exc:
                raise RuntimeError(
                    "Docling não está instalado. Adicione 'docling' às dependências do projeto."
                ) from exc

            self._docling_converter = DocumentConverter()

        return self._docling_converter

    def _extract_file_text_with_docling(self, file_bytes: bytes, suffix: str) -> str:
        """Converte um arquivo suportado pelo Docling e exporta o resultado em Markdown."""
        converter = self._get_docling_converter()

        with tempfile.NamedTemporaryFile(suffix=suffix or ".bin", delete=False) as temp_file:
            temp_file.write(file_bytes)
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            result = converter.convert(str(temp_path))
            return result.document.export_to_markdown().strip()
        finally:
            temp_path.unlink(missing_ok=True)

    def _extract_drive_file_text(self, service, drive_file: dict, extraction_method: str) -> str:
        if extraction_method == EXTRACTION_METHOD_DOCLING:
            plan = self._build_docling_file_plan(drive_file)
            if not plan:
                raise RuntimeError(f"Tipo de arquivo não suportado pelo Docling: {drive_file.get('mimeType')}")

            if plan["mode"] == "export":
                file_bytes = self._export_google_workspace_file_bytes(
                    service,
                    drive_file["id"],
                    plan["export_mime_type"],
                )
            else:
                file_bytes = self._download_drive_file_bytes(service, drive_file["id"])

            if plan["suffix"] in SPREADSHEET_SUFFIXES:
                try:
                    spreadsheet_text = extract_spreadsheet_markdown(
                        file_bytes=file_bytes,
                        suffix=plan["suffix"],
                        file_name=drive_file.get("name") or "spreadsheet",
                    ).strip()
                    if spreadsheet_text:
                        return spreadsheet_text
                except Exception:
                    pass

            return self._extract_file_text_with_docling(file_bytes, plan["suffix"])

        pdf_bytes = self._download_drive_file_bytes(service, drive_file["id"])
        return self._extract_pdf_text_with_pypdf(pdf_bytes)

    def _safe_filename(self, name: str) -> str:
        """Remove caracteres especiais do nome do arquivo."""
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
        return cleaned or "document"

    # ------------------------------------------------------------------ #
    # SALVAR COLEÇÃO
    # ------------------------------------------------------------------ #

    def ingest_folder_to_collection(
        self,
        folder_name="rag",
        collection_name="google_drive_rag",
        credentials=None,
        extraction_method=EXTRACTION_METHOD_PYPDF,
    ):
        """
        Baixa todos os arquivos suportados de uma pasta do Drive,
        extrai o texto e salva como arquivos .md em uma coleção local.
        """
        extraction_method = self._normalize_extraction_method(extraction_method)
        service = self._get_drive_service(credentials or self.login())

        # Lista os arquivos disponíveis para o extrator escolhido
        listing = self.list_supported_files(
            folder_name=folder_name,
            extraction_method=extraction_method,
            credentials=credentials,
        )
        if listing.get("message"):
            raise RuntimeError(listing["message"])

        files = listing.get("files", [])
        if not files:
            if extraction_method == EXTRACTION_METHOD_DOCLING:
                raise RuntimeError(f"Nenhum arquivo compatível com Docling encontrado na pasta '{folder_name}'.")
            raise RuntimeError(f"Nenhum PDF encontrado na pasta '{folder_name}'.")

        # Cria (ou limpa) a pasta da coleção local
        collection_path = self.collections_root / collection_name
        collection_path.mkdir(parents=True, exist_ok=True)
        for old_file in collection_path.glob("*.md"):
            old_file.unlink()

        # Baixa cada arquivo suportado e salva como .md
        saved_files = []
        for index, drive_file in enumerate(files, start=1):
            text = self._extract_drive_file_text(service, drive_file, extraction_method).strip()
            if not text:
                continue  # Pula arquivos sem conteúdo textual extraível

            safe_name = self._safe_filename(Path(drive_file["name"]).stem)
            output_path = collection_path / f"{index:02d}_{safe_name}.md"
            output_path.write_text(
                f"# {drive_file['name']}\n\nExtraction method: {extraction_method}\n\n{text}\n",
                encoding="utf-8",
            )
            saved_files.append(
                {
                    "id": drive_file["id"],
                    "name": drive_file["name"],
                    "mime_type": drive_file.get("mimeType"),
                    "extraction_method": extraction_method,
                }
            )

        if not saved_files:
            if extraction_method == EXTRACTION_METHOD_DOCLING:
                raise RuntimeError("Arquivos compatíveis encontrados, mas nenhum conteúdo pôde ser extraído com Docling.")
            raise RuntimeError("PDFs encontrados, mas nenhum texto pôde ser extraído.")

        return {
            "collection_name": collection_name,
            "folder_name": listing["folder_name"],
            "extraction_method": extraction_method,
            "files": saved_files,
        }
