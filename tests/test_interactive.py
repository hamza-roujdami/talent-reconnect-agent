"""
Interactive Test for Talent Reconnect Agent
Run this to test the orchestrator without Gradio UI
"""
import asyncio
import sys
from agents.orchestrator_agent import create_orchestrator


async def main():
    print("=" * 80)
    print("🎯 Talent Reconnect Agent - Interactive Test")
    print("=" * 80)
    print("\nInitializing orchestrator...")
    
    orchestrator = create_orchestrator()
    print("✅ Orchestrator ready!\n")
    
    # Test prompt
    test_prompt = """I need to find candidates for a Senior Machine Learning Engineer role.

Job Requirements:
- 5+ years experience in Python and machine learning
- Hands-on experience with Azure ML and MLOps practices
- Strong leadership and team collaboration skills
- Proven track record building production ML systems
- Experience with cloud platforms (Azure preferred)

Company: TechCorp Solutions
Location: Remote or San Francisco Bay Area"""
    
    print("📝 Test Prompt:")
    print("-" * 80)
    print(test_prompt)
    print("-" * 80)
    print("\n🚀 Starting workflow...\n")
    
    try:
        # Route the initial request
        response = await orchestrator.route(test_prompt)
        print(f"\n📋 Response:")
        print("=" * 80)
        if hasattr(response, 'text'):
            print(response.text)
        elif hasattr(response, 'content'):
            print(response.content)
        else:
            print(str(response))
        print("=" * 80)
        
        # Interactive mode
        print("\n\n💬 Continue the workflow by typing 'continue', 'next', or ask questions.")
        print("Type 'quit' or 'exit' to stop.\n")
        
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            print(f"\n🤖 Processing...\n")
            response = await orchestrator.route(user_input)
            
            print("📋 Response:")
            print("-" * 80)
            if hasattr(response, 'text'):
                print(response.text)
            elif hasattr(response, 'content'):
                print(response.content)
            else:
                print(str(response))
            print("-" * 80)
            print()
            
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
