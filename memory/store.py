"""Foundry Memory Store manager.

Provides long-term memory across sessions:
- User profile: Preferences, hiring patterns, preferred locations
- Chat summaries: Distilled conversation topics for continuity

Usage:
    manager = MemoryManager(project_client)
    await manager.initialize()
    
    # Get memory tool for agents
    tool = manager.get_memory_tool(user_id="user_123")
"""

import os
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
    MemorySearchTool,
)


class MemoryManager:
    """Manages Foundry Memory Store for recruiter preferences."""
    
    MEMORY_STORE_NAME = "talent-reconnect-memory"
    
    def __init__(self, client: AIProjectClient):
        self._client = client
        self._store = None
        self._chat_model = os.environ.get("FOUNDRY_MODEL_PRIMARY", "gpt-4o-mini")
        self._embedding_model = os.environ.get("FOUNDRY_EMBEDDING_MODEL", "text-embedding-3-small")
        self._enabled = os.environ.get("ENABLE_MEMORY", "true").lower() == "true"
    
    @property
    def enabled(self) -> bool:
        """Check if memory is enabled."""
        return self._enabled and self._store is not None
    
    async def initialize(self) -> bool:
        """Initialize or get existing memory store.
        
        Returns True if memory is ready, False if disabled or failed.
        """
        if not self._enabled:
            print("⚠️  Memory disabled (ENABLE_MEMORY=false)")
            return False
        
        try:
            # Check if store already exists
            stores = self._client.memory_stores.list()
            async for store in stores:
                if store.name == self.MEMORY_STORE_NAME:
                    self._store = store
                    print(f"✓ Memory store: {self.MEMORY_STORE_NAME}")
                    return True
            
            # Create new memory store
            options = MemoryStoreDefaultOptions(
                chat_summary_enabled=True,
                user_profile_enabled=True,
                user_profile_details=(
                    "Store recruiter preferences including: "
                    "preferred candidate skills, locations, seniority levels, "
                    "hiring patterns, past successful hires, "
                    "communication preferences. "
                    "Avoid storing sensitive personal data like salaries or private contact info."
                ),
            )
            
            definition = MemoryStoreDefaultDefinition(
                chat_model=self._chat_model,
                embedding_model=self._embedding_model,
                options=options,
            )
            
            self._store = await self._client.memory_stores.create(
                name=self.MEMORY_STORE_NAME,
                definition=definition,
                description="Long-term memory for Talent Reconnect recruiting assistant",
            )
            print(f"✓ Created memory store: {self.MEMORY_STORE_NAME}")
            return True
            
        except Exception as e:
            print(f"⚠️  Memory initialization failed: {e}")
            print("   Continuing without long-term memory")
            self._enabled = False
            return False
    
    def get_memory_tool(self, user_id: str, update_delay: int = 60) -> MemorySearchTool | None:
        """Get a memory search tool for a specific user.
        
        Args:
            user_id: Unique identifier for the user (scope for memory)
            update_delay: Seconds of inactivity before memories are saved (default 60)
            
        Returns:
            MemorySearchTool configured for the user, or None if memory disabled
        """
        if not self.enabled:
            return None
        
        return MemorySearchTool(
            memory_store_name=self.MEMORY_STORE_NAME,
            scope=user_id,
            update_delay=update_delay,
        )
    
    async def search_memories(
        self,
        user_id: str,
        query: str | None = None,
        max_memories: int = 5,
    ) -> list[dict]:
        """Search memories for a user.
        
        Args:
            user_id: User scope
            query: Search query (None for static profile memories)
            max_memories: Max results to return
            
        Returns:
            List of memory items with content
        """
        if not self.enabled:
            return []
        
        try:
            from azure.ai.projects.models import MemorySearchOptions, ResponsesUserMessageItemParam
            
            items = None
            if query:
                items = [ResponsesUserMessageItemParam(content=query)]
            
            response = await self._client.memory_stores.search_memories(
                name=self.MEMORY_STORE_NAME,
                scope=user_id,
                items=items,
                options=MemorySearchOptions(max_memories=max_memories),
            )
            
            return [
                {"id": m.memory_item.memory_id, "content": m.memory_item.content}
                for m in response.memories
            ]
        except Exception as e:
            print(f"⚠️  Memory search failed: {e}")
            return []
    
    async def delete_user_memories(self, user_id: str) -> bool:
        """Delete all memories for a user (GDPR compliance).
        
        Args:
            user_id: User scope to delete
            
        Returns:
            True if deleted successfully
        """
        if not self.enabled:
            return False
        
        try:
            await self._client.memory_stores.delete_scope(
                name=self.MEMORY_STORE_NAME,
                scope=user_id,
            )
            return True
        except Exception as e:
            print(f"⚠️  Memory deletion failed: {e}")
            return False


__all__ = ["MemoryManager"]
