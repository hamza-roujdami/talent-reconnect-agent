"""Agent Factory - 6-agent recruiting system with long-term memory.

Usage:
    async with AgentFactory() as factory:
        agent_key, response = await factory.orchestrate("Hi")
        if response:
            print(response)  # Orchestrator handled directly
        else:
            print(await factory.chat("Hi", agent_key))
"""

import json
import os
from dataclasses import dataclass

from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    AzureAISearchAgentTool,
    AzureAISearchToolResource,
    AISearchIndexResource,
    AzureAISearchQueryType,
    WebSearchPreviewTool,
    ApproximateLocation,
)
from dotenv import load_dotenv

from . import orchestrator, role_crafter, talent_scout, insight_pulse, connect_pilot, market_radar
from tools import SEND_EMAIL_TOOL
from memory import MemoryManager

load_dotenv()


@dataclass
class Agent:
    """Agent reference."""
    name: str
    version: int
    key: str


class AgentFactory:
    """Creates and manages 6 Foundry agents for recruiting with long-term memory."""
    
    def __init__(self):
        self.endpoint = os.environ.get("PROJECT_ENDPOINT")
        self.model = os.environ.get("FOUNDRY_MODEL_PRIMARY", "gpt-4o-mini")
        self._credential = None
        self._client = None
        self._openai = None
        self._agents: dict[str, Agent] = {}
        self._memory: MemoryManager | None = None
        self._user_agents: dict[str, dict[str, Agent]] = {}  # user_id -> {agent_key -> Agent}
        self._agent_configs: dict[str, dict] = {}  # Store agent configs for per-user creation
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, *args):
        await self.cleanup()
    
    async def initialize(self):
        """Initialize client, memory, and create agents."""
        self._credential = DefaultAzureCredential()
        self._client = AIProjectClient(endpoint=self.endpoint, credential=self._credential)
        self._openai = self._client.get_openai_client()
        
        # Initialize memory store
        self._memory = MemoryManager(self._client)
        await self._memory.initialize()
        
        # Get search connection
        conn_name = os.environ.get("AZURE_AI_SEARCH_CONNECTION_NAME", "")
        if not conn_name:
            raise RuntimeError("AZURE_AI_SEARCH_CONNECTION_NAME required")
        
        connection = await self._client.connections.get(conn_name)
        print(f"✓ Search connection: {conn_name}")
        
        # Build search tools
        def make_search_tool(index: str):
            return AzureAISearchAgentTool(
                azure_ai_search=AzureAISearchToolResource(
                    indexes=[AISearchIndexResource(
                        project_connection_id=connection.id,
                        index_name=index,
                        query_type=AzureAISearchQueryType.SEMANTIC,
                    )]
                )
            )
        
        resume_tool = make_search_tool(os.environ.get("SEARCH_RESUME_INDEX", "resumes"))
        feedback_tool = make_search_tool(os.environ.get("SEARCH_FEEDBACK_INDEX", "feedback"))
        
        # Agent definitions (store for per-user agent creation)
        self._agent_configs = {
            "orchestrator": orchestrator.get_config(),
            "role-crafter": role_crafter.get_config(),
            "talent-scout": talent_scout.get_config(resume_tool),
            "insight-pulse": insight_pulse.get_config(feedback_tool),
            "connect-pilot": connect_pilot.get_config(SEND_EMAIL_TOOL),
        }
        
        # Add MarketRadar with web search
        if os.environ.get("ENABLE_WEB_SEARCH", "true").lower() == "true":
            web_tool = WebSearchPreviewTool(
                user_location=ApproximateLocation(country="AE", city="Dubai", region="Dubai")
            )
            self._agent_configs["market-radar"] = market_radar.get_config(web_tool)
            print("✓ Web Search enabled")
        
        # Create base agents (without per-user memory)
        for key, config in self._agent_configs.items():
            agent = await self._client.agents.create_version(
                agent_name=key,
                definition=PromptAgentDefinition(
                    model=self.model,
                    instructions=config["instructions"],
                    tools=config["tools"],
                ),
            )
            self._agents[key] = Agent(name=agent.name, version=agent.version, key=key)
            print(f"✓ Created {key} (v{agent.version})")
    
    async def cleanup(self):
        """Close connections."""
        if self._openai:
            await self._openai.close()
        if self._client:
            await self._client.close()
        if self._credential:
            await self._credential.close()
    
    async def _get_agent_for_user(self, agent_key: str, user_id: str) -> Agent:
        """Get or create an agent with memory for a specific user.
        
        For agents that benefit from memory (role-crafter), creates a
        user-specific version with MemorySearchTool attached.
        
        Args:
            agent_key: The agent identifier
            user_id: User/session identifier for memory scope
            
        Returns:
            Agent reference (with memory if applicable)
        """
        # Agents that should have memory attached
        MEMORY_AGENTS = {"role-crafter"}  # Profile agent benefits most from memory
        
        # If memory disabled or not a memory agent, use base agent
        if not self.memory_enabled or agent_key not in MEMORY_AGENTS:
            return self._agents[agent_key]
        
        # Check if we already have a user-specific agent
        if user_id in self._user_agents and agent_key in self._user_agents[user_id]:
            return self._user_agents[user_id][agent_key]
        
        # Create user-specific agent with memory tool
        memory_tool = self._memory.get_memory_tool(user_id, update_delay=60)
        config = self._agent_configs[agent_key]
        
        # Add memory tool to existing tools
        tools = list(config.get("tools", [])) + [memory_tool]
        
        agent = await self._client.agents.create_version(
            agent_name=f"{agent_key}-{user_id[:8]}",  # Unique name per user
            definition=PromptAgentDefinition(
                model=self.model,
                instructions=config["instructions"],
                tools=tools,
            ),
        )
        
        # Cache it
        if user_id not in self._user_agents:
            self._user_agents[user_id] = {}
        self._user_agents[user_id][agent_key] = Agent(
            name=agent.name, version=agent.version, key=agent_key
        )
        
        print(f"✓ Created {agent_key} with memory for user {user_id[:8]}...")
        return self._user_agents[user_id][agent_key]
    
    def _build_input(self, message: str, agent_key: str, history: list[dict] = None):
        """Build input with history for an agent call."""
        if history:
            max_history = 6 if agent_key == "market-radar" else 20
            recent = history[-max_history:] if len(history) > max_history else history
            input_data = [{"role": m["role"], "content": m["content"]} for m in recent]
            input_data.append({"role": "user", "content": message})
            return input_data
        return message
    
    async def chat(self, message: str, agent_key: str, history: list[dict] = None, user_id: str = None) -> str:
        """Send message to an agent (non-streaming).
        
        Args:
            message: User message
            agent_key: Which agent to use
            history: Conversation history
            user_id: Optional user ID for memory-enabled agents
        """
        if user_id:
            agent = await self._get_agent_for_user(agent_key, user_id)
        else:
            agent = self._agents.get(agent_key)
            if not agent:
                raise ValueError(f"Unknown agent: {agent_key}")
        
        input_data = self._build_input(message, agent_key, history)
        
        response = await self._openai.responses.create(
            input=input_data,
            tool_choice="auto",
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        )
        return response.output_text or ""
    
    async def chat_stream(self, message: str, agent_key: str, history: list[dict] = None, user_id: str = None):
        """Stream response from an agent. Yields text chunks.
        
        Args:
            message: User message
            agent_key: Which agent to use
            history: Conversation history
            user_id: Optional user ID for memory-enabled agents
        """
        if user_id:
            agent = await self._get_agent_for_user(agent_key, user_id)
        else:
            agent = self._agents.get(agent_key)
            if not agent:
                raise ValueError(f"Unknown agent: {agent_key}")
        
        input_data = self._build_input(message, agent_key, history)
        
        async with await self._openai.responses.create(
            input=input_data,
            tool_choice="auto",
            stream=True,
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        ) as stream:
            async for event in stream:
                if hasattr(event, "type"):
                    if event.type == "response.output_text.delta":
                        yield event.delta
                    elif event.type == "response.output_text.done":
                        break
    
    async def orchestrate(self, message: str, history: list[dict] = None) -> tuple[str, str | None]:
        """Route message via Orchestrator.
        
        Returns (agent_key, direct_response).
        If direct_response is set, orchestrator handled it directly.
        """
        orch = self._agents.get("orchestrator")
        if not orch:
            return "role-crafter", None
        
        # Add context about profile state
        has_profile = any(
            "Profile Ready" in (m.get("content", "") or "")
            for m in (history or [])
            if m.get("role") == "assistant"
        )
        context = f"\n\nContext: Profile {'exists' if has_profile else 'not yet built'}."
        prompt = f"User message: {message}{context}\n\nOutput ONLY the JSON."
        
        try:
            response = await self._openai.responses.create(
                input=prompt,
                extra_body={"agent": {"name": orch.name, "type": "agent_reference"}},
            )
            
            text = response.output_text or ""
            if "{" in text and "}" in text:
                data = json.loads(text[text.index("{"):text.rindex("}")+1])
                agent_key = data.get("agent", "role-crafter")
                
                if agent_key == "orchestrator":
                    return "orchestrator", data.get("response", "How can I help with recruiting?")
                if agent_key in self._agents:
                    return agent_key, None
            
            return "role-crafter", None
            
        except Exception as e:
            print(f"⚠️  Orchestrator error: {e}")
            return "role-crafter", None
    
    # =========================================================================
    # Memory Methods
    # =========================================================================
    
    @property
    def memory_enabled(self) -> bool:
        """Check if long-term memory is enabled."""
        return self._memory is not None and self._memory.enabled
    
    async def get_user_memories(self, user_id: str, query: str | None = None) -> list[dict]:
        """Get memories for a user.
        
        Args:
            user_id: User identifier
            query: Optional search query (None for profile memories)
            
        Returns:
            List of memory items
        """
        if not self._memory:
            return []
        return await self._memory.search_memories(user_id, query)
    
    async def delete_user_memories(self, user_id: str) -> bool:
        """Delete all memories for a user (GDPR compliance).
        
        Args:
            user_id: User identifier
            
        Returns:
            True if deleted
        """
        if not self._memory:
            return False
        return await self._memory.delete_user_memories(user_id)
    
    def get_memory_tool(self, user_id: str):
        """Get memory search tool for a user.
        
        This can be attached to agents to enable automatic memory read/write.
        
        Args:
            user_id: User identifier (scope)
            
        Returns:
            MemorySearchTool or None if memory disabled
        """
        if not self._memory:
            return None
        return self._memory.get_memory_tool(user_id)


__all__ = ["AgentFactory", "Agent"]
