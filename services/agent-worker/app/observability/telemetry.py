"""Telemetry facade.

A single ``Telemetry`` interface with two implementations:

* ``NoopTelemetry`` — the default; zero overhead, no dependencies.
* ``OtelTelemetry`` — real OpenTelemetry traces + metrics over OTLP.

The rest of the code depends only on the facade, so instrumentation is fully
optional: with OTel disabled or its libraries absent, the system runs untouched.

Telemetry is deliberately decoupled from the graph layer (records are typed ``Any``
and accessed by duck-typing) to avoid import cycles.
"""

from __future__ import annotations

import logging
import os
from contextlib import nullcontext
from typing import Any, ContextManager

from ..config import Settings

logger = logging.getLogger("aegis.worker.telemetry")


class Telemetry:
    """No-op base. Every method is a safe default."""

    def workflow_span(self, *, ticker: str, request_id: str) -> ContextManager[Any]:
        return nullcontext()

    def node_span(self, name: str, **attributes: Any) -> ContextManager[Any]:
        return nullcontext()

    def record_agent_run(self, record: Any) -> None:  # AgentRunRecord (duck-typed)
        return None

    def record_workflow(
        self,
        *,
        ticker: str,
        outcome: str,
        duration_ms: float,
        failed: bool,
        num_agents: int,
        debate_rounds: int,
    ) -> None:
        return None

    def shutdown(self) -> None:
        return None


class NoopTelemetry(Telemetry):
    """Explicit no-op (identical to the base; named for clarity at call sites)."""


class OtelTelemetry(Telemetry):
    def __init__(self, settings: Settings) -> None:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        endpoint = settings.otel_exporter_otlp_endpoint or "http://localhost:4317"
        resource = Resource.create({"service.name": settings.otel_service_name})

        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
        )
        trace.set_tracer_provider(tracer_provider)

        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=endpoint, insecure=True),
            export_interval_millis=settings.metrics_export_interval_ms,
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(meter_provider)

        self._tracer_provider = tracer_provider
        self._meter_provider = meter_provider
        self._tracer = trace.get_tracer("aegis.agent_worker")

        meter = metrics.get_meter("aegis.agent_worker")
        self._m_agent_duration = meter.create_histogram(
            "aegis.agent.duration.ms", description="Per-agent execution time"
        )
        self._m_agent_tokens = meter.create_counter(
            "aegis.agent.tokens", description="LLM tokens by agent and direction"
        )
        self._m_agent_cost = meter.create_counter(
            "aegis.agent.cost_usd", description="LLM cost by agent (USD)"
        )
        self._m_wf_duration = meter.create_histogram(
            "aegis.workflow.duration.ms", description="End-to-end analysis time"
        )
        self._m_wf_count = meter.create_counter(
            "aegis.workflow.count", description="Completed/failed analyses"
        )
        self._m_debate_rounds = meter.create_histogram(
            "aegis.debate.rounds", description="Debate rounds per analysis"
        )

    def workflow_span(self, *, ticker: str, request_id: str):
        return self._tracer.start_as_current_span(
            "workflow.analyze",
            attributes={"aegis.ticker": ticker, "aegis.request_id": request_id},
        )

    def node_span(self, name: str, **attributes: Any):
        attrs = {f"aegis.{k}": v for k, v in attributes.items() if v is not None}
        return self._tracer.start_as_current_span(name, attributes=attrs)

    def record_agent_run(self, record: Any) -> None:
        attrs = {
            "agent_type": record.agent_type.value,
            "status": record.status.value,
        }
        if record.latency_ms is not None:
            self._m_agent_duration.record(record.latency_ms, attrs)
        self._m_agent_tokens.add(record.tokens_in, {**attrs, "direction": "in"})
        self._m_agent_tokens.add(record.tokens_out, {**attrs, "direction": "out"})
        self._m_agent_cost.add(record.cost_usd, {"agent_type": record.agent_type.value})

    def record_workflow(
        self,
        *,
        ticker: str,
        outcome: str,
        duration_ms: float,
        failed: bool,
        num_agents: int,
        debate_rounds: int,
    ) -> None:
        self._m_wf_duration.record(duration_ms, {"outcome": outcome})
        self._m_wf_count.add(1, {"status": "failed" if failed else "complete"})
        if debate_rounds:
            self._m_debate_rounds.record(debate_rounds, {})

    def shutdown(self) -> None:
        try:
            self._tracer_provider.shutdown()
            self._meter_provider.shutdown()
        except Exception:  # pragma: no cover
            pass


def configure_langsmith(settings: Settings) -> None:
    """Enable LangGraph's native LangSmith tracing via environment (opt-in)."""
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
        os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)


def build_telemetry(settings: Settings) -> Telemetry:
    configure_langsmith(settings)
    if not settings.otel_enabled:
        return NoopTelemetry()
    try:
        return OtelTelemetry(settings)
    except Exception as exc:  # missing libs / bad endpoint -> degrade to no-op
        logger.warning("OpenTelemetry init failed (%s); telemetry disabled", exc)
        return NoopTelemetry()
