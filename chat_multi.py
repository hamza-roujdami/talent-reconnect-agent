"""
Multi-Agent Chat Interface

Tests the HandoffBuilder workflow with specialist agents.

Usage:
    python chat_multi.py             # Run multi-agent workflow
    python chat_multi.py --verbose   # Show handoff details
"""
import argparse
import asyncio
from typing import cast
from agents.factory import create_recruiting_workflow
from agent_framework import (
    ChatMessage,
    WorkflowOutputEvent,
    WorkflowStatusEvent,
    WorkflowRunState,
    HandoffUserInputRequest,
    RequestInfoEvent,
    AgentRunUpdateEvent,
    FunctionCallContent,
    FunctionResultContent,
)

# Parse arguments
parser = argparse.ArgumentParser(description="Multi-Agent Recruiting Chat")
parser.add_argument("--verbose", "-v", action="store_true", help="Show handoff details")
args = parser.parse_args()

VERBOSE = args.verbose


async def process_stream(stream):
    """Process workflow stream and yield events."""
    pending_requests = []
    seen_agents = set()
    seen_tools = set()
    response_text = ""
    
    async for event in stream:
        if VERBOSE and isinstance(event, WorkflowStatusEvent):
            print(f"\n  📍 [{event.state.name}]", end="", flush=True)
        
        # Show agent and tool activity
        if isinstance(event, AgentRunUpdateEvent):
            agent_name = event.executor_id
            if agent_name and agent_name not in seen_agents:
                seen_agents.add(agent_name)
                display_name = agent_name.replace('_', ' ').title()
                print(f"\n🤖 {display_name}", flush=True)
            
            data = event.data
            if hasattr(data, 'contents') and data.contents:
                for item in data.contents:
                    if isinstance(item, FunctionCallContent) and item.name:
                        if not item.name.startswith('handoff_') and item.name not in seen_tools:
                            seen_tools.add(item.name)
                            print(f"🔧 {item.name}", flush=True)
                    if isinstance(item, FunctionResultContent) and item.result:
                        result_str = str(item.result)
                        if len(result_str) > 50 and 'handoff_to' not in result_str:
                            print(f"\n{result_str}\n", flush=True)
            
            if hasattr(data, 'text') and data.text:
                response_text += data.text
        
        # Collect pending user input requests
        if isinstance(event, RequestInfoEvent):
            pending_requests.append(event)
        
        # Final output
        if isinstance(event, WorkflowOutputEvent):
            pass  # Already handled via AgentRunUpdateEvent
    
    # Print accumulated text response
    if response_text:
        print(f"\n{response_text}", flush=True)
    
    return pending_requests


async def chat():
    """Main interactive chat loop with multi-agent workflow."""
    print("\n🎯 Talent Reconnect - Multi-Agent Mode")
    print("=" * 50)
    print("Agents: Orchestrator → Profile → Search → Insights → Outreach")
    print("I help you find and reach out to candidates.")
    print("\nType 'quit' to exit\n")
    
    # Create workflow
    workflow = create_recruiting_workflow()
    
    # Get initial user input
    user_input = input("You: ").strip()
    if user_input.lower() == "quit":
        print("\nGoodbye! 👋")
        return
    
    # Start workflow with initial message
    pending_requests = await process_stream(workflow.run_stream(user_input))
    
    # Continue conversation loop
    while pending_requests:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "quit":
                print("\nGoodbye! 👋")
                break
            
            # Send response to all pending requests
            responses = {req.request_id: user_input for req in pending_requests}
            pending_requests = await process_stream(workflow.send_responses_streaming(responses))
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            if VERBOSE:
                import traceback
                traceback.print_exc()


def main():
    """Entry point."""
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(chat())


if __name__ == "__main__":
    main()
