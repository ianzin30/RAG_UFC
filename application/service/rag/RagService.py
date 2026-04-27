"""Main RAG service — question answering from document collections.

Aggregates functionality from multiple specialized mixins (retrieval, routing,
document resolution, planning, selection, diagnostics, etc.) to provide a
unified interface for loading collections and answering questions with full
tracing for debugging.
"""
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.vectorstores import FAISS

from .modules.AnswerProcessing import AnswerProcessingMixin
from .modules.ChunkExpansion import ChunkExpansionMixin
from .modules.DocumentResolution import DocumentResolutionMixin
from .modules.GraderPayloadOptimization import GraderPayloadOptimizationMixin
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


class RAGService(
    AnswerProcessingMixin,
    ChunkExpansionMixin,
    GraderPayloadOptimizationMixin,
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
    """Unified RAG service combining all retrieval, answering, and diagnostic capabilities.

    Aggregates specialized mixins to provide methods for:
    - Loading document collections and building FAISS indices
    - Answering questions with full context tracing
    - Disambiguating queries and resolving document focus
    - Planning retrieval scope and selecting relevant chunks
    - Generating formatted prompts and extracting answers from LLM responses
    - Capturing comprehensive diagnostics for debugging

    Usage: load_collection() → ask_question_with_trace() → returns full trace dict.
    """

    pass
