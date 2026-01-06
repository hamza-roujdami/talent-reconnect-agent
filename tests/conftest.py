"""
Pytest configuration and shared fixtures.
"""
import asyncio
import os
import subprocess
import sys
import warnings
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
import pytest

# Suppress aiohttp warnings from Azure SDK
warnings.filterwarnings("ignore", message="Unclosed client session")
warnings.filterwarnings("ignore", message="Unclosed connector")

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests (may require external services)")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def workflow():
    """Create the recruiting workflow (shared across tests)."""
    from agents.factory import create_recruiting_workflow
    return create_recruiting_workflow()


@pytest.fixture(scope="module")
async def running_server() -> AsyncGenerator[str, None]:
    """Start the FastAPI server for API tests.
    
    Yields the base URL when server is ready.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    
    # Wait for server to be ready
    async with httpx.AsyncClient() as client:
        for _ in range(30):
            try:
                resp = await client.get(f"{BASE_URL}/health", timeout=2.0)
                if resp.status_code == 200:
                    break
            except Exception:
                pass
            await asyncio.sleep(0.5)
        else:
            proc.terminate()
            pytest.fail("Server failed to start within 15 seconds")
    
    yield BASE_URL
    
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture
def http_client():
    """Create an async HTTP client."""
    return httpx.AsyncClient(timeout=120.0)
