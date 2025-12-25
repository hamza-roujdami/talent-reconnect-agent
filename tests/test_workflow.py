#!/usr/bin/env python3
"""
Terminal-based workflow tester.

Run: python tests/test_workflow.py
"""
import asyncio
from agents.factory import create_recruiting_workflow
from agent_framework import (
    AgentRunUpdateEvent,
    FunctionCallContent,
    FunctionResultContent,
    WorkflowOutputEvent,
    RequestInfoEvent,
)

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_agent(name):
    print(f"{Colors.CYAN}🤖 Agent: {name}{Colors.ENDC}")

def print_tool_call(name, args):
    print(f"{Colors.YELLOW}  🔧 Tool Call: {name}{Colors.ENDC}")
    if args:
        print(f"{Colors.YELLOW}     Args: {args[:200]}...{Colors.ENDC}" if len(str(args)) > 200 else f"{Colors.YELLOW}     Args: {args}{Colors.ENDC}")

def print_tool_result(result):
    print(f"{Colors.GREEN}  📤 Tool Result:{Colors.ENDC}")
    # Print first 500 chars of result
    result_str = str(result)
    if len(result_str) > 500:
        print(f"{Colors.GREEN}     {result_str[:500]}...{Colors.ENDC}")
    else:
        print(f"{Colors.GREEN}     {result_str}{Colors.ENDC}")

def print_text(text):
    if text.strip():
        print(f"{Colors.BLUE}  💬 Text: {text}{Colors.ENDC}")

def print_user(text):
    print(f"\n{Colors.BOLD}👤 User: {text}{Colors.ENDC}\n")

async def run_workflow_test():
    """Run interactive workflow test."""
    print_header("Talent Reconnect - Workflow Test")
    
    # Create workflow
    print("Creating workflow...")
    workflow = create_recruiting_workflow()
    print("✅ Workflow created\n")
    
    pending_requests = []
    
    # Test conversation
    test_messages = [
        "Senior AI Engineer in Dubai",
        # Add more test messages as needed
    ]
    
    for user_message in test_messages:
        print_user(user_message)
        
        # Run workflow
        if pending_requests:
            responses = {req.request_id: user_message for req in pending_requests}
            pending_requests = []
            stream = workflow.send_responses_streaming(responses)
        else:
            stream = workflow.run_stream(user_message)
        
        current_agent = None
        
        async for event in stream:
            if isinstance(event, AgentRunUpdateEvent):
                # Track agent changes
                if event.executor_id != current_agent:
                    current_agent = event.executor_id
                    print_agent(current_agent)
                
                data = event.data
                
                # Process contents (tool calls and results)
                if hasattr(data, 'contents') and data.contents:
                    for item in data.contents:
                        if isinstance(item, FunctionCallContent):
                            print_tool_call(item.name, item.arguments)
                        elif isinstance(item, FunctionResultContent):
                            print_tool_result(item.result)
                
                # Process text output
                if hasattr(data, 'text') and data.text:
                    print_text(data.text)
            
            elif isinstance(event, RequestInfoEvent):
                pending_requests.append(event)
                print(f"{Colors.RED}⏳ Waiting for user input...{Colors.ENDC}")
            
            elif isinstance(event, WorkflowOutputEvent):
                if event.output:
                    print(f"\n{Colors.GREEN}✅ Workflow Output: {event.output}{Colors.ENDC}")
        
        print("\n" + "-"*60)
    
    print_header("Test Complete")

async def interactive_mode():
    """Run interactive chat mode."""
    print_header("Talent Reconnect - Interactive Mode")
    print("Type 'quit' to exit\n")
    
    workflow = create_recruiting_workflow()
    pending_requests = []
    
    while True:
        try:
            user_input = input(f"{Colors.BOLD}👤 You: {Colors.ENDC}")
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            if not user_input.strip():
                continue
            
            print()  # Blank line
            
            # Run workflow
            if pending_requests:
                responses = {req.request_id: user_input for req in pending_requests}
                pending_requests = []
                stream = workflow.send_responses_streaming(responses)
            else:
                stream = workflow.run_stream(user_input)
            
            current_agent = None
            
            async for event in stream:
                if isinstance(event, AgentRunUpdateEvent):
                    if event.executor_id != current_agent:
                        current_agent = event.executor_id
                        print_agent(current_agent)
                    
                    data = event.data
                    
                    if hasattr(data, 'contents') and data.contents:
                        for item in data.contents:
                            if isinstance(item, FunctionCallContent):
                                print_tool_call(item.name, item.arguments)
                            elif isinstance(item, FunctionResultContent):
                                print_tool_result(item.result)
                    
                    if hasattr(data, 'text') and data.text:
                        print_text(data.text)
                
                elif isinstance(event, RequestInfoEvent):
                    pending_requests.append(event)
            
            print()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
    
    print("\n👋 Goodbye!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run predefined test
        asyncio.run(run_workflow_test())
    else:
        # Interactive mode
        asyncio.run(interactive_mode())
