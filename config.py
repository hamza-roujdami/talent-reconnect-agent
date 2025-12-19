"""
Configuration Management

All settings are loaded from environment variables (.env file).
See .env.example for required variables.
"""
import os
from dataclasses import dataclass
from typing import Optional, Literal
from dotenv import load_dotenv

load_dotenv()


# LLM Provider type
LLMProvider = Literal["azure_openai", "compass", "openai"]


@dataclass
class LLMConfig:
    """LLM configuration - supports Azure OpenAI, Compass, or OpenAI."""
    provider: LLMProvider
    model: str
    # For Compass/OpenAI (API key auth)
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    # For Azure OpenAI
    azure_endpoint: Optional[str] = None
    azure_deployment: Optional[str] = None
    use_entra_id: bool = False  # Use Azure AD auth instead of API key


@dataclass
class SearchConfig:
    """Azure AI Search configuration - for resume database."""
    endpoint: str
    key: str
    index: str
    enabled: bool


@dataclass
class Config:
    """Application configuration."""
    llm: LLMConfig
    search: SearchConfig
    use_mock_data: bool = True
    debug: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
        
        # Determine LLM provider
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        compass_key = os.getenv("COMPASS_API_KEY", "")
        
        if azure_endpoint:
            # Azure OpenAI (Entra ID auth by default if no API key)
            llm_config = LLMConfig(
                provider="azure_openai",
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
                azure_endpoint=azure_endpoint,
                azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
                api_key=os.getenv("AZURE_OPENAI_KEY"),  # Optional - uses Entra ID if not set
                use_entra_id=not os.getenv("AZURE_OPENAI_KEY"),
            )
        elif compass_key:
            # Compass/Core42 API
            llm_config = LLMConfig(
                provider="compass",
                model=os.getenv("COMPASS_MODEL", "gpt-4.1"),
                api_key=compass_key,
                base_url=os.getenv("COMPASS_BASE_URL", "https://api.core42.ai/v1"),
            )
        else:
            # Default/fallback - will fail if nothing configured
            llm_config = LLMConfig(
                provider="compass",
                model="gpt-4.1",
                api_key="",
                base_url="https://api.core42.ai/v1",
            )
        
        return cls(
            llm=llm_config,
            search=SearchConfig(
                endpoint=search_endpoint,
                key=os.getenv("AZURE_SEARCH_KEY", ""),
                index=os.getenv("AZURE_SEARCH_INDEX", "resumes"),
                enabled=bool(search_endpoint),
            ),
            use_mock_data=os.getenv("USE_MOCK_DATA", "true").lower() == "true",
            debug=os.getenv("DEBUG", "false").lower() == "true",
        )


# Global singleton
config = Config.from_env()
