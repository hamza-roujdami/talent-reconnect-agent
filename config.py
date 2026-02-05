"""Configuration management for Talent Reconnect Agent."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration from environment variables."""
    
    # Azure AI Foundry
    project_endpoint: str = os.environ.get("PROJECT_ENDPOINT", "")
    model_primary: str = os.environ.get("FOUNDRY_MODEL_PRIMARY", "gpt-4o-mini")
    embedding_model: str = os.environ.get("FOUNDRY_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Foundry IQ Knowledge Bases
    search_endpoint: str = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
    resumes_kb_name: str = os.environ.get("RESUMES_KB_NAME", "resumes-kb")
    feedback_kb_name: str = os.environ.get("FEEDBACK_KB_NAME", "feedback-kb")
    resumes_kb_connection: str = os.environ.get("RESUMES_KB_CONNECTION", "resumes-kb-mcp")
    feedback_kb_connection: str = os.environ.get("FEEDBACK_KB_CONNECTION", "feedback-kb-mcp")
    
    # Memory (long-term cross-session)
    enable_memory: bool = os.environ.get("ENABLE_MEMORY", "true").lower() == "true"
    
    # Server
    host: str = os.environ.get("HOST", "0.0.0.0")
    port: int = int(os.environ.get("PORT", "8000"))
    
    def validate(self) -> list[str]:
        """Check required config is set. Returns list of missing vars."""
        missing = []
        
        if not self.project_endpoint:
            missing.append("PROJECT_ENDPOINT")
        
        if not self.search_endpoint:
            missing.append("AZURE_SEARCH_ENDPOINT")
        
        return missing


# Global config instance
config = Config()
