"""
Unit tests for individual agents.

Run with: pytest tests/test_agents.py -v
"""
import pytest


class TestWorkflowCreation:
    """Tests for workflow and agent creation."""
    
    def test_workflow_creates_successfully(self, workflow):
        """Workflow should be created without errors."""
        assert workflow is not None
    
    def test_workflow_has_executors(self, workflow):
        """Workflow should have multiple executors (agents)."""
        executors = workflow.get_executors_list()
        assert len(executors) >= 4, "Expected at least 4 agents (orchestrator + 3 specialists)"
    
    def test_workflow_has_coordinator(self, workflow):
        """Workflow should have a coordinator agent."""
        # The coordinator is set via set_coordinator() in factory
        executors = workflow.get_executors_list()
        agent_names = []
        for executor in executors:
            agent = getattr(executor, '_agent', None)
            if agent:
                agent_names.append(agent.name)
        
        assert "orchestrator" in agent_names, "Expected orchestrator as coordinator"


class TestAgentConfiguration:
    """Tests for agent configuration and tools."""
    
    def test_agents_have_names(self, workflow):
        """Each agent should have a name."""
        for executor in workflow.get_executors_list():
            agent = getattr(executor, '_agent', None)
            if agent:
                assert agent.name is not None
                assert len(agent.name) > 0
    
    def test_specialist_agents_exist(self, workflow):
        """All specialist agents should exist."""
        executors = workflow.get_executors_list()
        agent_names = set()
        for executor in executors:
            agent = getattr(executor, '_agent', None)
            if agent:
                agent_names.add(agent.name.lower())
        
        # Check for expected specialists (actual names from factory)
        expected_agents = ["rolecrafter", "talentscout", "insightpulse", "connectpilot"]
        for expected in expected_agents:
            assert expected in agent_names, f"Expected agent '{expected}' not found. Found: {agent_names}"
    
    def test_orchestrator_has_handoff_tools(self, workflow):
        """Orchestrator should have handoff tools for routing."""
        for executor in workflow.get_executors_list():
            agent = getattr(executor, '_agent', None)
            if agent and agent.name == "orchestrator":
                tools = agent.chat_options.tools or []
                tool_names = [getattr(t, 'name', str(t)) for t in tools]
                
                # Should have handoff tools
                handoff_tools = [t for t in tool_names if 'handoff' in t.lower()]
                assert len(handoff_tools) >= 3, "Orchestrator should have handoff tools for specialists"
                break
        else:
            pytest.fail("Orchestrator agent not found")


class TestAgentInstructions:
    """Tests for agent instructions loading."""
    
    def test_agent_modules_exist(self):
        """Agent module files should exist."""
        from pathlib import Path
        
        agents_dir = Path(__file__).parent.parent / "agents"
        expected_files = [
            "profile_agent.py",
            "search_agent.py", 
            "insights_agent.py",
            "outreach_agent.py",
        ]
        
        for filename in expected_files:
            filepath = agents_dir / filename
            assert filepath.exists(), f"Missing agent file: {filename}"
    
    def test_agent_creators_importable(self):
        """Agent creator functions should be importable."""
        from agents.profile_agent import create_profile_agent
        from agents.search_agent import create_search_agent
        from agents.insights_agent import create_insights_agent
        from agents.outreach_agent import create_outreach_agent
        
        assert callable(create_profile_agent)
        assert callable(create_search_agent)
        assert callable(create_insights_agent)
        assert callable(create_outreach_agent)
