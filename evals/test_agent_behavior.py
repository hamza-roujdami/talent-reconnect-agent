"""
Agent Behavior Evaluation

Tests if agent follows the HITL workflow correctly.
"""
import asyncio
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_framework import ChatMessage
from agents.factory import create_recruiter


def load_golden_dataset():
    """Load test cases from golden dataset."""
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path) as f:
        return json.load(f)


async def test_single_response(agent, input_text: str, expected: dict) -> dict:
    """Test a single agent response against expectations."""
    messages = [ChatMessage("user", text=input_text)]
    
    # Track tool calls
    tool_calls = []
    response_text = ""
    
    async for event in agent.run_stream(messages):
        if hasattr(event, 'text') and event.text:
            response_text += event.text
        if hasattr(event, 'contents'):
            for item in event.contents:
                if hasattr(item, 'name') and item.name:
                    tool_calls.append(item.name)
    
    # Check expectations
    result = {
        "input": input_text,
        "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text,
        "tool_calls": tool_calls,
        "passed": True,
        "failures": [],
    }
    
    # Check if expected tool was called
    if expected.get("expected_tool"):
        if expected["expected_tool"] not in tool_calls:
            result["passed"] = False
            result["failures"].append(f"Expected tool '{expected['expected_tool']}' not called")
    
    # Check if response contains expected content
    if expected.get("should_contain"):
        response_lower = response_text.lower()
        for keyword in expected["should_contain"]:
            if keyword.lower() not in response_lower:
                result["passed"] = False
                result["failures"].append(f"Response missing expected keyword: '{keyword}'")
    
    return result


async def run_behavior_eval():
    """Run agent behavior evaluation."""
    print("=" * 60)
    print("Agent Behavior Evaluation")
    print("=" * 60)
    
    dataset = load_golden_dataset()
    tests = dataset["behavior_tests"]
    
    # Create agent (semantic mode)
    agent = create_recruiter("semantic")
    
    results = []
    passed = 0
    failed = 0
    
    for test in tests:
        # Skip tests that require conversation context for now
        if test.get("context"):
            print(f"\n⏭️  Skipping: {test['id']} (requires context)")
            continue
        
        print(f"\n🧪 Test: {test['id']}")
        print(f"   Input: \"{test['input']}\"")
        print(f"   Description: {test['description']}")
        
        result = await test_single_response(agent, test["input"], test)
        results.append(result)
        
        if result["passed"]:
            passed += 1
            print(f"   ✅ PASSED")
        else:
            failed += 1
            print(f"   ❌ FAILED")
            for failure in result["failures"]:
                print(f"      - {failure}")
        
        if result["tool_calls"]:
            print(f"   Tools called: {', '.join(result['tool_calls'])}")
    
    # Summary
    total = passed + failed
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {failed}/{total}")
    print(f"Success Rate: {passed/total:.0%}" if total > 0 else "No tests run")
    
    return {
        "passed": passed,
        "failed": failed,
        "total": total,
        "success_rate": passed / total if total > 0 else 0,
    }


if __name__ == "__main__":
    asyncio.run(run_behavior_eval())
