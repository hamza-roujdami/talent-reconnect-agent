#!/usr/bin/env python3
"""
Debug script to check what tools are registered on agents.
"""
from agents.factory import create_recruiting_workflow

# Use the actual factory function
print("Creating workflow via factory...")
workflow = create_recruiting_workflow()

print("\n=== AFTER HandoffBuilder (from factory) ===\n")

# Inspect each executor
for executor in workflow.get_executors_list():
    agent = getattr(executor, '_agent', None)
    if agent:
        print(f"Agent: {agent.name}")
        tools = agent.chat_options.tools or []
        print(f"  Tools ({len(tools)}):")
        for tool in tools:
            tool_name = getattr(tool, 'name', str(tool))
            print(f"    - {tool_name}")
        print()
