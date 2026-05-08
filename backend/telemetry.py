"""OpenTelemetry bootstrap (optional)."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def init_telemetry() -> None:
    if (os.getenv("OTEL_SDK_DISABLED") or "").strip().lower() in ("1", "true", "yes"):
        return
    endpoint = (os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip()
    if not endpoint:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        service_name = (os.getenv("OTEL_SERVICE_NAME") or "donald-api").strip()
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        traces_url = endpoint.rstrip("/") + "/v1/traces"
        exporter = OTLPSpanExporter(endpoint=traces_url)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry tracing enabled traces_url=%s", traces_url)
    except Exception as exc:
        logger.warning("OpenTelemetry init failed: %s", exc)
