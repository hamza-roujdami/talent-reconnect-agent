"""Cosmos DB session storage for multi-agent conversations.

Uses Azure Cosmos DB for persistent session storage while keeping
Responses API for flexible multi-agent routing.

Usage:
    store = CosmosSessionStore()
    await store.initialize()
    
    # Create/get session
    session = await store.get_session(session_id)
    
    # Add messages
    await store.add_message(session_id, "user", "Find Python devs")
    await store.add_message(session_id, "assistant", "I found 5...", agent="search")
    
    # Get history
    history = await store.get_history(session_id)
"""

import os
from datetime import datetime
from typing import Optional

from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()


class CosmosSessionStore:
    """Persistent session storage using Cosmos DB."""
    
    def __init__(
        self,
        endpoint: str = None,
        database_name: str = "talent-reconnect",
        container_name: str = "sessions",
    ):
        self.endpoint = endpoint or os.environ.get("COSMOS_ENDPOINT", "")
        self.database_name = database_name
        self.container_name = container_name
        
        self._credential = None
        self._client = None
        self._database = None
        self._container = None
    
    async def initialize(self):
        """Connect to Cosmos DB and ensure database/container exist."""
        if not self.endpoint:
            raise ValueError(
                "COSMOS_ENDPOINT not set. Add it to your .env file.\n"
                "Get it from Azure Portal → Cosmos DB → Overview → URI"
            )
        
        self._credential = DefaultAzureCredential()
        self._client = CosmosClient(
            url=self.endpoint,
            credential=self._credential,
        )
        
        # Get existing database and container (created via Azure CLI/Bicep)
        self._database = self._client.get_database_client(self.database_name)
        self._container = self._database.get_container_client(self.container_name)
        
        # Verify connection works by reading container properties
        await self._container.read()
        
        print(f"✓ Cosmos DB: {self.database_name}/{self.container_name}")
    
    async def close(self):
        """Close connections."""
        if self._client:
            await self._client.close()
        if self._credential:
            await self._credential.close()
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
    # =========================================================================
    # Session CRUD
    # =========================================================================
    
    async def create_session(self, session_id: str, title: str = None) -> dict:
        """Create a new session."""
        now = datetime.utcnow().isoformat()
        session = {
            "id": session_id,
            "session_id": session_id,  # Partition key
            "title": title,
            "messages": [],
            "current_agent": "orchestrator",
            "created_at": now,
            "updated_at": now,
        }
        
        await self._container.create_item(body=session)
        return session
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session by ID, returns None if not found."""
        try:
            return await self._container.read_item(
                item=session_id,
                partition_key=session_id,
            )
        except Exception:
            return None
    
    async def get_or_create_session(self, session_id: str) -> dict:
        """Get existing session or create new one."""
        session = await self.get_session(session_id)
        if session is None:
            session = await self.create_session(session_id)
        return session
    
    async def update_session(self, session_id: str, updates: dict) -> dict:
        """Update session fields."""
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        
        updates["updated_at"] = datetime.utcnow().isoformat()
        session.update(updates)
        
        await self._container.replace_item(
            item=session_id,
            body=session,
        )
        return session
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if deleted, False if not found."""
        try:
            await self._container.delete_item(
                item=session_id,
                partition_key=session_id,
            )
            return True
        except Exception:
            return False
    
    # =========================================================================
    # Message Operations
    # =========================================================================
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent: str = None,
    ) -> dict:
        """Add a message to session history."""
        session = await self.get_or_create_session(session_id)
        
        message = {
            "role": role,
            "content": content,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        session["messages"].append(message)
        session["updated_at"] = datetime.utcnow().isoformat()
        
        # Set title from first user message
        if not session["title"] and role == "user":
            session["title"] = content[:50] + ("..." if len(content) > 50 else "")
        
        await self._container.replace_item(
            item=session_id,
            body=session,
        )
        
        return message
    
    async def get_history(
        self,
        session_id: str,
        max_messages: int = None,
    ) -> list[dict]:
        """Get message history for a session.
        
        Returns list of {"role": "user/assistant", "content": "..."} dicts
        suitable for passing to Responses API.
        """
        session = await self.get_session(session_id)
        if session is None:
            return []
        
        messages = session.get("messages", [])
        
        if max_messages:
            messages = messages[-max_messages:]
        
        # Return format compatible with Responses API
        return [{"role": m["role"], "content": m["content"]} for m in messages]
    
    async def set_current_agent(self, session_id: str, agent: str):
        """Update the current agent for a session."""
        await self.update_session(session_id, {"current_agent": agent})
    
    # =========================================================================
    # Listing
    # =========================================================================
    
    async def list_sessions(self, limit: int = 50) -> list[dict]:
        """List recent sessions (newest first)."""
        query = """
        SELECT c.id, c.session_id, c.title, c.created_at, c.updated_at,
               ARRAY_LENGTH(c.messages) as message_count
        FROM c
        ORDER BY c.updated_at DESC
        OFFSET 0 LIMIT @limit
        """
        
        sessions = []
        async for item in self._container.query_items(
            query=query,
            parameters=[{"name": "@limit", "value": limit}],
        ):
            sessions.append(item)
        
        return sessions


# =============================================================================
# Fallback In-Memory Store (for development/testing)
# =============================================================================

class InMemorySessionStore:
    """In-memory session store for local development."""
    
    def __init__(self):
        self._sessions: dict[str, dict] = {}
    
    async def initialize(self):
        print("✓ Using in-memory session storage")
    
    async def close(self):
        pass
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
    async def create_session(self, session_id: str, title: str = None) -> dict:
        now = datetime.utcnow().isoformat()
        session = {
            "id": session_id,
            "session_id": session_id,
            "title": title,
            "messages": [],
            "current_agent": "orchestrator",
            "created_at": now,
            "updated_at": now,
        }
        self._sessions[session_id] = session
        return session
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        return self._sessions.get(session_id)
    
    async def get_or_create_session(self, session_id: str) -> dict:
        if session_id not in self._sessions:
            return await self.create_session(session_id)
        return self._sessions[session_id]
    
    async def update_session(self, session_id: str, updates: dict) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        
        updates["updated_at"] = datetime.utcnow().isoformat()
        session.update(updates)
        return session
    
    async def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent: str = None,
    ) -> dict:
        session = await self.get_or_create_session(session_id)
        
        message = {
            "role": role,
            "content": content,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        session["messages"].append(message)
        session["updated_at"] = datetime.utcnow().isoformat()
        
        if not session["title"] and role == "user":
            session["title"] = content[:50] + ("..." if len(content) > 50 else "")
        
        return message
    
    async def get_history(
        self,
        session_id: str,
        max_messages: int = None,
    ) -> list[dict]:
        session = self._sessions.get(session_id)
        if session is None:
            return []
        
        messages = session.get("messages", [])
        if max_messages:
            messages = messages[-max_messages:]
        
        return [{"role": m["role"], "content": m["content"]} for m in messages]
    
    async def set_current_agent(self, session_id: str, agent: str):
        await self.update_session(session_id, {"current_agent": agent})
    
    async def list_sessions(self, limit: int = 50) -> list[dict]:
        sessions = sorted(
            self._sessions.values(),
            key=lambda x: x.get("updated_at", ""),
            reverse=True,
        )[:limit]
        
        return [
            {
                "id": s["id"],
                "session_id": s["session_id"],
                "title": s.get("title"),
                "created_at": s.get("created_at"),
                "updated_at": s.get("updated_at"),
                "message_count": len(s.get("messages", [])),
            }
            for s in sessions
        ]


# =============================================================================
# Factory
# =============================================================================

def create_session_store():
    """Create appropriate session store based on config.
    
    Uses Cosmos DB if COSMOS_ENDPOINT is set, otherwise falls back to in-memory.
    """
    endpoint = os.environ.get("COSMOS_ENDPOINT", "")
    database = os.environ.get("COSMOS_DATABASE", "talent-reconnect")
    container = os.environ.get("COSMOS_CONTAINER", "sessions")
    
    if endpoint:
        return CosmosSessionStore(
            endpoint=endpoint,
            database_name=database,
            container_name=container,
        )
    else:
        return InMemorySessionStore()
