"""End-to-end workflow test.

Tests the full multi-agent workflow with all capabilities.

Run with:
    pytest tests/e2e/test_workflow.py -v
    
Or standalone:
    python tests/e2e/test_workflow.py
"""

import asyncio
import pytest
from src.agents import AgentFactory


@pytest.mark.asyncio
class TestFullWorkflow:
    """Test complete agent workflow."""

    async def test_full_workflow(self, project_endpoint):
        """Test all agents in sequence."""
        async with AgentFactory() as factory:
            # 1. Orchestrator greeting
            response = await factory.chat("Hello, what can you help me with?", "orchestrator")
            assert len(response) > 0
            print(f"✓ Orchestrator: {len(response)} chars")

            # 2. Profile agent
            response = await factory.chat(
                "I need a senior data engineer with Python and Spark",
                "profile"
            )
            assert len(response) > 0
            print(f"✓ Profile: {len(response)} chars")

            # 3. Search agent with tool
            response = await factory.chat("Find ML engineers in Dubai", "search")
            assert len(response) > 0
            print(f"✓ Search: {len(response)} chars")

            # 4. Insights agent with feedback tool
            response = await factory.chat(
                "What feedback do we have for candidates?",
                "insights"
            )
            assert len(response) > 0
            print(f"✓ Insights: {len(response)} chars")

            # 5. Outreach agent
            response = await factory.chat(
                "Write an email to a candidate about a Senior Engineer role",
                "outreach"
            )
            assert len(response) > 0
            print(f"✓ Outreach: {len(response)} chars")

            # 6. Auto-routing
            response, agent = await factory.orchestrate("Find candidates who know PyTorch")
            assert agent == "search"
            assert len(response) > 0
            print(f"✓ Auto-routing: routed to {agent}")


async def main():
    """Standalone test runner."""
    print("=" * 60)
    print("🧪 Full Workflow Test")
    print("=" * 60)

    async with AgentFactory() as factory:
        print(f"\n✅ Created {len(factory.agents)} agents\n")

        scenarios = [
            ("orchestrator", "Hello! What can you help me with?"),
            ("profile", "I need a Senior Data Engineer with Python and Azure, 5+ years, in Dubai"),
            ("search", "Find Python developers in Dubai with cloud experience"),
            ("insights", "What's the interview feedback for candidates named Ahmed?"),
            ("outreach", "Draft an email to a candidate for a Data Engineer role at TechCorp"),
        ]

        for agent, prompt in scenarios:
            print("-" * 60)
            print(f"📤 [{agent.upper()}] {prompt}")
            print("-" * 60)

            response = await factory.chat(prompt, agent_key=agent)
            # Truncate for display
            display = response[:500] + "..." if len(response) > 500 else response
            print(f"📥 Response:\n{display}\n")

        # Test auto-routing
        print("=" * 60)
        print("🔀 Testing Auto-Routing")
        print("=" * 60)

        routing_tests = [
            "Find senior backend engineers",
            "Help me define requirements for a PM role",
            "What feedback do we have on Omar?",
            "Write an outreach email to John",
        ]

        for prompt in routing_tests:
            response, agent = await factory.orchestrate(prompt)
            print(f"\n📤 '{prompt}'")
            print(f"   → Routed to: {agent}")
            print(f"   → Response: {response[:150]}...")

    print("\n✅ All tests complete!")


if __name__ == "__main__":
    asyncio.run(main())
