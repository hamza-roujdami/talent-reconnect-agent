"""Test agent factory and workflow."""

import pytest
from src.agents import AgentFactory, AGENTS
from src.agents.definitions import get_agent_definitions, AGENT_KEYS


class TestAgentDefinitions:
    """Test agent definitions."""

    def test_all_agents_defined(self):
        """All expected agents have definitions."""
        definitions = get_agent_definitions()
        
        for key in AGENT_KEYS:
            assert key in definitions, f"Missing definition for {key}"
            assert "instructions" in definitions[key], f"Missing instructions for {key}"

    def test_agent_keys_match(self):
        """AGENTS export matches AGENT_KEYS."""
        assert set(AGENTS) == set(AGENT_KEYS)

    def test_search_agent_has_tool(self):
        """Search agent should have a tool."""
        definitions = get_agent_definitions()
        assert "tools" in definitions["search"]
        assert len(definitions["search"]["tools"]) > 0

    def test_insights_agent_has_tool(self):
        """Insights agent should have a tool."""
        definitions = get_agent_definitions()
        assert "tools" in definitions["insights"]
        assert len(definitions["insights"]["tools"]) > 0


class TestAgentImports:
    """Test agent module imports."""

    def test_import_factory(self):
        """Can import AgentFactory."""
        from src.agents import AgentFactory
        assert AgentFactory is not None

    def test_import_agent_modules(self):
        """Can import individual agent modules."""
        from src.agents import orchestrator, profile, search, insights, outreach
        
        # Each module should have get_config
        assert hasattr(orchestrator, "get_config")
        assert hasattr(profile, "get_config")
        assert hasattr(search, "get_config")
        assert hasattr(insights, "get_config")
        assert hasattr(outreach, "get_config")


@pytest.mark.asyncio
class TestAgentFactory:
    """Test AgentFactory (requires Azure credentials)."""

    async def test_factory_initialization(self, project_endpoint):
        """Factory initializes and creates agents."""
        async with AgentFactory(persist_agents=True) as factory:
            assert len(factory.agents) == 5
            assert "orchestrator" in factory.agents
            assert "search" in factory.agents

    async def test_chat_orchestrator(self, project_endpoint):
        """Can chat with orchestrator agent."""
        async with AgentFactory() as factory:
            response = await factory.chat("Hello, what can you help me with?", "orchestrator")
            assert len(response) > 0

    async def test_chat_search(self, project_endpoint):
        """Can chat with search agent."""
        async with AgentFactory() as factory:
            response = await factory.chat("Find Python developers in Dubai", "search")
            assert len(response) > 0

    async def test_orchestrate_routes_correctly(self, project_endpoint):
        """Orchestrate method routes to correct agent."""
        async with AgentFactory() as factory:
            response, agent = await factory.orchestrate("Find ML engineers")
            assert agent == "search"
            assert len(response) > 0
