"""Shared test fixtures and configuration."""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="session")
def project_endpoint():
    """Get project endpoint from environment."""
    endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not endpoint:
        pytest.skip("PROJECT_ENDPOINT not set")
    return endpoint


@pytest.fixture(scope="session")
def search_endpoint():
    """Get search endpoint from environment."""
    endpoint = os.environ.get("SEARCH_SERVICE_ENDPOINT") or os.environ.get("AZURE_SEARCH_ENDPOINT")
    if not endpoint:
        pytest.skip("SEARCH_SERVICE_ENDPOINT not set")
    return endpoint


@pytest.fixture(scope="session")
def search_api_key():
    """Get search API key from environment."""
    key = os.environ.get("SEARCH_SERVICE_API_KEY") or os.environ.get("AZURE_SEARCH_API_KEY")
    if not key:
        pytest.skip("SEARCH_SERVICE_API_KEY not set")
    return key
