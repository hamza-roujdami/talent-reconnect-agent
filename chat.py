"""
Terminal Chat Interface

Simple CLI for testing the talent reconnect agent locally.

Usage:
    python chat.py                    # Default: Semantic search
    python chat.py --mode bm25        # BM25 keyword search
    python chat.py --mode semantic    # Semantic search (+15-25%)
    python chat.py --verbose          # Show full tool args/results
"""
import argparse
import asyncio
import sys
from workflow import create_workflow
from agent_framework import (
    ChatMessage,
    FunctionCallContent,
    FunctionResultContent,
)

# Parse arguments
parser = argparse.ArgumentParser(description="Talent Reconnect Chat")
parser.add_argument("--mode", "-m", choices=["bm25", "semantic"], 
                    default="semantic", help="Search mode (default: semantic)")
parser.add_argument("--verbose", "-v", action="store_true", help="Show tool details")
args = parser.parse_args()

VERBOSE = args.verbose
SEARCH_MODE = args.mode


async def chat():
    """Main interactive chat loop."""
    mode_labels = {
        "bm25": "BM25 (keyword matching)",
        "semantic": "Semantic (+15-25% relevance)",
    }
    
    print("\n🎯 Talent Reconnect - AI Recruiting Agent")
    print("=" * 50)
    print(f"Search Mode: {mode_labels[SEARCH_MODE]}")
    print("I help you find and reach out to candidates.")
    print("\nWorkflow:")
    print("  1. Understand your requirements")
    print("  2. Search 100k+ resumes")
    print("  3. Generate personalized outreach")
    print("\nType 'quit' to exit\n")
    
    # Create agent with selected search mode
    agent = create_workflow(search_mode=SEARCH_MODE)
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

