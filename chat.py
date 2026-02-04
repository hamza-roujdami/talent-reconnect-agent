#!/usr/bin/env python
"""CLI chat interface for Talent Reconnect Agent.

Usage:
    python chat.py
"""

import asyncio
from agents import AgentFactory
from config import config


async def main():
    """Interactive CLI chat loop."""
    
    # Validate config
    missing = config.validate()
    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nCopy .env.example to .env and fill in your credentials.")
        return
    
    print("🎯 Talent Reconnect Agent")
    print("=" * 40)
    print("AI-powered recruiting assistant")
    print("Type 'quit' or 'exit' to stop\n")
    
    history = []
    
    async with AgentFactory() as factory:
        print("\n✓ Ready! Describe the role you're hiring for.\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\nGoodbye!")
                break
            
            if not user_input:
                continue
            
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break
            
            # Add user message to history
            history.append({"role": "user", "content": user_input})
            
            try:
                # Route via orchestrator
                agent_key, direct_response = await factory.orchestrate(user_input, history=history)
                
                if direct_response:
                    # Orchestrator handled directly (greeting, out-of-scope)
                    response = direct_response
                else:
                    # Get response from the routed agent
                    response = await factory.chat(user_input, agent_key, history=history)
                
                # Add assistant response to history
                history.append({"role": "assistant", "content": response})
                
                print(f"\n[{agent_key}] {response}\n")
                
            except Exception as e:
                print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
