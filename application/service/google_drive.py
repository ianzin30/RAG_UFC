import json
import os
import re
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pypdf import PdfReader

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

# Permissões que pedimos ao Google: apenas leitura do Drive
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class GoogleDriveService:

    def __init__(self):
        # Caminho raiz do projeto (3 níveis acima deste arquivo)
        root_dir = Path(__file__).resolve().parents[2]
        # Arquivo com as credenciais OAuth do Google Cloud Console
        self.credentials_file = root_dir / "google-oauth-credentials.json"
        # Pasta onde as coleções de documentos são salvas
        self.collections_root = root_dir / "data" / "collections"

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

    def list_pdfs(self, folder_name="rag", credentials=None):
        """
        Lista todos os PDFs dentro de uma pasta do Drive.
        Retorna um dicionário com o nome da pasta e a lista de arquivos.
        """
        service = self._get_drive_service(credentials or self.login())

        folder = self._find_folder(service, folder_name)
        if not folder:
            return {"folder_name": folder_name, "files": [], "message": f"Pasta '{folder_name}' não encontrada."}

        query = f"'{folder['id']}' in parents and trashed = false and mimeType = 'application/pdf'"
        result = service.files().list(q=query, fields="files(id, name, mimeType)", pageSize=100).execute()

        return {
            "folder_name": folder["name"],
            "files": result.get("files", []),
            "message": None,
        }

    # ------------------------------------------------------------------ #
    # DOWNLOAD E EXTRAÇÃO DE TEXTO
    # ------------------------------------------------------------------ #

    def _download_pdf_text(self, service, file_id: str) -> str:
        """Baixa um PDF do Drive e extrai o texto de todas as páginas."""
        # Faz o download do arquivo para a memória (sem salvar em disco)
        request = service.files().get_media(fileId=file_id)
        buffer = BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        # Lê o PDF e extrai o texto página por página
        buffer.seek(0)
        reader = PdfReader(buffer)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(p.strip() for p in pages if p.strip())

    def _safe_filename(self, name: str) -> str:
        """Remove caracteres especiais do nome do arquivo."""
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
        return cleaned or "document"

    # ------------------------------------------------------------------ #
    # SALVAR COLEÇÃO
    # ------------------------------------------------------------------ #

    def ingest_folder_to_collection(self, folder_name="rag", collection_name="google_drive_rag", credentials=None):
        """
        Baixa todos os PDFs de uma pasta do Drive,
        extrai o texto e salva como arquivos .md em uma coleção local.
        """
        service = self._get_drive_service(credentials or self.login())

        # Lista os PDFs disponíveis
        listing = self.list_pdfs(folder_name=folder_name, credentials=credentials)
        if listing.get("message"):
            raise RuntimeError(listing["message"])

        files = listing.get("files", [])
        if not files:
            raise RuntimeError(f"Nenhum PDF encontrado na pasta '{folder_name}'.")

        # Cria (ou limpa) a pasta da coleção local
        collection_path = self.collections_root / collection_name
        collection_path.mkdir(parents=True, exist_ok=True)
        for old_file in collection_path.glob("*.md"):
            old_file.unlink()

        # Baixa cada PDF e salva como .md
        saved_files = []
        for index, drive_file in enumerate(files, start=1):
            text = self._download_pdf_text(service, drive_file["id"]).strip()
            if not text:
                continue  # Pula PDFs sem texto (ex: PDFs com imagens apenas)

            safe_name = self._safe_filename(Path(drive_file["name"]).stem)
            output_path = collection_path / f"{index:02d}_{safe_name}.md"
            output_path.write_text(f"# {drive_file['name']}\n\n{text}\n", encoding="utf-8")
            saved_files.append({"id": drive_file["id"], "name": drive_file["name"]})

        if not saved_files:
            raise RuntimeError("PDFs encontrados, mas nenhum texto pôde ser extraído.")

        return {
            "collection_name": collection_name,
            "folder_name": listing["folder_name"],
            "files": saved_files,
        }
