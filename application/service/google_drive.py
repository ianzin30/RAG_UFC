import json
import os
import re
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pypdf import PdfReader

from .collections.contracts import NormalizedDocument, SpreadsheetModel
from .collections.document_normalizer import DocumentNormalizer
from .collections.repository import CollectionRepository
from .extractors.docling_pure import DoclingPureExtractor
from .spreadsheets.markdown import (
    extract_spreadsheet_csv_children,
    extract_spreadsheet_markdown,
    extract_spreadsheet_markdown_via_csv,
)
from .spreadsheets.normalizer import SpreadsheetNormalizer

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

# Permissões que pedimos ao Google: apenas leitura do Drive
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
EXTRACTION_METHOD_PYPDF = "pypdf"
EXTRACTION_METHOD_DOCLING = "docling"
EXTRACTION_METHOD_DOCLING_PURE = "docling-puro"
EXTRACTION_METHOD_DOC_CSV = "doc-csv"
SUPPORTED_EXTRACTION_METHODS = {
    EXTRACTION_METHOD_PYPDF,
    EXTRACTION_METHOD_DOCLING,
    EXTRACTION_METHOD_DOCLING_PURE,
    EXTRACTION_METHOD_DOC_CSV,
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
        self.credentials_file = root_dir / "google-oauth-credentials.json"
        self._docling_pure_extractor = DoclingPureExtractor()
        self._collection_repository = CollectionRepository(root_dir)
        self._document_normalizer = DocumentNormalizer()
        self._spreadsheet_normalizer = SpreadsheetNormalizer()

    # ------------------------------------------------------------------ #
    # AUTENTICAÇÃO
    # ------------------------------------------------------------------ #

    def login(self):
        """Abre o navegador para o usuário fazer login com a conta Google."""
        config = json.loads(self.credentials_file.read_text(encoding="utf-8"))
        flow = InstalledAppFlow.from_client_config(config, SCOPES)
        return flow.run_local_server(
            port=0,
            open_browser=True,
            prompt="select_account",
            access_type="offline",
            include_granted_scopes="false",
        )

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
        if extraction_method in {
            EXTRACTION_METHOD_DOCLING,
            EXTRACTION_METHOD_DOCLING_PURE,
            EXTRACTION_METHOD_DOC_CSV,
        }:
            supported_files = [drive_file for drive_file in files if self._build_docling_file_plan(drive_file)]
        else:
            supported_files = [drive_file for drive_file in files if drive_file.get("mimeType") == PDF_MIME_TYPE]

        return {
            "folder_name": folder["name"],
            "files": supported_files,
            "message": None,
        }

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

    def _build_doc_csv_child_document_id(self, parent_document_id: str, sheet_name: str, position: int) -> str:
        safe_sheet = re.sub(r"[^A-Za-z0-9._-]+", "_", sheet_name or "").strip("._")
        if not safe_sheet:
            safe_sheet = f"sheet_{position}"
        return f"{parent_document_id}__{safe_sheet}"

    def _build_doc_csv_child_markdown(self, workbook_name: str, sheet_name: str, csv_text: str) -> str:
        return (
            f"Workbook: {workbook_name}\n"
            f"Sheet: {sheet_name}\n"
            f"Spreadsheet route: csv-per-sheet\n\n"
            f"```csv\n{csv_text.rstrip()}\n```"
        ).strip()

    def _build_doc_csv_child_text(self, workbook_name: str, sheet_name: str, csv_text: str) -> str:
        return (
            f"Workbook: {workbook_name}\n"
            f"Sheet: {sheet_name}\n"
            f"Spreadsheet route: csv-per-sheet\n\n"
            f"{csv_text.rstrip()}"
        ).strip()

    def _build_doc_csv_spreadsheet_documents(
        self,
        index: int,
        drive_file: dict,
        extraction_method: str,
        file_bytes: bytes,
        suffix: str,
    ) -> list[NormalizedDocument]:
        display_name = drive_file.get("name") or f"document_{index}"

        if suffix == ".csv":
            content_markdown = extract_spreadsheet_markdown(
                file_bytes=file_bytes,
                suffix=suffix,
                file_name=display_name,
                route_label="csv-direct",
            ).strip()
            spreadsheet_model = self._spreadsheet_normalizer.normalize(
                display_name,
                content_markdown,
                suffix.lstrip("."),
            )
            return [
                self._document_normalizer.normalize_drive_document(
                    index=index,
                    drive_file=drive_file,
                    extraction_method=extraction_method,
                    content_markdown=content_markdown,
                    spreadsheet_model=spreadsheet_model,
                )
            ]

        content_markdown = extract_spreadsheet_markdown_via_csv(
            file_bytes=file_bytes,
            suffix=suffix,
            file_name=display_name,
        ).strip()
        spreadsheet_model = self._spreadsheet_normalizer.normalize(
            display_name,
            content_markdown,
            suffix.lstrip("."),
        )
        parent_document = self._document_normalizer.normalize_drive_document(
            index=index,
            drive_file=drive_file,
            extraction_method=extraction_method,
            content_markdown=content_markdown,
            spreadsheet_model=spreadsheet_model,
        )
        parent_document.catalog_visibility = "visible"
        parent_document.component_kind = "spreadsheet_parent"
        parent_document.component_name = None
        parent_document.parent_document_id = None
        parent_document.logical_item_id = parent_document.document_id
        parent_document.logical_item_name = display_name
        parent_document.logical_item_kind = "file"

        child_documents = []
        for position, child in enumerate(extract_spreadsheet_csv_children(file_bytes, suffix), start=1):
            sheet_name = child["sheet_name"]
            csv_text = child["csv_text"]
            child_document_id = self._build_doc_csv_child_document_id(
                parent_document.document_id,
                sheet_name,
                position,
            )
            child_display_name = f"{display_name}::{sheet_name}.csv"
            child_content_markdown = self._build_doc_csv_child_markdown(display_name, sheet_name, csv_text)
            child_content_text = self._build_doc_csv_child_text(display_name, sheet_name, csv_text)
            child_documents.append(
                NormalizedDocument(
                    document_id=child_document_id,
                    display_name=child_display_name,
                    document_type="text_document",
                    source_kind="google_drive",
                    source_metadata={
                        "id": drive_file.get("id"),
                        "mime_type": drive_file.get("mimeType"),
                        "name": display_name,
                        "sheet_name": sheet_name,
                    },
                    extraction_method=extraction_method,
                    content_markdown_path="",
                    content_text=child_content_text,
                    summary=self._document_normalizer.extract_summary(child_content_text),
                    structured_data=None,
                    content_markdown=child_content_markdown,
                    logical_item_id=parent_document.document_id,
                    logical_item_name=display_name,
                    logical_item_kind="file",
                    catalog_visibility="internal",
                    parent_document_id=parent_document.document_id,
                    component_kind="csv_sheet_child",
                    component_name=sheet_name,
                )
            )

        return [parent_document, *child_documents]

    def _extract_drive_documents(self, service, drive_file: dict, extraction_method: str, index: int) -> list[NormalizedDocument]:
        if extraction_method in {
            EXTRACTION_METHOD_DOCLING,
            EXTRACTION_METHOD_DOCLING_PURE,
            EXTRACTION_METHOD_DOC_CSV,
        }:
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

            if extraction_method == EXTRACTION_METHOD_DOC_CSV and plan["suffix"] in SPREADSHEET_SUFFIXES:
                return self._build_doc_csv_spreadsheet_documents(
                    index=index,
                    drive_file=drive_file,
                    extraction_method=extraction_method,
                    file_bytes=file_bytes,
                    suffix=plan["suffix"],
                )

            if extraction_method == EXTRACTION_METHOD_DOCLING and plan["suffix"] in SPREADSHEET_SUFFIXES:
                try:
                    content_markdown = extract_spreadsheet_markdown(
                        file_bytes=file_bytes,
                        suffix=plan["suffix"],
                        file_name=drive_file.get("name") or "spreadsheet",
                    ).strip()
                    if content_markdown:
                        spreadsheet_model = self._spreadsheet_normalizer.normalize(
                            drive_file.get("name") or "spreadsheet",
                            content_markdown,
                            plan["suffix"].lstrip("."),
                        )
                        return [
                            self._document_normalizer.normalize_drive_document(
                                index=index,
                                drive_file=drive_file,
                                extraction_method=extraction_method,
                                content_markdown=content_markdown,
                                spreadsheet_model=spreadsheet_model if isinstance(spreadsheet_model, SpreadsheetModel) else None,
                            )
                        ]
                except Exception:
                    pass

            content_markdown = self._docling_pure_extractor.extract_markdown(file_bytes, plan["suffix"])
            spreadsheet_model = None
            if plan["suffix"] in SPREADSHEET_SUFFIXES:
                spreadsheet_model = self._spreadsheet_normalizer.normalize(
                    drive_file.get("name") or "spreadsheet",
                    content_markdown,
                    plan["suffix"].lstrip("."),
                )
            return [
                self._document_normalizer.normalize_drive_document(
                    index=index,
                    drive_file=drive_file,
                    extraction_method=extraction_method,
                    content_markdown=content_markdown,
                    spreadsheet_model=spreadsheet_model if isinstance(spreadsheet_model, SpreadsheetModel) else None,
                )
            ]

        pdf_bytes = self._download_drive_file_bytes(service, drive_file["id"])
        content_markdown = self._extract_pdf_text_with_pypdf(pdf_bytes)
        return [
            self._document_normalizer.normalize_drive_document(
                index=index,
                drive_file=drive_file,
                extraction_method=extraction_method,
                content_markdown=content_markdown,
                spreadsheet_model=None,
            )
        ]

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
            if extraction_method in {
                EXTRACTION_METHOD_DOCLING,
                EXTRACTION_METHOD_DOCLING_PURE,
                EXTRACTION_METHOD_DOC_CSV,
            }:
                raise RuntimeError(f"Nenhum arquivo compatível com o extrator '{extraction_method}' encontrado na pasta '{folder_name}'.")
            raise RuntimeError(f"Nenhum PDF encontrado na pasta '{folder_name}'.")

        normalized_documents = []
        saved_files = []
        for index, drive_file in enumerate(files, start=1):
            extracted_documents = self._extract_drive_documents(service, drive_file, extraction_method, index)
            extracted_documents = [
                document
                for document in extracted_documents
                if (document.content_markdown or "").strip() or (document.content_text or "").strip()
            ]
            if not extracted_documents:
                continue  # Pula arquivos sem conteúdo textual extraível

            normalized_documents.extend(extracted_documents)
            saved_files.append(
                {
                    "id": drive_file["id"],
                    "name": drive_file["name"],
                    "mime_type": drive_file.get("mimeType"),
                    "extraction_method": extraction_method,
                }
            )

        if not normalized_documents:
            if extraction_method in {
                EXTRACTION_METHOD_DOCLING,
                EXTRACTION_METHOD_DOCLING_PURE,
                EXTRACTION_METHOD_DOC_CSV,
            }:
                raise RuntimeError(
                    f"Arquivos compatíveis encontrados, mas nenhum conteúdo pôde ser extraído com '{extraction_method}'."
                )
            raise RuntimeError("PDFs encontrados, mas nenhum texto pôde ser extraído.")

        self._collection_repository.save_collection(
            collection_name=collection_name,
            source_kind="google_drive",
            extraction_method=extraction_method,
            documents=normalized_documents,
        )

        return {
            "collection_name": collection_name,
            "folder_name": listing["folder_name"],
            "extraction_method": extraction_method,
            "files": saved_files,
        }
