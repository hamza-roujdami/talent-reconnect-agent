"""Foundry V2 Agent Factory.

Manages agent lifecycle and chat interactions with Azure AI Foundry.
Uses built-in AzureAISearchAgentTool for search operations.

Usage:
    async with AgentFactory() as factory:
        response = await factory.chat("Find Python developers in Dubai")
        print(response)
"""

import os
from dataclasses import dataclass, field
from typing import AsyncIterator
from contextlib import asynccontextmanager

from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from dotenv import load_dotenv

from .definitions import get_agent_definitions, AGENT_KEYS
from . import orchestrator

load_dotenv()


# =============================================================================
# Configuration
# =============================================================================

# Connection name (from Foundry project connections)
SEARCH_CONNECTION_NAME = os.environ.get("AZURE_AI_SEARCH_CONNECTION_NAME", "")


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Agent:
    """V2 agent reference."""
    name: str
    version: int
    key: str  # orchestrator, search, etc.


@dataclass 
class Session:
    """Conversation session with history."""
    history: list[dict] = field(default_factory=list)
    current_agent: str = "orchestrator"
    
    def add_message(self, role: str, content: str, agent: str = None):
        self.history.append({
            "role": role,
            "content": content,
            "agent": agent or self.current_agent,
        })


# =============================================================================
# Agent Factory
# =============================================================================

class AgentFactory:
    """Factory for Foundry V2 agents with built-in tools."""
    
    def __init__(
        self, 
        endpoint: str = None, 
        model: str = None,
        persist_agents: bool = True,
    ):
        self.endpoint = endpoint or os.environ.get("PROJECT_ENDPOINT")
        self.model = model or os.environ.get("FOUNDRY_MODEL_PRIMARY", "gpt-4o-mini")
        self.persist_agents = persist_agents
        
        self._credential = None
        self._client = None
        self._openai = None
        self._agents: dict[str, Agent] = {}
        self._search_connection_id: str = None
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, *args):
        await self.cleanup()
    
    async def initialize(self):
        """Initialize client and create/load agents."""
        self._credential = DefaultAzureCredential()
        self._client = AIProjectClient(
            endpoint=self.endpoint,
            credential=self._credential,
        )
        self._openai = self._client.get_openai_client()
        
        # Get Azure AI Search connection ID (required)
        if not SEARCH_CONNECTION_NAME:
            raise RuntimeError(
                "AZURE_AI_SEARCH_CONNECTION_NAME required. "
                "Create a connection in your Foundry project and set this variable."
            )
        
        try:
            connection = await self._client.connections.get(SEARCH_CONNECTION_NAME)
            self._search_connection_id = connection.id
            print(f"✓ Search connection: {SEARCH_CONNECTION_NAME}")
        except Exception as e:
            raise RuntimeError(
                f"Failed to get search connection '{SEARCH_CONNECTION_NAME}'. "
                f"Error: {e}"
            )
        
        # Get agent definitions with built-in search tools
        definitions = get_agent_definitions(
            search_connection_id=self._search_connection_id,
        )
        
        # Always create new versions to pick up instruction changes
        # (Foundry persists agents, but we want fresh instructions each time)
        for key, config in definitions.items():
            agent = await self._client.agents.create_version(
                agent_name=key,
                definition=PromptAgentDefinition(
                    model=self.model,
                    instructions=config["instructions"],
                    tools=config.get("tools", []),
                ),
            )
            self._agents[key] = Agent(name=agent.name, version=agent.version, key=key)
            print(f"✓ Created {key} (v{agent.version})")
    
    async def cleanup(self):
        """Close connections (agents persist in Foundry)."""
        if self._openai:
            await self._openai.close()
        if self._client:
            await self._client.close()
        if self._credential:
            await self._credential.close()
    
    async def delete_agents(self):
        """Explicitly delete all agents (for cleanup)."""
        for agent in self._agents.values():
            try:
                await self._client.agents.delete_version(
                    agent_name=agent.name,
                    agent_version=agent.version,
                )
                print(f"✗ Deleted {agent.key}")
            except Exception as e:
                print(f"  Error deleting {agent.key}: {e}")
    
    async def chat(self, message: str, agent_key: str = "orchestrator", history: list[dict] = None) -> str:
        """Send a message to an agent and get response.
        
        Args:
            message: Current user message
            agent_key: Which agent to use
            history: Optional conversation history [{"role": "user/assistant", "content": "..."}]
        """
        agent = self._agents.get(agent_key)
        if not agent:
            raise ValueError(f"Unknown agent: {agent_key}")
        
        # Build input with history if provided
        if history:
            # Format history for the model
            input_messages = []
            for msg in history:
                input_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })
            # Add current message
            input_messages.append({"role": "user", "content": message})
            input_data = input_messages
        else:
            input_data = message
        
        response = await self._openai.responses.create(
            input=input_data,
            tool_choice="auto",
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        )
        
        # Foundry handles built-in search tools automatically
        return response.output_text or ""
    
    async def chat_stream(self, message: str, agent_key: str = "orchestrator") -> AsyncIterator[str]:
        """Stream a response from an agent."""
        agent = self._agents.get(agent_key)
        if not agent:
            raise ValueError(f"Unknown agent: {agent_key}")
        
        stream = await self._openai.responses.create(
            stream=True,
            input=message,
            tool_choice="auto",
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        )
        
        async for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta
    
    def route(self, message: str) -> str:
        """Route message to appropriate agent."""
        return orchestrator.route(message)
    
    async def orchestrate(self, message: str, session: Session = None) -> tuple[str, str]:
        """Route message to appropriate agent and get response.
        
        Returns:
            Tuple of (response_text, agent_key)
        """
        agent_key = self.route(message)
        
        if session:
            session.current_agent = agent_key
            session.add_message("user", message)
        
        response = await self.chat(message, agent_key)
        
        if session:
            session.add_message("assistant", response, agent_key)
        
        return response, agent_key
    
    @property
    def agents(self) -> dict[str, Agent]:
        """Get all agents."""
        return self._agents


# =============================================================================
# Convenience Functions
# =============================================================================

@asynccontextmanager
async def create_factory(**kwargs):
    """Async context manager for factory."""
    factory = AgentFactory(**kwargs)
    try:
        await factory.initialize()
        yield factory
    finally:
        await factory.cleanup()


async def quick_chat(message: str, agent: str = "orchestrator") -> str:
    """One-off chat without managing lifecycle."""
    async with create_factory() as factory:
        return await factory.chat(message, agent)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "AgentFactory",
    "Agent",
    "Session",
    "create_factory",
    "quick_chat",
    "AGENT_KEYS",
]

# Backwards compatibility
AGENTS = AGENT_KEYS
