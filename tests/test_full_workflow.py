"""Full workflow test: Hi → JD → Search → Feedback → Email."""

import asyncio
import sys
sys.path.insert(0, "/Users/hamza/projects/talent-reconnect-agent")
from agents.factory import AgentFactory


async def test_workflow():
    """Test the complete recruiting workflow."""
    print("\n" + "=" * 70)
    print("🚀 TALENT RECONNECT - FULL WORKFLOW TEST")
    print("=" * 70)
    
    async with AgentFactory() as factory:
        history = []
        
        def add_to_history(role: str, content: str):
            history.append({"role": role, "content": content})
        
        async def chat(step: int, msg: str) -> str:
            print(f"\n{'─' * 70}")
            print(f"📝 STEP {step}: {msg}")
            print("─" * 70)
            add_to_history("user", msg)
            
            # Route via orchestrator
            agent_key, direct_response = await factory.orchestrate(msg, history=history)
            print(f"🤖 ORCHESTRATOR → {agent_key}")
            
            # If orchestrator handles directly (greetings, out-of-scope)
            if direct_response:
                response = direct_response
            else:
                # Get response from the routed agent
                response = await factory.chat(msg, agent_key, history=history)
            
            add_to_history("assistant", response)
            
            # Print response (truncate if too long)
            print(f"\n💬 {agent_key.upper()} RESPONSE:")
            if len(response) > 1500:
                print(response[:1500] + "\n...[truncated]")
            else:
                print(response)
            
            return response
        
        # Step 1: Greeting
        await chat(1, "Hi")
        
        # Step 2: Define the role
        await chat(2, "I need a Senior AI Engineer in Dubai")
        
        # Step 3: Add requirements
        await chat(3, "Required: Python, LLMs, Azure. Nice to have: Kubernetes, MLOps. 5+ years experience.")
        
        # Step 4: Confirm and search
        await chat(4, "Looks good. Now search for candidates matching the profile.")
        
        # Step 5: Get feedback
        await chat(5, "Check interview feedback for candidate 1")
        
        # Step 6: Send email
        await chat(6, "Send an outreach email to candidate 1")
        
        print("\n" + "=" * 70)
        print("✅ WORKFLOW COMPLETE!")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_workflow())
