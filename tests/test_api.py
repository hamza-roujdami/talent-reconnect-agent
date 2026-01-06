"""
API endpoint tests using pytest.

Run with: pytest tests/test_api.py -v
"""
import json
import pytest

pytestmark = pytest.mark.asyncio


class TestHealthEndpoint:
    """Tests for /health endpoint."""
    
    async def test_health_returns_200(self, running_server, http_client):
        """Health endpoint should return 200 with status healthy."""
        async with http_client:
            resp = await http_client.get(f"{running_server}/health")
        
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "model" in data
        assert "sessions" in data
    
    async def test_health_contains_model_info(self, running_server, http_client):
        """Health response should include model configuration."""
        async with http_client:
            resp = await http_client.get(f"{running_server}/health")
        
        data = resp.json()
        assert data.get("model") is not None


class TestSessionsEndpoint:
    """Tests for session management endpoints."""
    
    async def test_list_sessions(self, running_server, http_client):
        """GET /sessions should return a list."""
        async with http_client:
            resp = await http_client.get(f"{running_server}/sessions")
        
        assert resp.status_code == 200
        data = resp.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)
    
    async def test_delete_nonexistent_session(self, running_server, http_client):
        """DELETE /session/{id} should handle missing sessions gracefully."""
        async with http_client:
            resp = await http_client.delete(f"{running_server}/session/nonexistent-id")
        
        # Should succeed (idempotent delete)
        assert resp.status_code == 200
    
    async def test_get_history_missing_session(self, running_server, http_client):
        """GET /session/{id}/history should 404 for missing sessions."""
        async with http_client:
            resp = await http_client.get(f"{running_server}/session/nonexistent/history")
        
        assert resp.status_code == 404


class TestChatStreamEndpoint:
    """Tests for /chat/stream SSE endpoint."""
    
    async def test_chat_stream_returns_session_id(self, running_server, http_client):
        """Chat stream should return a session ID."""
        session_id = None
        
        async with http_client:
            async with http_client.stream(
                "POST",
                f"{running_server}/chat/stream",
                json={"message": "Hello"},
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        payload = line[6:]
                        if payload == "[DONE]":
                            break
                        try:
                            event = json.loads(payload)
                            if event.get("type") == "session":
                                session_id = event.get("session_id")
                                break
                        except json.JSONDecodeError:
                            continue
        
        assert session_id is not None
    
    async def test_chat_stream_requires_message(self, running_server, http_client):
        """Chat stream should reject empty messages."""
        async with http_client:
            resp = await http_client.post(
                f"{running_server}/chat/stream",
                json={"message": ""},
            )
        
        assert resp.status_code == 422  # Validation error
    
    async def test_chat_stream_activates_agents(self, running_server, http_client):
        """Chat stream should activate at least one agent."""
        agents_seen = []
        
        async with http_client:
            async with http_client.stream(
                "POST",
                f"{running_server}/chat/stream",
                json={"message": "Find a Python developer"},
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        payload = line[6:]
                        if payload == "[DONE]":
                            break
                        try:
                            event = json.loads(payload)
                            if event.get("type") == "agent":
                                agents_seen.append(event.get("name"))
                        except json.JSONDecodeError:
                            continue
        
        assert len(agents_seen) > 0, "Expected at least one agent to be activated"
