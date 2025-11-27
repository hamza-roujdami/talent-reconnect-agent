"""
Interactive terminal test for HITL workflow
"""
import asyncio
from agents.supervisor import SupervisorWorkflow


async def interactive_test():
    """Test the interactive workflow in terminal"""
    print("="*60)
    print("🎯 Interactive Workflow Test")
    print("="*60)
    
    # Initialize workflow
    supervisor = SupervisorWorkflow()
    
    # Get job description from user
    print("\n📝 Enter job description (or press Enter for default):")
    user_input = input("> ").strip()
    
    if not user_input:
        user_input = "Need Senior Machine Learning Engineer with Python, Azure, and MLOps experience at TechCorp Solutions"
        print(f"Using default: {user_input}")
    
    print(f"\n💬 Starting workflow with: {user_input}\n")
    
    # Start workflow
    responses = {}
    
    while True:
        # Run or resume workflow
        if responses:
            events = await supervisor.workflow.send_responses(responses)
            responses.clear()
        else:
            events = await supervisor.workflow.run(user_input)
        
        # Handle approval requests
        request_info_events = events.get_request_info_events()
        if request_info_events:
            for request_info_event in request_info_events:
                approval_request = request_info_event.data
                request_id = request_info_event.request_id
                
                # Display step output
                print(f"\n{'='*60}")
                print(f"✅ {approval_request.step_name} COMPLETE")
                print(f"{'='*60}")
                print(f"\n{approval_request.output}\n")
                print(f"{'='*60}")
                print(f"⏸️  {approval_request.prompt}")
                print(f"{'='*60}")
                
                # Get user input
                user_response = input("\n👉 Your response: ").strip()
                
                if not user_response:
                    # Default to 'continue' or 'email' based on step
                    if approval_request.step_num == 6:
                        user_response = "email"
                        print(f"   (defaulting to: {user_response})")
                    else:
                        user_response = "continue"
                        print(f"   (defaulting to: {user_response})")
                
                responses[request_id] = user_response
                print(f"\n✓ Approved with: '{user_response}'\n")
            
            continue
        
        # Check for outputs (workflow complete)
        if outputs := events.get_outputs():
            final_output = outputs[0]
            print(f"\n{'='*60}")
            print("🎉 WORKFLOW COMPLETE")
            print(f"{'='*60}\n")
            print(final_output)
            print(f"\n{'='*60}\n")
            break


if __name__ == "__main__":
    try:
        asyncio.run(interactive_test())
    except KeyboardInterrupt:
        print("\n\n⚠️  Workflow interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
