"""Historical import name for ``rag_ufc_core.llm_client`` (Track A, checks, tests).

The module object is the core one, so errors raised by core providers match
``except llm_client.LLMError`` here. The research checkout's ``.env`` stays the
default for ``LLMSettings.from_env()``.
"""
from pathlib import Path
import sys

from rag_ufc_core import llm_client as _client

_client.DEFAULT_ENV = Path(__file__).resolve().parent / '.env'
sys.modules[__name__] = _client
