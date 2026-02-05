"""Agent Factory - Creates and manages Foundry agents for recruiting.

This is the core of the multi-agent system. It:
1. Creates 6 specialized agents in Azure AI Foundry
2. Connects them to Foundry IQ Knowledge Bases via MCPTool
3. Routes conversations through an orchestrator

Usage:
    async with AgentFactory() as factory:
        agent_key, response = await factory.orchestrate("Find Python developers")
        async for chunk in factory.chat_stream("Find Python developers", agent_key):
            print(chunk, end="")
"""

import json
import os
from dataclasses import dataclass

from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    WebSearchPreviewTool,
    ApproximateLocation,
    MCPTool,
)
from dotenv import load_dotenv

from . import orchestrator, role_crafter, talent_scout, insight_pulse, connect_pilot, market_radar
from tools import SEND_EMAIL_TOOL
from memory import MemoryManager

load_dotenv()


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Agent:
    """Reference to a Foundry agent."""
    name: str
    version: int
    key: str


# =============================================================================
# Agent Factory
# =============================================================================

class AgentFactory:
    """Creates and manages 6 Foundry agents for recruiting.
    
    Agents:
        - orchestrator: Routes messages to the right agent
        - role-crafter: Builds candidate profiles from requirements
        - talent-scout: Searches resumes via Foundry IQ
        - insight-pulse: Retrieves interview feedback via Foundry IQ
        - connect-pilot: Drafts outreach emails
        - market-radar: Web search for market research (optional)
    """
    
    def __init__(self):
        self.endpoint = os.environ.get("PROJECT_ENDPOINT")
        self.model = os.environ.get("FOUNDRY_MODEL_PRIMARY", "gpt-4o-mini")
        self._credential = None
        self._client = None
        self._openai = None
        self._agents: dict[str, Agent] = {}
        self._memory: MemoryManager | None = None
    
    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, *args):
        await self.cleanup()
    
    async def initialize(self):
        """Initialize Azure clients and create all agents."""
        # Connect to Azure AI Foundry
        self._credential = DefaultAzureCredential()
        self._client = AIProjectClient(endpoint=self.endpoint, credential=self._credential)
        self._openai = self._client.get_openai_client()
        
        # Initialize long-term memory (optional)
        self._memory = MemoryManager(self._client)
        await self._memory.initialize()
        
        # Build search tools for Foundry IQ Knowledge Bases
        resume_tool, feedback_tool = self._build_kb_tools()
        
        # Configure each agent with its tools
        configs = {
            "orchestrator": orchestrator.get_config(),
            "role-crafter": role_crafter.get_config(),
            "talent-scout": talent_scout.get_config(resume_tool),
            "insight-pulse": insight_pulse.get_config(feedback_tool),
            "connect-pilot": connect_pilot.get_config(SEND_EMAIL_TOOL),
        }
        
        # Add web search agent if enabled
        if os.environ.get("ENABLE_WEB_SEARCH", "true").lower() == "true":
            web_tool = WebSearchPreviewTool(
                user_location=ApproximateLocation(country="AE", city="Dubai", region="Dubai")
            )
            configs["market-radar"] = market_radar.get_config(web_tool)
            print("✓ Web search enabled")
        
        # Create agents in Foundry
        for key, config in configs.items():
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
        """Close all Azure connections."""
        if self._openai:
            await self._openai.close()
        if self._client:
            await self._client.close()
        if self._credential:
            await self._credential.close()
    
    # -------------------------------------------------------------------------
    # Knowledge Base Tools (Foundry IQ)
    # -------------------------------------------------------------------------
    
    def _build_kb_tools(self) -> tuple[MCPTool, MCPTool]:
        """Build MCPTool connections to Foundry IQ Knowledge Bases.
        
        Returns:
            (resume_tool, feedback_tool) - Tools for searching resumes and feedback
        """
        search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
        api_version = "2025-11-01-preview"
        
        # Knowledge base names and MCP connections
        resumes_kb = os.environ.get("RESUMES_KB_NAME", "resumes-kb")
        feedback_kb = os.environ.get("FEEDBACK_KB_NAME", "feedback-kb")
        resumes_conn = os.environ.get("RESUMES_KB_CONNECTION", "resumes-kb-mcp")
        feedback_conn = os.environ.get("FEEDBACK_KB_CONNECTION", "feedback-kb-mcp")
        
        # Build MCP URLs
        resumes_url = f"{search_endpoint}/knowledgebases/{resumes_kb}/mcp?api-version={api_version}"
        feedback_url = f"{search_endpoint}/knowledgebases/{feedback_kb}/mcp?api-version={api_version}"
        
        resume_tool = MCPTool(
            server_label="resumes-kb",
            server_url=resumes_url,
            require_approval="never",
            allowed_tools=["knowledge_base_retrieve"],
            project_connection_id=resumes_conn,
        )
        
        feedback_tool = MCPTool(
            server_label="feedback-kb",
            server_url=feedback_url,
            require_approval="never",
            allowed_tools=["knowledge_base_retrieve"],
            project_connection_id=feedback_conn,
        )
        
        print(f"✓ Connected to Knowledge Bases: {resumes_kb}, {feedback_kb}")
        return resume_tool, feedback_tool
    
    # -------------------------------------------------------------------------
    # Chat Methods
    # -------------------------------------------------------------------------
    
    def _get_agent(self, agent_key: str) -> Agent:
        """Get agent by key. Raises ValueError if not found."""
        agent = self._agents.get(agent_key)
        if not agent:
            raise ValueError(f"Unknown agent: {agent_key}")
        return agent
    
    def _build_messages(self, message: str, agent_key: str, history: list[dict] = None) -> list | str:
        """Build message list with history for API call."""
        if not history:
            return message
        
        # Limit history (shorter for web search to avoid token limits)
        max_msgs = 6 if agent_key == "market-radar" else 20
        recent = history[-max_msgs:] if len(history) > max_msgs else history
        
        messages = [{"role": m["role"], "content": m["content"]} for m in recent]
        messages.append({"role": "user", "content": message})
        return messages
    
    async def chat(self, message: str, agent_key: str, history: list[dict] = None, user_id: str = None) -> str:
        """Send message to an agent and get complete response.
        
        Args:
            message: User's message
            agent_key: Which agent to use (e.g., "talent-scout")
            history: Previous messages for context
            user_id: For future memory scoping
        """
        agent = self._get_agent(agent_key)
        messages = self._build_messages(message, agent_key, history)
        
        response = await self._openai.responses.create(
            input=messages,
            tool_choice="auto",
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        )
        return response.output_text or ""
    
    async def chat_stream(self, message: str, agent_key: str, history: list[dict] = None, user_id: str = None):
        """Stream response from an agent. Yields text chunks.
        
        Args:
            message: User's message
            agent_key: Which agent to use
            history: Previous messages for context
            user_id: For future memory scoping
        """
        agent = self._get_agent(agent_key)
        messages = self._build_messages(message, agent_key, history)
        
        async with await self._openai.responses.create(
            input=messages,
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
    
    # -------------------------------------------------------------------------
    # Orchestration
    # -------------------------------------------------------------------------
    
    async def orchestrate(self, message: str, history: list[dict] = None) -> tuple[str, str | None]:
        """Route message to the appropriate agent via Orchestrator.
        
        Returns:
            (agent_key, direct_response)
            - If direct_response is set, orchestrator handled it directly
            - Otherwise, call chat() or chat_stream() with agent_key
        """
        orch = self._agents.get("orchestrator")
        if not orch:
            return "role-crafter", None
        
        # Build context about conversation state
        context = self._analyze_conversation(history)
        prompt = f"User message: {message}\n\n{context}\n\nOutput ONLY the JSON."
        
        try:
            response = await self._openai.responses.create(
                input=prompt,
                extra_body={"agent": {"name": orch.name, "type": "agent_reference"}},
            )
            
            # Parse JSON response from orchestrator
            text = response.output_text or ""
            if "{" in text and "}" in text:
                data = json.loads(text[text.index("{"):text.rindex("}")+1])
                agent_key = data.get("agent", "role-crafter")
                
                # Orchestrator handles greetings/out-of-scope directly
                if agent_key == "orchestrator":
                    return "orchestrator", data.get("response", "How can I help with recruiting?")
                
                if agent_key in self._agents:
                    return agent_key, None
            
            return "role-crafter", None
            
        except Exception as e:
            print(f"⚠️ Orchestrator error: {e}")
            return "role-crafter", None
    
    def _analyze_conversation(self, history: list[dict] = None) -> str:
        """Analyze conversation history for orchestrator context."""
        if not history:
            return "Context: New conversation, no profile yet."
        
        # Check if we have a profile
        has_profile = any(
            any(kw in (m.get("content") or "") for kw in ["Profile Ready", "Role:", "Title:"])
            for m in history if m.get("role") == "assistant"
        )
        
        # Check if we found candidates
        has_candidates = any(
            "candidate" in (m.get("content") or "").lower() and
            any(kw in (m.get("content") or "").lower() for kw in ["match", "found", "result"])
            for m in history if m.get("role") == "assistant"
        )
        
        # Check if last message was asking for more profile info
        last_assistant = next(
            (m.get("content", "") for m in reversed(history) if m.get("role") == "assistant"),
            ""
        )
        gathering_info = any(phrase in last_assistant.lower() for phrase in [
            "years of experience", "required skills", "preferred skills",
            "more details", "please provide", "please specify"
        ])
        
        parts = [
            f"Profile: {'exists' if has_profile else 'in progress'}",
            f"Candidates: {'found' if has_candidates else 'not searched'}",
        ]
        if gathering_info:
            parts.append("Currently gathering profile details")
        
        return "Context: " + ". ".join(parts) + "."
    
    # -------------------------------------------------------------------------
    # Memory (Long-term, Cross-session)
    # -------------------------------------------------------------------------
    
    @property
    def memory_enabled(self) -> bool:
        """Check if long-term memory is enabled."""
        return self._memory is not None and self._memory.enabled
    
    async def get_user_memories(self, user_id: str, query: str | None = None) -> list[dict]:
        """Get memories for a user."""
        if not self._memory:
            return []
        return await self._memory.search_memories(user_id, query)
    
    async def delete_user_memories(self, user_id: str) -> bool:
        """Delete all memories for a user (GDPR compliance)."""
        if not self._memory:
            return False
        return await self._memory.delete_user_memories(user_id)


__all__ = ["AgentFactory", "Agent"]
