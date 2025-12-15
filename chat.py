"""
Terminal Chat Interface

Simple CLI for testing the talent reconnect agent locally.
Run with: python chat.py
         python chat.py --verbose  # Show full tool args/results
"""
import asyncio
import sys
from workflow import create_workflow
from agent_framework import (
    ChatMessage,
    FunctionCallContent,
    FunctionResultContent,
)

VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv


async def chat():
    """Main interactive chat loop."""
    print("\n🎯 Talent Reconnect - AI Recruiting Agent")
    print("=" * 50)
    print("I help you find and reach out to candidates.")
    print("\nWorkflow:")
    print("  1. Understand your requirements")
    print("  2. Search 100k+ resumes")
    print("  3. Generate personalized outreach")
    print("\nType 'quit' to exit\n")
    
    # Create agent
    agent = create_workflow()
    messages = []
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "quit":
                print("\nGoodbye! 👋")
                break
            
            # Add user message
            messages.append(ChatMessage("user", text=user_input))
            
            # Run agent
            print("\nAssistant: ", end="", flush=True)
            response_text = ""
            
            async for event in agent.run_stream(messages):
                # Show tool calls
                if hasattr(event, 'contents'):
                    for item in event.contents:
                        if isinstance(item, FunctionCallContent) and item.name:
                            print(f"\n  🔧 {item.name}", flush=True)
                            if VERBOSE and item.arguments:
                                print(f"     Args: {item.arguments}")
                        if isinstance(item, FunctionResultContent) and VERBOSE:
                            result = str(item.result)[:500] if item.result else "None"
                            print(f"     Result: {result}...")
                
                # Stream text - event.text is the delta chunk, print it directly
                if hasattr(event, 'text') and event.text:
                    print(event.text, end="", flush=True)
                    response_text += event.text
            
            if response_text:
                print()  # Newline after streaming completes
                messages.append(ChatMessage("assistant", text=response_text))
            
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

