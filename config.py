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
    
    # Azure AI Search
    search_endpoint: str = os.environ.get("SEARCH_SERVICE_ENDPOINT", "") or os.environ.get("AZURE_SEARCH_ENDPOINT", "")
    search_api_key: str = os.environ.get("SEARCH_SERVICE_API_KEY", "") or os.environ.get("AZURE_SEARCH_API_KEY", "")
    resume_index: str = os.environ.get("SEARCH_RESUME_INDEX", "resumes")
    feedback_index: str = os.environ.get("SEARCH_FEEDBACK_INDEX", "feedback")
    
    # Search mode
    use_builtin_search: bool = os.environ.get("USE_BUILTIN_SEARCH", "false").lower() == "true"
    search_connection_name: str = os.environ.get("AZURE_AI_SEARCH_CONNECTION_NAME", "")
    
    # Server
    host: str = os.environ.get("HOST", "0.0.0.0")
    port: int = int(os.environ.get("PORT", "8000"))
    
    def validate(self) -> list[str]:
        """Check required config is set. Returns list of missing vars."""
        missing = []
        
        if not self.project_endpoint:
            missing.append("PROJECT_ENDPOINT")
        
        if not self.use_builtin_search:
            # FunctionTool mode needs API key
            if not self.search_endpoint:
                missing.append("SEARCH_SERVICE_ENDPOINT or AZURE_SEARCH_ENDPOINT")
            if not self.search_api_key:
                missing.append("SEARCH_SERVICE_API_KEY or AZURE_SEARCH_API_KEY")
        else:
            # Built-in mode needs connection name
            if not self.search_connection_name:
                missing.append("AZURE_AI_SEARCH_CONNECTION_NAME")
        
        return missing


# Global config instance
config = Config()
