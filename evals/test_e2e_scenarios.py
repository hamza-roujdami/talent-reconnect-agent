"""
End-to-End Scenario Evaluation

Tests full conversation flows through the recruiting agent.
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
    """Load scenarios from golden dataset."""
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path) as f:
        return json.load(f)


async def run_conversation(agent, conversation: list) -> dict:
    """Run a full conversation and check expectations at each step."""
    messages = []
    results = []
    
    for turn in conversation:
        if turn["role"] == "user":
            # Add user message
            messages.append(ChatMessage("user", text=turn["content"]))
            
        elif turn["role"] == "assistant":
            # Get agent response
            tool_calls = []
            response_text = ""
            
            async for event in agent.run_stream(messages):
                if hasattr(event, 'text') and event.text:
                    response_text += event.text
                if hasattr(event, 'contents'):
                    for item in event.contents:
                        if hasattr(item, 'name') and item.name:
                            tool_calls.append(item.name)
            
            # Add assistant message to history
            messages.append(ChatMessage("assistant", text=response_text))
            
            # Check expectations
            turn_result = {
                "passed": True,
                "failures": [],
                "response_preview": response_text[:150] + "..." if len(response_text) > 150 else response_text,
                "tool_calls": tool_calls,
            }
            
            # Check should_contain
            if turn.get("should_contain"):
                response_lower = response_text.lower()
                for keyword in turn["should_contain"]:
                    if keyword.lower() not in response_lower:
                        turn_result["passed"] = False
                        turn_result["failures"].append(f"Missing: '{keyword}'")
            
            # Check should_call
            if turn.get("should_call"):
                if turn["should_call"] not in tool_calls:
                    turn_result["passed"] = False
                    turn_result["failures"].append(f"Expected tool: '{turn['should_call']}'")
            
            results.append(turn_result)
    
    return results


async def run_e2e_eval():
    """Run end-to-end scenario evaluation."""
    print("=" * 60)
    print("End-to-End Scenario Evaluation")
    print("=" * 60)
    
    dataset = load_golden_dataset()
    scenarios = dataset["e2e_scenarios"]
    
    scenario_results = []
    
    for scenario in scenarios:
        print(f"\n🎬 Scenario: {scenario['name']}")
        print(f"   {scenario['description']}")
        print("-" * 40)
        
        # Create fresh agent for each scenario
        agent = create_recruiter("semantic")
        
        turn_results = await run_conversation(agent, scenario["conversation"])
        
        all_passed = all(r["passed"] for r in turn_results)
        scenario_results.append({
            "name": scenario["name"],
            "passed": all_passed,
            "turns": turn_results,
        })
        
        # Print turn-by-turn results
        turn_num = 0
        for i, turn in enumerate(scenario["conversation"]):
            if turn["role"] == "user":
                print(f"\n   👤 User: \"{turn['content'][:50]}...\"" if len(turn['content']) > 50 else f"\n   👤 User: \"{turn['content']}\"")
            elif turn["role"] == "assistant":
                result = turn_results[turn_num]
                status = "✅" if result["passed"] else "❌"
                print(f"   🤖 Agent: {status}")
                if result["tool_calls"]:
                    print(f"      Tools: {', '.join(result['tool_calls'])}")
                if not result["passed"]:
                    for failure in result["failures"]:
                        print(f"      ⚠️ {failure}")
                turn_num += 1
        
        print(f"\n   {'✅ SCENARIO PASSED' if all_passed else '❌ SCENARIO FAILED'}")
    
    # Summary
    passed_scenarios = sum(1 for s in scenario_results if s["passed"])
    total_scenarios = len(scenario_results)
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Scenarios Passed: {passed_scenarios}/{total_scenarios}")
    
    for s in scenario_results:
        status = "✅" if s["passed"] else "❌"
        print(f"  {status} {s['name']}")
    
    return {
        "passed": passed_scenarios,
        "total": total_scenarios,
        "success_rate": passed_scenarios / total_scenarios if total_scenarios > 0 else 0,
    }


if __name__ == "__main__":
    asyncio.run(run_e2e_eval())
