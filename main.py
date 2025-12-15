"""
Talent Reconnect Agent - Main Entry Point

API server for the talent acquisition workflow.
Run with: python main.py
"""
import uvicorn
from api import app
from config import config


def main():
    """Run the API server."""
    source = "Azure AI Search" if not config.use_mock_data else "Mock Data"
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║            Talent Reconnect - AI Recruiting Agent            ║
╠══════════════════════════════════════════════════════════════╣
║  Model:      {config.llm.model:<46} ║
║  Resumes:    {source:<46} ║
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
