"""Tests for Foundry IQ Knowledge Base integration.

Tests TalentScout (resumes-kb) and InsightPulse (feedback-kb) agents
using MCPTool to query Azure AI Search Knowledge Bases.

Usage:
    # Run all tests
    pytest tests/test_foundry_iq.py -v
    
    # Run specific test
    pytest tests/test_foundry_iq.py::TestAgentFactoryIntegration -v
    
    # Run with output
    pytest tests/test_foundry_iq.py -v -s
    
    # Run quick test directly
    python tests/test_foundry_iq.py
"""

import asyncio
import os
import pytest
from dotenv import load_dotenv

load_dotenv()


# Skip all tests if required env vars are missing
pytestmark = pytest.mark.skipif(
    not os.environ.get("PROJECT_ENDPOINT") or not os.environ.get("AZURE_SEARCH_ENDPOINT"),
    reason="PROJECT_ENDPOINT and AZURE_SEARCH_ENDPOINT required"
)


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfiguration:
    """Test environment configuration."""
    
    def test_project_endpoint_set(self):
        """Verify PROJECT_ENDPOINT is configured."""
        endpoint = os.environ.get("PROJECT_ENDPOINT")
        assert endpoint, "PROJECT_ENDPOINT not set"
        assert "services.ai.azure.com" in endpoint, "Invalid endpoint format"
    
    def test_search_endpoint_set(self):
        """Verify AZURE_SEARCH_ENDPOINT is configured."""
        endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
        assert endpoint, "AZURE_SEARCH_ENDPOINT not set"
        assert "search.windows.net" in endpoint, "Invalid search endpoint format"
    
    def test_kb_names_set(self):
        """Verify knowledge base names are configured."""
        resumes_kb = os.environ.get("RESUMES_KB_NAME", "resumes-kb")
        feedback_kb = os.environ.get("FEEDBACK_KB_NAME", "feedback-kb")
        assert resumes_kb, "RESUMES_KB_NAME not set"
        assert feedback_kb, "FEEDBACK_KB_NAME not set"
    
    def test_mcp_connections_set(self):
        """Verify MCP connection names are configured."""
        resumes_conn = os.environ.get("RESUMES_KB_CONNECTION", "resumes-kb-mcp")
        feedback_conn = os.environ.get("FEEDBACK_KB_CONNECTION", "feedback-kb-mcp")
        assert resumes_conn, "RESUMES_KB_CONNECTION not set"
        assert feedback_conn, "FEEDBACK_KB_CONNECTION not set"


# =============================================================================
# Integration Tests (Full Agent Factory)
# =============================================================================

class TestAgentFactoryIntegration:
    """Test full AgentFactory with Foundry IQ."""
    
    @pytest.mark.asyncio
    async def test_factory_initialization(self):
        """Test AgentFactory initializes with Foundry IQ tools."""
        from agents import AgentFactory
        
        factory = AgentFactory()
        await factory.initialize()
        
        # Check all agents created
        assert "orchestrator" in factory._agents
        assert "talent-scout" in factory._agents
        assert "insight-pulse" in factory._agents
        
        print("\n✓ AgentFactory initialized with all agents")
        
        await factory.cleanup()
    
    @pytest.mark.asyncio
    async def test_talent_scout_search(self):
        """Test TalentScout agent search through factory."""
        from agents import AgentFactory
        
        factory = AgentFactory()
        await factory.initialize()
        
        try:
            response = await factory.chat(
                "Find software engineers with Python and Azure skills in Dubai",
                agent_key="talent-scout"
            )
            
            assert response, "No response from TalentScout"
            assert len(response) > 50, "Response too short"
            print(f"\n✓ TalentScout Response:\n{response[:500]}...")
        finally:
            await factory.cleanup()
    
    @pytest.mark.asyncio
    async def test_talent_scout_with_experience(self):
        """Test TalentScout with experience filter."""
        from agents import AgentFactory
        
        factory = AgentFactory()
        await factory.initialize()
        
        try:
            response = await factory.chat(
                "Find Senior Data Engineers with 5+ years experience",
                agent_key="talent-scout"
            )
            
            assert response, "No response from TalentScout"
            print(f"\n✓ Experience Filter Response:\n{response[:500]}...")
        finally:
            await factory.cleanup()
    
    @pytest.mark.asyncio
    async def test_insight_pulse_search(self):
        """Test InsightPulse agent through factory."""
        from agents import AgentFactory
        
        factory = AgentFactory()
        await factory.initialize()
        
        try:
            response = await factory.chat(
                "Find interview feedback for senior candidates",
                agent_key="insight-pulse"
            )
            
            assert response, "No response from InsightPulse"
            print(f"\n✓ InsightPulse Response:\n{response[:500]}...")
        finally:
            await factory.cleanup()
    
    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Test streaming response from TalentScout."""
        from agents import AgentFactory
        
        factory = AgentFactory()
        await factory.initialize()
        
        try:
            chunks = []
            async for chunk in factory.chat_stream(
                "Find AI Engineers with 5 years experience",
                agent_key="talent-scout"
            ):
                chunks.append(chunk)
            
            full_response = "".join(chunks)
            assert full_response, "No streaming response from TalentScout"
            assert len(chunks) > 1, "Expected multiple chunks in streaming"
            print(f"\n✓ Streaming Response ({len(chunks)} chunks):\n{full_response[:500]}...")
        finally:
            await factory.cleanup()


# =============================================================================
# Direct Test Runner
# =============================================================================

async def run_quick_test():
    """Quick test to verify Foundry IQ is working."""
    from azure.identity.aio import DefaultAzureCredential
    from azure.ai.projects.aio import AIProjectClient
    from azure.ai.projects.models import PromptAgentDefinition, MCPTool
    
    print("=" * 60)
    print("Foundry IQ Quick Test")
    print("=" * 60)
    
    endpoint = os.environ.get("PROJECT_ENDPOINT")
    search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    resumes_kb = os.environ.get("RESUMES_KB_NAME", "resumes-kb")
    resumes_conn = os.environ.get("RESUMES_KB_CONNECTION", "resumes-kb-mcp")
    
    print(f"\nProject: {endpoint}")
    print(f"Search: {search_endpoint}")
    print(f"KB: {resumes_kb}")
    print(f"Connection: {resumes_conn}")
    
    credential = DefaultAzureCredential()
    client = AIProjectClient(endpoint=endpoint, credential=credential)
    openai = client.get_openai_client()
    
    try:
        # Build MCP tool
        mcp_url = f"{search_endpoint}/knowledgebases/{resumes_kb}/mcp?api-version=2025-11-01-preview"
        print(f"\nMCP URL: {mcp_url}")
        
        resume_tool = MCPTool(
            server_label="resumes-kb",
            server_url=mcp_url,
            require_approval="never",
            allowed_tools=["knowledge_base_retrieve"],
            project_connection_id=resumes_conn,
        )
        
        # Create test agent
        agent = await client.agents.create_version(
            agent_name="foundry-iq-test",
            definition=PromptAgentDefinition(
                model="gpt-4o-mini",
                instructions="You search for candidates. Use the knowledge_base_retrieve tool to find matching candidates.",
                tools=[resume_tool],
            ),
        )
        print(f"\n✓ Created test agent v{agent.version}")
        
        # Test query
        print("\n" + "-" * 40)
        print("Testing: Senior AI Engineer Dubai Azure 5+ years")
        print("-" * 40)
        
        response = await openai.responses.create(
            input="Find Senior AI Engineers in Dubai with Azure skills and 5+ years experience. List their names and skills.",
            tool_choice="auto",
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
        )
        
        if response.output_text:
            print(f"\n✓ SUCCESS!\n\nResponse:\n{response.output_text}")
        else:
            print("\n✗ No output text in response")
            print(f"Raw response: {response}")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await openai.close()
        await client.close()
        await credential.close()


if __name__ == "__main__":
    asyncio.run(run_quick_test())
