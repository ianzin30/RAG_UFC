"""Typed payloads used by the scraping service."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScrapeOutcome:
    ok: bool
    files: int = 0
    message: str | None = None
    source: str | None = None
    strategy: str | None = None
    target_url: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "files": self.files,
            "message": self.message,
            "source": self.source,
            "strategy": self.strategy,
            "target_url": self.target_url,
            "error": self.error,
        }
