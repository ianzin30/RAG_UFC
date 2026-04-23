"""Thin public facade for the RAG service."""
# Simple: Main search system that answers questions from documents

# Estes aliases ficam no facade para manter compatibilidade com testes antigos.
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.vectorstores import FAISS

from .modules.DocumentResolution import DocumentResolutionMixin
from .modules.Prompting import PromptingMixin
from .modules.Retrieval import RetrievalMixin
from .modules.Routing import RoutingMixin
from .modules.Spreadsheet import SpreadsheetMixin
from .modules.TextProcessing import TextProcessingMixin
from .parts.Bootstrap import RAGServiceBootstrapMixin
from .parts.CollectionLoading import RAGServiceCollectionLoadingMixin
from .parts.Diagnostics import RAGServiceDiagnosticsMixin
from .parts.FocusState import RAGServiceFocusStateMixin
from .parts.Planning import RAGServicePlanningMixin
from .parts.QuestionAnswering import RAGServiceQuestionAnsweringMixin
from .parts.Selection import RAGServiceSelectionMixin
from .parts.TraceBuilders import RAGServiceTraceBuilderMixin


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
    RAGServiceDiagnosticsMixin,
    RAGServiceCollectionLoadingMixin,
    RAGServiceQuestionAnsweringMixin,
):
    pass
