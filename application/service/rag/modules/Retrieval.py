"""Composable retrieval mixins."""
# Simple: Find relevant documents from the knowledge base

from .retrieval.Aggregation import RetrievalAggregationMixin
from .retrieval.Agents import RetrievalAgentMixin
from .retrieval.Clarification import RetrievalClarificationMixin
from .retrieval.Core import RetrievalCoreMixin
from .retrieval.Intents import RetrievalIntentMixin


class RetrievalMixin(
    RetrievalIntentMixin,
    RetrievalClarificationMixin,
    RetrievalAggregationMixin,
    RetrievalAgentMixin,
    RetrievalCoreMixin,
):
    pass
