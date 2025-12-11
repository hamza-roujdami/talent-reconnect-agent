"""
Talent Reconnect Agent - Main Application

MAF WorkflowBuilder with HITL pattern for talent acquisition:
1. JD Generation → HITL pause → "proceed?"
2. Resume Matching → HITL pause → "send emails?"  
3. Outreach → Complete
"""

import asyncio
from workflow import create_talent_reconnect_workflow, HITLRequest


async def interactive_terminal():
    """
    Run the MAF workflow in interactive terminal mode.
    
    Demonstrates:
    - WorkflowBuilder orchestration
    - HITL with ctx.request_info() and @response_handler
    - Multi-agent coordination
    """
    print("=" * 60)
    print("🎯 Talent Reconnect Agent - MAF Workflow Demo")
    print("=" * 60)
    print("Powered by Microsoft Agent Framework + Compass LLM")
    print("Type 'quit' to exit\n")
    
    # Create the MAF workflow
    print("🔧 Initializing MAF Workflow...")
    workflow = create_talent_reconnect_workflow()
    print("✅ Workflow ready!\n")
    
    # Track pending responses
    responses: dict[str, str] = {}
    is_first_run = True
    
    while True:
        try:
            # Get user input
            if is_first_run:
                user_input = input("👤 You: ").strip()
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\n👋 Goodbye!")
                    break
                if not user_input:
                    user_input = "hi"  # Default to greeting
            
            # Run workflow or send response
            if responses:
                events = await workflow.send_responses(responses)
                responses.clear()
            else:
                events = await workflow.run(user_input)
                is_first_run = False
            
            # Handle HITL request_info events
            request_info_events = events.get_request_info_events()
            for event in request_info_events:
                if not isinstance(event.data, HITLRequest):
                    continue
                
                hitl_request: HITLRequest = event.data
                
                # Display agent output
                print(f"\n🤖 Agent:\n{hitl_request.output}\n")
                
                # Get user response
                user_response = input("👤 You: ").strip()
                
                if user_response.lower() in ["quit", "exit", "q"]:
                    print("\n👋 Goodbye!")
                    return
                
                # Store response for next iteration
                responses[event.request_id] = user_response
            
            # Check for workflow completion (outputs)
            if outputs := events.get_outputs():
                for output in outputs:
                    print(f"\n🤖 Agent:\n{output}\n")
                print("=" * 60)
                print("✅ Workflow Complete!")
                print("=" * 60)
                
                # Ask if user wants to start again
                again = input("\n🔄 Start a new search? (yes/no): ").strip().lower()
                if again in ["yes", "y", ""]:
                    responses.clear()
                    is_first_run = True
                    workflow = create_talent_reconnect_workflow()  # Reset workflow
                    print("\n" + "=" * 60 + "\n")
                else:
                    print("\n👋 Goodbye!")
                    break
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            break


async def run_demo_flow():
    """
    Run automated demo of the full workflow.
    Useful for testing and demonstrations.
    """
    print("=" * 60)
    print("🎯 Talent Reconnect - Automated Demo")
    print("=" * 60)
    
    workflow = create_talent_reconnect_workflow()
    responses = {}
    
    # Simulated user inputs
    demo_inputs = [
        "hi",                              # Trigger welcome
        "AI Engineer",                     # Provide job role
        "proceed",                         # Approve JD
        "send emails to top 3 candidates"  # Send outreach
    ]
    input_index = 0
    
    while input_index < len(demo_inputs):
        user_input = demo_inputs[input_index]
        
        print(f"\n👤 User: {user_input}")
        
        # Run or send response
        if responses:
            events = await workflow.send_responses(responses)
            responses.clear()
        else:
            events = await workflow.run(user_input)
        
        # Handle HITL events
        for event in events.get_request_info_events():
            if isinstance(event.data, HITLRequest):
                print(f"\n🤖 Agent:\n{event.data.output}\n")
                
                # Get next simulated input
                input_index += 1
                if input_index < len(demo_inputs):
                    responses[event.request_id] = demo_inputs[input_index]
        
        # Check for completion
        if outputs := events.get_outputs():
            for output in outputs:
                print(f"\n🤖 Agent:\n{output}\n")
            print("\n✅ Demo Complete!")
            break
        
        input_index += 1


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        asyncio.run(run_demo_flow())
    else:
        asyncio.run(interactive_terminal())
