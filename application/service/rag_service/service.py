"""Thin public facade for the RAG service."""

# Estes aliases ficam no facade para manter compatibilidade com testes antigos.
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.vectorstores import FAISS

from .modules.document_resolution import DocumentResolutionMixin
from .modules.prompting import PromptingMixin
from .modules.retrieval import RetrievalMixin
from .modules.routing import RoutingMixin
from .modules.spreadsheet import SpreadsheetMixin
from .modules.text_processing import TextProcessingMixin
from .service_parts.bootstrap import RAGServiceBootstrapMixin
from .service_parts.collection_loading import RAGServiceCollectionLoadingMixin
from .service_parts.focus_state import RAGServiceFocusStateMixin
from .service_parts.planning import RAGServicePlanningMixin
from .service_parts.question_answering import RAGServiceQuestionAnsweringMixin
from .service_parts.selection import RAGServiceSelectionMixin
from .service_parts.trace_builders import RAGServiceTraceBuilderMixin


# Esta classe junta os blocos pequenos que formam o comportamento completo do RAG.
class RAGService(
    PromptingMixin,
    SpreadsheetMixin,
    RetrievalMixin,
    DocumentResolutionMixin,
    RoutingMixin,
    TextProcessingMixin,
    RAGServiceBootstrapMixin,
    RAGServiceFocusStateMixin,
    RAGServiceSelectionMixin,
    RAGServicePlanningMixin,
    RAGServiceTraceBuilderMixin,
    RAGServiceCollectionLoadingMixin,
    RAGServiceQuestionAnsweringMixin,
):
    pass
