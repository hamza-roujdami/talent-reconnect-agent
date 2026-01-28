"""
Agent Behavior Evaluation

Tests if the multi-agent workflow follows the correct handoff patterns.
"""
import asyncio
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_framework import AgentRunUpdateEvent, Content
from agents.factory import create_recruiting_workflow


def load_golden_dataset():
    """Load test cases from golden dataset."""
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path) as f:
        return json.load(f)


async def test_single_response(workflow, input_text: str, expected: dict) -> dict:
    """Test a single workflow response against expectations."""
    # Track tool calls and response
    tool_calls = []
    response_text = ""
    agents_seen = []
    
    async for event in workflow.run_stream(input_text):
        if isinstance(event, AgentRunUpdateEvent):
            if event.executor_id and event.executor_id not in agents_seen:
                agents_seen.append(event.executor_id)
            
            data = event.data
            if hasattr(data, 'text') and data.text:
                response_text += data.text
            if hasattr(data, 'contents') and data.contents:
                for item in data.contents:
                    if isinstance(item, Content) and item.type == 'function_call' and item.name:
                        if not item.name.startswith('handoff_'):
                            tool_calls.append(item.name)
    
    # Check expectations
    result = {
        "input": input_text,
        "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text,
        "tool_calls": tool_calls,
        "agents_seen": agents_seen,
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
    print("Multi-Agent Workflow Behavior Evaluation")
    print("=" * 60)
    
    dataset = load_golden_dataset()
    tests = dataset["behavior_tests"]
    
    # Create workflow
    workflow = create_recruiting_workflow()
    
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
        
        result = await test_single_response(workflow, test["input"], test)
        results.append(result)
        
        if result["passed"]:
            passed += 1
            print(f"   ✅ PASSED")
        else:
            failed += 1
            print(f"   ❌ FAILED")
            for failure in result["failures"]:
                print(f"      - {failure}")
        
        if result["agents_seen"]:
            print(f"   Agents: {' → '.join(result['agents_seen'])}")
        if result["tool_calls"]:
            print(f"   Tools: {', '.join(result['tool_calls'])}")
    
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
