from aegis_shared.contracts import AgentType

from app.config import Settings
from app.observability import NoopTelemetry, Telemetry, build_telemetry
from app.observability.telemetry import configure_langsmith
from app.runner import run_analysis


class RecordingTelemetry(Telemetry):
    """Test spy: captures records without any OTel dependency."""

    def __init__(self) -> None:
        self.agent_runs: list = []
        self.workflows: list = []

    def record_agent_run(self, record) -> None:
        self.agent_runs.append(record)

    def record_workflow(self, **kwargs) -> None:
        self.workflows.append(kwargs)


def test_build_telemetry_defaults_to_noop():
    tel = build_telemetry(Settings(otel_enabled=False))
    assert isinstance(tel, NoopTelemetry)


def test_disabled_otel_even_when_requested_without_libs_is_safe():
    # otel libs are not installed in the base env -> must degrade to noop, not crash.
    tel = build_telemetry(Settings(otel_enabled=True, otel_exporter_otlp_endpoint=None))
    assert isinstance(tel, Telemetry)  # never raises


def test_langsmith_not_enabled_without_key(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    configure_langsmith(Settings(langsmith_tracing=True, langsmith_api_key=None))
    import os

    assert os.environ.get("LANGSMITH_TRACING") is None


async def test_metrics_recorded_for_full_run(deps):
    spy = RecordingTelemetry()
    deps.telemetry = spy

    await run_analysis("NVDA", deps=deps, enable_debate=True, max_debate_rounds=3)

    # 5 analysts + portfolio manager
    assert len(spy.agent_runs) == 6
    assert AgentType.PORTFOLIO_MANAGER in {r.agent_type for r in spy.agent_runs}
    # exactly one workflow summary, marked not-failed
    assert len(spy.workflows) == 1
    assert spy.workflows[0]["failed"] is False
    assert spy.workflows[0]["num_agents"] == 6
