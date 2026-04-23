"""Composable retrieval mixins."""
# Simple: Find relevant documents from the knowledge base

from .retrieval.Aggregation import RetrievalAggregationMixin
from .retrieval.Agents import RetrievalAgentMixin
from .retrieval.Clarification import RetrievalClarificationMixin
from .retrieval.Core import RetrievalCoreMixin
from .retrieval.Evidence import RetrievalEvidenceMixin
from .retrieval.Intents import RetrievalIntentMixin
from .retrieval.Spreadsheet import SpreadsheetRetrievalMixin


class RetrievalMixin(
    RetrievalIntentMixin,
    RetrievalClarificationMixin,
    RetrievalEvidenceMixin,
    RetrievalAggregationMixin,
    RetrievalAgentMixin,
    SpreadsheetRetrievalMixin,
    RetrievalCoreMixin,
):
    pass
