"""CrewAI telemetry defaults for local/offline runs."""

from __future__ import annotations

import os


def disable_crewai_telemetry_by_default() -> None:
    """Prevent CrewAI from attempting network telemetry unless explicitly re-enabled."""

    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")
    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

