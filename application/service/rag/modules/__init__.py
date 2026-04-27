"""RAG core modules — mixins for retrieval, routing, and text processing.

Exports specialized mixins that handle different aspects of the RAG pipeline:
- DocumentResolution: match document references in queries
- Prompting: build answer and small-talk prompts
- Retrieval: dense/lexical search, ranking, selection
- Routing: classify queries as retrieval or casual
- Spreadsheet: extract entities from structured tables
- TextProcessing: normalize and clean text
"""
from .DocumentResolution import DocumentResolutionMixin
from .Prompting import PromptingMixin
from .Retrieval import RetrievalMixin
from .Routing import RoutingMixin
from .Spreadsheet import SpreadsheetMixin
from .TextProcessing import TextProcessingMixin

__all__ = [
    "DocumentResolutionMixin",
    "PromptingMixin",
    "RetrievalMixin",
    "RoutingMixin",
    "SpreadsheetMixin",
    "TextProcessingMixin",
]
