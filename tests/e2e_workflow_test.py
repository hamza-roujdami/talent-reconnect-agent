#!/usr/bin/env python
"""End-to-end test for the recruiting workflow."""

import asyncio
import sys
from pathlib import Path

# Add project root to path to avoid tests/agents shadowing
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import AgentFactory


async def e2e_test():
    """Run full recruiting workflow."""
    print("=" * 60)
    print("END-TO-END CLI TEST - Full Recruiting Workflow")
    print("=" * 60)
    
    async with AgentFactory() as factory:
        print("\n✓ Agents ready\n")
        
        # Step 1: Define role
        print("-" * 60)
        print("STEP 1: Define the role (profile agent)")
        print("-" * 60)
        msg1 = "Hire a Data Engineer in Dubai with Azure and Python skills"
        print(f"User: {msg1}\n")
        resp1, agent1 = await factory.orchestrate(msg1)
        print(f"[{agent1}]: {resp1[:500]}..." if len(resp1) > 500 else f"[{agent1}]: {resp1}")
        print()
        
        # Step 2: Search candidates
        print("-" * 60)
        print("STEP 2: Search for candidates (search agent)")
        print("-" * 60)
        msg2 = "Find candidates matching this profile"
        print(f"User: {msg2}\n")
        resp2, agent2 = await factory.orchestrate(msg2)
        print(f"[{agent2}]: {resp2[:800]}..." if len(resp2) > 800 else f"[{agent2}]: {resp2}")
        print()
        
        # Step 3: Get feedback
        print("-" * 60)
        print("STEP 3: Check interview feedback (insights agent)")
        print("-" * 60)
        msg3 = "What interview feedback do we have for the top candidate?"
        print(f"User: {msg3}\n")
        resp3, agent3 = await factory.orchestrate(msg3)
        print(f"[{agent3}]: {resp3[:600]}..." if len(resp3) > 600 else f"[{agent3}]: {resp3}")
        print()
        
        # Step 4: Send outreach
        print("-" * 60)
        print("STEP 4: Draft outreach email (outreach agent)")
        print("-" * 60)
        msg4 = "Draft an email to reach out to the top candidate"
        print(f"User: {msg4}\n")
        resp4, agent4 = await factory.orchestrate(msg4)
        print(f"[{agent4}]: {resp4[:800]}..." if len(resp4) > 800 else f"[{agent4}]: {resp4}")
        print()
        
        # Summary
        print("=" * 60)
        print("WORKFLOW SUMMARY")
        print("=" * 60)
        agents_used = [agent1, agent2, agent3, agent4]
        expected = ["profile", "search", "insights", "outreach"]
        print(f"Agents used: {agents_used}")
        print(f"Expected:    {expected}")
        
        if agents_used == expected:
            print("\n✓ All agents routed correctly!")
            return True
        else:
            print("\n✗ Routing mismatch detected")
            return False


if __name__ == "__main__":
    success = asyncio.run(e2e_test())
    exit(0 if success else 1)
