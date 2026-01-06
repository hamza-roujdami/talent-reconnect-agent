#!/usr/bin/env python3
"""
Demo scenario test - runs predefined conversation.
"""
import asyncio
import time
import warnings

# Suppress aiohttp unclosed session warnings (Azure SDK internal noise)
warnings.filterwarnings("ignore", message="Unclosed client session")
warnings.filterwarnings("ignore", message="Unclosed connector")

from agents.factory import create_recruiting_workflow
from agent_framework import (
    AgentRunUpdateEvent,
    FunctionCallContent,
    FunctionResultContent,
    WorkflowOutputEvent,
    RequestInfoEvent,
)

# Colors
class C:
    H = '\033[95m'  # Header
    B = '\033[94m'  # Blue
    C = '\033[96m'  # Cyan
    G = '\033[92m'  # Green
    Y = '\033[93m'  # Yellow
    R = '\033[91m'  # Red
    E = '\033[0m'   # End
    BOLD = '\033[1m'

# Demo conversation
DEMO_SCRIPT = [
    "Hire a Data Engineer in Dubai",
    "Add Azure to the required skills",
    "yes",
    "Check interview feedback for all candidates",
    "Send email to candidate 1",
]

async def run_demo():
    print(f"\n{C.H}{C.BOLD}{'='*70}{C.E}")
    print(f"{C.H}{C.BOLD}  DEMO: Talent Reconnect Multi-Agent Recruiting Workflow{C.E}")
    print(f"{C.H}{C.BOLD}{'='*70}{C.E}\n")
    
    workflow = create_recruiting_workflow()
    pending_requests = []
    
    for i, user_msg in enumerate(DEMO_SCRIPT, 1):
        step_start = time.perf_counter()
        print(f"\n{C.BOLD}{'─'*70}{C.E}")
        print(f"{C.BOLD}Step {i}: {user_msg}{C.E}")
        print(f"{C.BOLD}{'─'*70}{C.E}\n")
        
        # Run workflow
        if pending_requests:
            responses = {req.request_id: user_msg for req in pending_requests}
            pending_requests = []
            stream = workflow.send_responses_streaming(responses)
        else:
            stream = workflow.run_stream(user_msg)
        
        current_agent = None
        full_text = ""
        
        async for event in stream:
            if isinstance(event, AgentRunUpdateEvent):
                # Agent change - only print once per agent
                if event.executor_id and event.executor_id != current_agent:
                    current_agent = event.executor_id
                    print(f"{C.C}🤖 [{current_agent}]{C.E}")
                
                data = event.data
                
                # Tool calls - only print non-handoff tools once
                if hasattr(data, 'contents') and data.contents:
                    for item in data.contents:
                        if isinstance(item, FunctionCallContent) and item.name:
                            tool_key = f"{current_agent}:{item.name}"
                            if item.name and not item.name.startswith('handoff_'):
                                print(f"{C.Y}  → {item.name}(){C.E}")
                        elif isinstance(item, FunctionResultContent) and item.result:
                            result = str(item.result)
                            if '|' in result or '📧' in result or '📋' in result:
                                # Show important results
                                lines = result.split('\n')[:30]
                                for line in lines:
                                    print(f"{C.G}{line}{C.E}")
                                if len(result.split('\n')) > 30:
                                    print(f"{C.G}... (truncated){C.E}")
                
                # Text output - accumulate
                if hasattr(data, 'text') and data.text:
                    full_text += data.text
            
            elif isinstance(event, RequestInfoEvent):
                pending_requests.append(event)
        
        # Print accumulated text (profile card, rankings, insights, etc)
        if full_text.strip():
            text = full_text.strip()
            highlight = '🎯' in text or '📋' in text or '✨' in text
            color = C.B if highlight else C.C
            print(f"\n{color}{text}{C.E}")
        step_duration = time.perf_counter() - step_start
        print(f"{C.B}⏱️  Step {i} latency: {step_duration:.2f}s{C.E}")
        
        # Wait between steps
        await asyncio.sleep(1)
    
    print(f"\n{C.H}{C.BOLD}{'='*70}{C.E}")
    print(f"{C.G}{C.BOLD}  ✅ Demo Complete!{C.E}")
    print(f"{C.H}{C.BOLD}{'='*70}{C.E}\n")

if __name__ == "__main__":
    import sys
    import os

    # Suppress aiohttp unclosed session warnings printed at shutdown
    # by redirecting stderr to /dev/null during GC cleanup
    asyncio.run(run_demo())

    # Flush and redirect stderr to suppress Azure SDK aiohttp noise
    sys.stderr.flush()
    sys.stderr = open(os.devnull, "w")
