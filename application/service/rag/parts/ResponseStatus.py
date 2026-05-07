"""Lightweight response progress events for interactive UIs."""

from __future__ import annotations

import logging
from collections.abc import Callable


logger = logging.getLogger(__name__)


class RAGServiceResponseStatusMixin:
    def set_response_status_callback(self, callback: Callable[[dict[str, object]], None] | None) -> None:
        self._response_status_callback = callback if callable(callback) else None

    def _emit_response_status(
        self,
        stage: str,
        message: str,
        *,
        mode: str | None = None,
        agent: str | None = None,
    ) -> None:
        callback = getattr(self, "_response_status_callback", None)
        if not callable(callback):
            return

        payload = {
            "stage": str(stage or "").strip() or "processing",
            "message": str(message or "").strip() or "Processando...",
            "mode": str(mode or "").strip() or None,
            "agent": str(agent or "").strip() or None,
        }
        try:
            callback(payload)
        except Exception:
            logger.debug("Response status callback failed.", exc_info=True)
