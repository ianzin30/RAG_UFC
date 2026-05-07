"""Telegram bot handlers for Google Drive document ingestion and RAG chat.

Manages the flow of logging in with Google Drive, selecting extraction method,
importing documents, and answering questions about them via chat.
"""
from ..GoogleDrive import GoogleDriveService
from ..rag.RagService import RAGService
from .ExtractionSelection import format_extraction_method

# nome da pasta no Google Drive onde os arquivos devem estar para serem importados
DRIVE_FOLDER_NAME = "RAG"


def build_collection_name(user_id: int, extraction_method: str) -> str:
    return f"google_drive_rag_{user_id}_{extraction_method}"


def format_files_count(files_count: int) -> str:
    return f"{files_count} arquivo" if files_count == 1 else f"{files_count} arquivos"


def build_loaded_collection_label(extraction_method: str) -> str:
    return f"documentos do Google Drive extraidos com {format_extraction_method(extraction_method)}"


def build_login_intro_messages(extraction_method: str) -> tuple[str, str]:
    extractor_label = format_extraction_method(extraction_method)
    intro = (
        f"Extrator configurado para o Google Drive: {extractor_label}.\n\n"
        "Para continuar, clique em /login para conectar o Google Drive 🔐"
    )
    details = (
        f"📂 Depois disso, eu importo os arquivos compatíveis da pasta '{DRIVE_FOLDER_NAME}' usando {extractor_label}.\n"
        "💬 Assim que tudo estiver pronto, libero o chat para voce conversar com os documentos.\n"
        "🔁 Se quiser refazer a importação, use /extractor."
    )
    return intro, details


def build_ready_message(files_count: int, extraction_method: str) -> str:
    return (
        f"Tudo certo por aqui. Ja estou com {format_files_count(files_count)} carregados "
        f"usando {format_extraction_method(extraction_method)} e pronto para responder as suas perguntas.\n"
        "Se quiser refazer a importação do Google Drive, use /extractor."
    )


def build_success_caption(files_count: int, folder_name: str, extraction_method: str) -> str:
    return (
        "🎉 Tudo pronto.\n\n"
        f"📄 Encontrei {format_files_count(files_count)} na pasta '{folder_name}'.\n"
        f"🧠 Extrator usado: {format_extraction_method(extraction_method)}.\n"
        "💬 Agora voce ja pode conversar comigo sobre os documentos."
    )


def login_google_drive():
    drive_service = GoogleDriveService()
    credentials = drive_service.login()
    return drive_service, credentials


def prepare_chat_from_drive(user_id: int, drive_service: GoogleDriveService, credentials, extraction_method: str):
    result = drive_service.ingest_folder_to_collection(
        folder_name=DRIVE_FOLDER_NAME,
        collection_name=build_collection_name(user_id, extraction_method),
        credentials=credentials,
        extraction_method=extraction_method,
    )
    rag_service = RAGService(collection_name=result["collection_name"])
    rag_service.collection_name = build_loaded_collection_label(extraction_method)
    return result, rag_service
