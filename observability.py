"""
Observability Configuration - OpenTelemetry Setup for Azure AI Foundry

Configures tracing, logging, and metrics for Talent Reconnect.
Supports Azure AI Foundry, Application Insights, and local exporters.

Environment Variables:
    APPLICATIONINSIGHTS_CONNECTION_STRING: Azure App Insights connection (for Foundry tracing)
    OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (e.g., http://localhost:4317 for Aspire)
    OTEL_SERVICE_NAME: Service name for traces (default: talent-reconnect)
    ENABLE_CONSOLE_TRACING: Set to "true" for console trace output
    ENABLE_INSTRUMENTATION: Set to "true" to enable MAF instrumentation
    ENABLE_SENSITIVE_DATA: Set to "true" to include prompts/responses in traces

Usage:
    from observability import configure_observability
    configure_observability()  # Call once at startup - auto-detects Foundry/AppInsights
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Track if observability is already configured
_configured = False


def configure_observability(
    *,
    service_name: Optional[str] = None,
    enable_console: Optional[bool] = None,
    enable_sensitive_data: bool = False,
) -> bool:
    """Configure OpenTelemetry observability for the application.
    
    Auto-detects and configures:
    1. Azure Application Insights (if APPLICATIONINSIGHTS_CONNECTION_STRING is set)
    2. OTLP exporter (if OTEL_EXPORTER_OTLP_ENDPOINT is set, e.g., Aspire Dashboard)
    3. Console output (if ENABLE_CONSOLE_TRACING=true or enable_console=True)
    
    Args:
        service_name: Override service name (default: OTEL_SERVICE_NAME or 'talent-reconnect')
        enable_console: Enable console exporters for local debugging
        enable_sensitive_data: Include message content in traces (default: False for privacy)
    
    Returns:
        True if observability was configured, False if already configured or unavailable
    """
    global _configured
    
    if _configured:
        logger.debug("Observability already configured, skipping")
        return False
    
    # Resolve settings
    resolved_service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "talent-reconnect")
    resolved_console = enable_console if enable_console is not None else (
        os.getenv("ENABLE_CONSOLE_TRACING", "").lower() == "true"
    )
    
    # Set service name env var if not already set (MAF reads this)
    if not os.getenv("OTEL_SERVICE_NAME"):
        os.environ["OTEL_SERVICE_NAME"] = resolved_service_name
    
    # Check for Azure Application Insights (Foundry tracing)
    appinsights_conn = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if appinsights_conn:
        success = _configure_azure_monitor(appinsights_conn, enable_sensitive_data)
        if success:
            _configured = True
            return True
    
    # Fall back to standard OTLP/console configuration
    try:
        from agent_framework.observability import configure_otel_providers
    except ImportError:
        logger.warning(
            "agent_framework.observability not available. "
            "Install with: pip install agent-framework"
        )
        return False
    
    try:
        # Configure OpenTelemetry via MAF
        configure_otel_providers(
            enable_console_exporters=resolved_console,
            enable_sensitive_data=enable_sensitive_data,
        )
        _configured = True
        
        # Log configuration summary
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        
        logger.info(
            f"📊 Observability configured | service={resolved_service_name} | "
            f"console={resolved_console} | otlp={'✓' if otlp_endpoint else '✗'}"
        )
        return True
        
    except Exception as e:
        logger.warning(f"Failed to configure observability: {e}")
        return False


def _configure_azure_monitor(connection_string: str, enable_sensitive_data: bool = False) -> bool:
    """Internal: Configure Azure Monitor/Application Insights."""
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor as azure_configure
        from agent_framework.observability import create_resource, enable_instrumentation
        
        # Disable features that cause issues on macOS
        azure_configure(
            connection_string=connection_string,
            resource=create_resource(),
            enable_live_metrics=False,  # Avoid performance counter issues on macOS
            logger_name="talent-reconnect",  # Only capture our logs
        )
        enable_instrumentation(enable_sensitive_data=enable_sensitive_data)
        
        logger.info("📊 Azure Monitor configured (Application Insights + Foundry tracing)")
        return True
        
    except ImportError:
        logger.warning(
            "azure-monitor-opentelemetry not installed. "
            "Install with: pip install azure-monitor-opentelemetry"
        )
        return False
    except Exception as e:
        logger.warning(f"Failed to configure Azure Monitor: {e}")
        return False


def configure_azure_monitor(connection_string: Optional[str] = None) -> bool:
    """Configure Azure Application Insights for production monitoring.
    
    Args:
        connection_string: App Insights connection string (or uses APPLICATIONINSIGHTS_CONNECTION_STRING)
    
    Returns:
        True if configured successfully
    """
    conn_str = connection_string or os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    if not conn_str:
        logger.warning(
            "Azure Monitor not configured. Set APPLICATIONINSIGHTS_CONNECTION_STRING "
            "or pass connection_string parameter."
        )
        return False
    
    return _configure_azure_monitor(conn_str)
