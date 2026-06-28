from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

logger = logging.getLogger(__name__)


def setup_tracing(app: FastAPI, settings: Any) -> None:
    """Initialize OpenTelemetry tracing if enabled."""
    if not settings.otel_enabled:
        logger.info("OpenTelemetry tracing is disabled.")
        return

    try:
        provider = TracerProvider()
        
        # Default to Console exporter for local/dev visibility
        processor = SimpleSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        
        trace.set_tracer_provider(provider)
        
        # Instrument FastAPI app
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor().instrument_app(app)
        
        logger.info("OpenTelemetry tracing initialized successfully.")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry tracing: {e}")


def get_tracer() -> trace.Tracer:
    """Get the standard app tracer."""
    return trace.get_tracer("callforce-api")
