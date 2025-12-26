"""
Talent Reconnect Agent - Main Entry Point

API server for the talent acquisition workflow.
Run with: python main.py
"""
import logging
import uvicorn
from api import app
from config import config
from observability import configure_observability

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

# Reduce noise from third-party libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("azure").setLevel(logging.WARNING)


def main():
    """Run the API server."""
    # Configure observability (traces, metrics, logs)
    otel_enabled = configure_observability()
    
    source = "Azure AI Search" if not config.use_mock_data else "Mock Data"
    otel_status = "✓ Enabled" if otel_enabled else "✗ Disabled"
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║            Talent Reconnect - AI Recruiting Agent            ║
╠══════════════════════════════════════════════════════════════╣
║  Model:      {config.llm.model:<46} ║
║  Resumes:    {source:<46} ║
║  Telemetry:  {otel_status:<46} ║
║  Server:     http://localhost:8000                           ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=config.debug,
    )


if __name__ == "__main__":
    main()
