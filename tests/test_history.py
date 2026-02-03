#!/usr/bin/env python
"""Test multi-turn conversation with history."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import AgentFactory


async def test_with_history():
    """Test that agents maintain context across turns."""
    print("Testing conversation WITH history...")
    print("=" * 60)
    
    async with AgentFactory() as factory:
        history = []
        
        # Turn 1: Define role
        msg1 = "Hire a Data Engineer in Dubai"
        print(f"\nUser: {msg1}")
        resp1 = await factory.chat(msg1, "profile", history=history)
        print(f"Agent: {resp1[:300]}...")
        history.append({"role": "user", "content": msg1})
        history.append({"role": "assistant", "content": resp1})
        
        # Turn 2: Add details - agent should remember context
        msg2 = "senior level, Azure required, 8+ years experience"
        print(f"\nUser: {msg2}")
        resp2 = await factory.chat(msg2, "profile", history=history)
        print(f"Agent: {resp2[:400]}...")
        history.append({"role": "user", "content": msg2})
        history.append({"role": "assistant", "content": resp2})
        
        # Turn 3: Search with context
        msg3 = "now search for candidates matching this profile"
        print(f"\nUser: {msg3}")
        resp3 = await factory.chat(msg3, "search", history=history)
        print(f"Agent: {resp3[:500]}...")
        
        print("\n" + "=" * 60)
        print("Context test complete!")
        
        # Check if agent remembered context
        if "azure" in resp3.lower() or "dubai" in resp3.lower() or "senior" in resp3.lower():
            print("✓ Agent appears to remember context from previous turns")
        else:
            print("? Agent may not be using full context")


if __name__ == "__main__":
    asyncio.run(test_with_history())
