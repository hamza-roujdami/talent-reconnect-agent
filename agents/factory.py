"""Agent Factory - 6-agent recruiting system.

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

load_dotenv()


@dataclass
class Agent:
    """Agent reference."""
    name: str
    version: int
    key: str


class AgentFactory:
    """Creates and manages 6 Foundry agents for recruiting."""
    
    def __init__(self):
        self.endpoint = os.environ.get("PROJECT_ENDPOINT")
        self.model = os.environ.get("FOUNDRY_MODEL_PRIMARY", "gpt-4o-mini")
        self._credential = None
        self._client = None
        self._openai = None
        self._agents: dict[str, Agent] = {}
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, *args):
        await self.cleanup()
    
    async def initialize(self):
        """Initialize client and create agents."""
        self._credential = DefaultAzureCredential()
        self._client = AIProjectClient(endpoint=self.endpoint, credential=self._credential)
        self._openai = self._client.get_openai_client()
        
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
        
        # Agent definitions
        definitions = {
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
            definitions["market-radar"] = market_radar.get_config(web_tool)
            print("✓ Web Search enabled")
        
        # Create agents
        for key, config in definitions.items():
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
    
    async def chat(self, message: str, agent_key: str, history: list[dict] = None) -> str:
        """Send message to an agent."""
        agent = self._agents.get(agent_key)
        if not agent:
            raise ValueError(f"Unknown agent: {agent_key}")
        
        # Build input with history
        if history:
            max_history = 6 if agent_key == "market-radar" else 20
            recent = history[-max_history:] if len(history) > max_history else history
            input_data = [{"role": m["role"], "content": m["content"]} for m in recent]
            input_data.append({"role": "user", "content": message})
        else:
            input_data = message
        
        response = await self._openai.responses.create(
            input=input_data,
            tool_choice="auto",
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        )
        return response.output_text or ""
    
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


__all__ = ["AgentFactory", "Agent"]
