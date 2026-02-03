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


def enable_foundry_tracing(destination=None):
    """Enable Foundry SDK telemetry for agent/tool tracing.
    
    This instruments azure-ai-agents, azure-ai-inference, and
    other GenAI libraries for detailed tracing.
    
    Args:
        destination: Optional. Set to sys.stdout for console output,
                    or OTLP endpoint string for local dev.
    """
    # Enable content recording for debugging (disable in prod)
    if os.environ.get("AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED") is None:
        os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "false"
    
    try:
        from azure.ai.projects import enable_telemetry
        
        # Enable Foundry SDK telemetry
        enable_telemetry(destination=destination)
        logger.info("✓ Foundry agent tracing enabled")
        return True
        
    except ImportError:
        # Try the agents package directly
        try:
            from azure.ai.agents.telemetry import enable_telemetry
            enable_telemetry(destination=destination)
            logger.info("✓ Foundry agent tracing enabled (via agents SDK)")
            return True
        except ImportError:
            logger.debug("Foundry telemetry not available")
            return False
    except Exception as e:
        logger.warning(f"Failed to enable Foundry tracing: {e}")
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
