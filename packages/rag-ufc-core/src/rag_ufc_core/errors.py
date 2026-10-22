"""Exceptions applications may catch, without importing engine internals.

``ProviderError`` (and ``InputBudgetError``, which carries ``code`` and
``public_message``) come from model providers; ``LLMError`` and its subclasses
from the Spark client. Their messages are safe to show: no prompts, credentials
or raw server responses.
"""

from .llm_client import LLMConnectionError, LLMError
from .rag.v2.Providers import ProviderError
from .rag.v2.Spark import InputBudgetError

__all__ = ["InputBudgetError", "LLMConnectionError", "LLMError", "ProviderError"]
