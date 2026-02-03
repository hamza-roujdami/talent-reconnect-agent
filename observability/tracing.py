"""OpenTelemetry tracing with Azure AI Foundry + Azure Monitor.

Uses Foundry's native enable_telemetry() for agent/tool tracing,
plus Azure Monitor for App Insights export.

Usage:
    from observability import setup_telemetry
    
    # Call once at startup
    await setup_telemetry()
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


async def setup_telemetry(project_client=None) -> bool:
    """Configure OpenTelemetry with Foundry + Azure Monitor.
    
    Args:
        project_client: Optional AIProjectClient. If provided, gets
                       connection string from Foundry project.
    
    Returns:
        True if telemetry was configured, False if skipped
    """
    # Try to get connection string from Foundry project first
    connection_string = None
    
    if project_client:
        try:
            connection_string = project_client.telemetry.get_application_insights_connection_string()
            logger.info("✓ Got App Insights connection from Foundry project")
        except Exception as e:
            logger.debug(f"Could not get connection string from project: {e}")
    
    # Fall back to environment variable
    if not connection_string:
        connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    
    if not connection_string:
        logger.info("No App Insights connection string - telemetry disabled")
        return False
    
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        
        # Configure Azure Monitor with App Insights
        configure_azure_monitor(
            connection_string=connection_string,
            enable_live_metrics=True,
        )
        
        logger.info("✓ Azure Monitor telemetry configured")
        return True
        
    except ImportError as e:
        logger.warning(f"Telemetry packages not installed: {e}")
        return False
    except Exception as e:
        logger.warning(f"Failed to configure telemetry: {e}")
        return False


def enable_foundry_tracing():
    """Enable Foundry SDK telemetry for agent/tool tracing.
    
    This instruments azure-ai-agents, azure-ai-inference, and
    other GenAI libraries for detailed tracing.
    
    Uses AIAgentsInstrumentor from azure.ai.agents.telemetry.
    """
    # Enable content recording for debugging (set to "true" in dev, "false" in prod)
    if os.environ.get("AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED") is None:
        os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "false"
    
    # Configure Azure SDK to use OpenTelemetry
    try:
        from azure.core.settings import settings
        settings.tracing_implementation = "opentelemetry"
    except Exception:
        pass  # Not critical
    
    instrumented = False
    
    # 1. Try AIAgentsInstrumentor (azure-ai-agents SDK)
    try:
        from azure.ai.agents.telemetry import AIAgentsInstrumentor
        AIAgentsInstrumentor().instrument()
        logger.info("✓ AIAgentsInstrumentor enabled")
        instrumented = True
    except ImportError:
        logger.debug("AIAgentsInstrumentor not available")
    except Exception as e:
        logger.debug(f"AIAgentsInstrumentor failed: {e}")
    
    # 2. Try AIInferenceInstrumentor (azure-ai-inference SDK)
    try:
        from azure.ai.inference.tracing import AIInferenceInstrumentor
        AIInferenceInstrumentor().instrument()
        logger.info("✓ AIInferenceInstrumentor enabled")
        instrumented = True
    except ImportError:
        logger.debug("AIInferenceInstrumentor not available")
    except Exception as e:
        logger.debug(f"AIInferenceInstrumentor failed: {e}")
    
    if instrumented:
        return True
    else:
        logger.warning("No Foundry instrumentors available - agent calls won't be traced")
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
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    status = message.get("status", 200)
                    span.set_attribute("http.status_code", status)
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
