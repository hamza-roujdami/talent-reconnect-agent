"""
Configuration Management

All settings are loaded from environment variables (.env file).
See .env.example for required variables.
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMConfig:
    """LLM configuration - connects to Compass/Core42 API."""
    api_key: str
    base_url: str
    model: str


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
        return cls(
            llm=LLMConfig(
                api_key=os.getenv("COMPASS_API_KEY", ""),
                base_url=os.getenv("COMPASS_BASE_URL", "https://api.core42.ai/v1"),
                model=os.getenv("COMPASS_MODEL", "gpt-4.1"),
            ),
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
