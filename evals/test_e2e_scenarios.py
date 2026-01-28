"""
End-to-End Scenario Evaluation

Tests full conversation flows through the multi-agent recruiting workflow.
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
    """Load scenarios from golden dataset."""
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path) as f:
        return json.load(f)


async def run_conversation(workflow, conversation: list) -> list:
    """Run a full conversation and check expectations at each step."""
    results = []
    
    for turn in conversation:
        if turn["role"] == "user":
            user_input = turn["content"]
            
            # Get workflow response
            tool_calls = []
            response_text = ""
            agents_seen = []
            
            async for event in workflow.run_stream(user_input):
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
            
            # Check expectations from next assistant turn
            expected = next((t for t in conversation if t["role"] == "assistant" and t.get("after") == turn.get("id")), None)
            
            turn_result = {
                "user_input": user_input,
                "passed": True,
                "failures": [],
                "response_preview": response_text[:150] + "..." if len(response_text) > 150 else response_text,
                "tool_calls": tool_calls,
                "agents_seen": agents_seen,
            }
            
            if expected:
                # Check should_contain
                if expected.get("should_contain"):
                    response_lower = response_text.lower()
                    for keyword in expected["should_contain"]:
                        if keyword.lower() not in response_lower:
                            turn_result["passed"] = False
                            turn_result["failures"].append(f"Missing: '{keyword}'")
                
                # Check should_call
                if expected.get("should_call"):
                    if expected["should_call"] not in tool_calls:
                        turn_result["passed"] = False
                        turn_result["failures"].append(f"Expected tool: '{expected['should_call']}'")
            
            results.append(turn_result)
    
    return results


async def run_e2e_eval():
    """Run end-to-end scenario evaluation."""
    print("=" * 60)
    print("End-to-End Multi-Agent Scenario Evaluation")
    print("=" * 60)
    
    dataset = load_golden_dataset()
    scenarios = dataset.get("e2e_scenarios", [])
    
    if not scenarios:
        print("\n⚠️ No e2e_scenarios found in golden_dataset.json")
        return {"passed": 0, "total": 0, "success_rate": 0}
    
    scenario_results = []
    
    for scenario in scenarios:
        print(f"\n🎬 Scenario: {scenario['name']}")
        print(f"   {scenario['description']}")
        print("-" * 40)
        
        # Create fresh workflow for each scenario
        workflow = create_recruiting_workflow()
        
        turn_results = await run_conversation(workflow, scenario["conversation"])
        
        all_passed = all(r["passed"] for r in turn_results)
        scenario_results.append({
            "name": scenario["name"],
            "passed": all_passed,
            "turns": turn_results,
        })
        
        # Print turn-by-turn results
        for result in turn_results:
            status = "✅" if result["passed"] else "❌"
            print(f"\n   👤 User: \"{result['user_input'][:50]}...\"" if len(result['user_input']) > 50 else f"\n   👤 User: \"{result['user_input']}\"")
            print(f"   🤖 Response: {status}")
            if result["agents_seen"]:
                print(f"      Agents: {' → '.join(result['agents_seen'])}")
            if result["tool_calls"]:
                print(f"      Tools: {', '.join(result['tool_calls'])}")
            if not result["passed"]:
                for failure in result["failures"]:
                    print(f"      ⚠️ {failure}")
        
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
