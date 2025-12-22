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
)

# Parse arguments
parser = argparse.ArgumentParser(description="Multi-Agent Recruiting Chat")
parser.add_argument("--verbose", "-v", action="store_true", help="Show handoff details")
args = parser.parse_args()

VERBOSE = args.verbose


async def chat():
    """Main interactive chat loop with multi-agent workflow."""
    print("\n🎯 Talent Reconnect - Multi-Agent Mode")
    print("=" * 50)
    print("Agents: Orchestrator → Profile → Search → Outreach")
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
    print("\nAssistant: ", end="", flush=True)
    
    pending_requests = []
    async for event in workflow.run_stream(user_input):
        if VERBOSE and isinstance(event, WorkflowStatusEvent):
            print(f"\n  📍 [{event.state.name}]", end="", flush=True)
        
        # Collect pending user input requests
        if isinstance(event, RequestInfoEvent):
            if isinstance(event.data, HandoffUserInputRequest):
                # Print the conversation so far
                for msg in event.data.conversation:
                    if msg.role.value == "assistant" and msg.text:
                        print(msg.text, end="", flush=True)
            pending_requests.append(event)
        
        # Final output
        if isinstance(event, WorkflowOutputEvent):
            conversation = event.data
            if isinstance(conversation, list):
                for msg in conversation:
                    if msg.role.value == "assistant" and msg.text:
                        print(msg.text, end="", flush=True)
    
    print()  # Newline
    
    # Continue conversation loop
    while pending_requests:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "quit":
                print("\nGoodbye! 👋")
                break
            
            print("\nAssistant: ", end="", flush=True)
            
            # Send response to all pending requests
            responses = {req.request_id: user_input for req in pending_requests}
            pending_requests = []
            
            async for event in workflow.send_responses_streaming(responses):
                if VERBOSE and isinstance(event, WorkflowStatusEvent):
                    print(f"\n  📍 [{event.state.name}]", end="", flush=True)
                
                if isinstance(event, RequestInfoEvent):
                    if isinstance(event.data, HandoffUserInputRequest):
                        for msg in event.data.conversation:
                            if msg.role.value == "assistant" and msg.text:
                                # Only print new messages
                                print(msg.text, end="", flush=True)
                    pending_requests.append(event)
                
                if isinstance(event, WorkflowOutputEvent):
                    conversation = event.data
                    if isinstance(conversation, list):
                        for msg in conversation:
                            if msg.role.value == "assistant" and msg.text:
                                print(msg.text, end="", flush=True)
            
            print()
            
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
