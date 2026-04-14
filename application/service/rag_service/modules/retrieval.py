"""Composable retrieval mixins."""

from .retrieval_parts.aggregation import RetrievalAggregationMixin
from .retrieval_parts.agents import RetrievalAgentMixin
from .retrieval_parts.clarification import RetrievalClarificationMixin
from .retrieval_parts.core import RetrievalCoreMixin
from .retrieval_parts.intents import RetrievalIntentMixin
from .retrieval_parts.spreadsheet import SpreadsheetRetrievalMixin


class RetrievalMixin(
    RetrievalIntentMixin,
    RetrievalClarificationMixin,
    RetrievalAggregationMixin,
    RetrievalAgentMixin,
    SpreadsheetRetrievalMixin,
    RetrievalCoreMixin,
):
    pass
