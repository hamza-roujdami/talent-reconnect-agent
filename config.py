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
    
    # Azure AI Search (via Foundry connection)
    search_connection_name: str = os.environ.get("AZURE_AI_SEARCH_CONNECTION_NAME", "")
    resume_index: str = os.environ.get("SEARCH_RESUME_INDEX", "resumes")
    feedback_index: str = os.environ.get("SEARCH_FEEDBACK_INDEX", "feedback")
    
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
        
        if not self.search_connection_name:
            missing.append("AZURE_AI_SEARCH_CONNECTION_NAME")
        
        return missing


# Global config instance
config = Config()
