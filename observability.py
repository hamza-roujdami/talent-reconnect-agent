"""Observability setup for Talent Reconnect Agent.

Configures OpenTelemetry tracing with Azure Monitor (App Insights) export.
Also enables Foundry agent tracing for detailed agent/tool visibility.

Usage:
    from observability import setup_telemetry
    
    # Call once at startup
    setup_telemetry()
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def setup_telemetry() -> bool:
    """Configure OpenTelemetry with Azure Monitor exporter.
    
    Returns:
        True if telemetry was configured, False if skipped (no connection string)
    """
    connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    
    if not connection_string:
        logger.info("APPLICATIONINSIGHTS_CONNECTION_STRING not set - telemetry disabled")
        return False
    
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        from opentelemetry import trace
        
        # Configure Azure Monitor with App Insights
        configure_azure_monitor(
            connection_string=connection_string,
            enable_live_metrics=True,
        )
        
        # Auto-instrument HTTP clients (optional)
        try:
            from opentelemetry.instrumentation.requests import RequestsInstrumentor
            RequestsInstrumentor().instrument()
        except ImportError:
            pass
        
        try:
            from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
            AioHttpClientInstrumentor().instrument()
        except ImportError:
            pass
        
        logger.info("✓ Telemetry configured (Azure Monitor + OpenTelemetry)")
        return True
        
    except ImportError as e:
        logger.warning(f"Telemetry packages not installed: {e}")
        logger.warning("Install with: pip install azure-monitor-opentelemetry opentelemetry-instrumentation-requests opentelemetry-instrumentation-aiohttp-client")
        return False
    except Exception as e:
        logger.warning(f"Failed to configure telemetry: {e}")
        return False


def get_tracer(name: str = "talent-reconnect"):
    """Get an OpenTelemetry tracer for custom spans.
    
    Usage:
        tracer = get_tracer()
        with tracer.start_as_current_span("my-operation") as span:
            span.set_attribute("agent", "search")
            # ... do work ...
    """
    from opentelemetry import trace
    return trace.get_tracer(name)


def enable_foundry_tracing():
    """Enable Foundry agent SDK tracing.
    
    This enables detailed tracing of agent operations, tool calls,
    and model interactions within Azure AI Foundry.
    """
    try:
        from azure.ai.projects import enable_telemetry
        
        # Enable tracing in the Foundry SDK
        enable_telemetry(destination="azure_monitor")
        logger.info("✓ Foundry agent tracing enabled")
        return True
        
    except ImportError:
        logger.warning("Foundry telemetry not available in this SDK version")
        return False
    except Exception as e:
        logger.warning(f"Failed to enable Foundry tracing: {e}")
        return False


class TracingMiddleware:
    """ASGI middleware for request tracing.
    
    Adds trace context to all incoming requests and logs key metrics.
    """
    
    def __init__(self, app):
        self.app = app
        self.tracer = get_tracer()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        path = scope.get("path", "/")
        method = scope.get("method", "GET")
        
        with self.tracer.start_as_current_span(
            f"{method} {path}",
            attributes={
                "http.method": method,
                "http.path": path,
                "http.scheme": scope.get("scheme", "http"),
            }
        ) as span:
            # Track response status
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    status = message.get("status", 200)
                    span.set_attribute("http.status_code", status)
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
