import os

from application.service.rag.CrewAiTelemetry import disable_crewai_telemetry_by_default


def test_crewai_telemetry_is_disabled_by_default(monkeypatch) -> None:
    for key in (
        "OTEL_SDK_DISABLED",
        "CREWAI_DISABLE_TELEMETRY",
        "CREWAI_DISABLE_TRACKING",
        "CREWAI_TRACING_ENABLED",
    ):
        monkeypatch.delenv(key, raising=False)

    disable_crewai_telemetry_by_default()

    assert os.environ["OTEL_SDK_DISABLED"] == "true"
    assert os.environ["CREWAI_DISABLE_TELEMETRY"] == "true"
    assert os.environ["CREWAI_DISABLE_TRACKING"] == "true"
    assert os.environ["CREWAI_TRACING_ENABLED"] == "false"


def test_crewai_telemetry_defaults_do_not_override_explicit_env(monkeypatch) -> None:
    monkeypatch.setenv("CREWAI_DISABLE_TELEMETRY", "false")

    disable_crewai_telemetry_by_default()

    assert os.environ["CREWAI_DISABLE_TELEMETRY"] == "false"

