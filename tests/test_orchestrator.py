"""
Test script for Orchestrator Agent

Tests the LLM-powered sequential workflow orchestration
"""

import asyncio
from agents.orchestrator_agent import create_orchestrator


async def test_single_step():
    """Test the orchestrator with a single step (Skills Mapping only)"""
    
    print("\n" + "="*60)
    print("🧪 Testing Orchestrator Agent - Single Step")
    print("="*60 + "\n")
    
    # Create orchestrator
    print("🔧 Initializing orchestrator...")
    orchestrator = create_orchestrator()
    print("✅ Orchestrator initialized\n")
    
    # Test input
    test_input = """
I need to find candidates for a Senior Machine Learning Engineer role. 

Job Requirements:
- 5+ years experience in Python and ML
- Azure ML and MLOps experience
- Leadership and team collaboration skills
- Experience with production ML systems
"""
    
    print("📨 Test Input:")
    print(test_input)
    print("\n" + "-"*60 + "\n")
    
    # Run orchestrator
    print("🚀 Running orchestrator workflow...\n")
    
    try:
        result = await orchestrator.route(test_input)
        
        print("\n" + "-"*60)
        print("\n📊 Result:")
        print(result)
        print("\n" + "="*60)
        
        # Show workflow state
        print("\n📈 Workflow State:")
        print(f"  Completed Steps: {orchestrator.workflow_state['completed_steps']}")
        print(f"  Skills Found: {len(orchestrator.workflow_state['skills'])} skills")
        print(f"  Candidates Found: {len(orchestrator.workflow_state['candidates'])} candidates")
        print(f"  Filtered: {len(orchestrator.workflow_state['filtered_candidates'])} candidates")
        print(f"  Enriched: {len(orchestrator.workflow_state['enriched_candidates'])} candidates")
        print(f"  Approved: {len(orchestrator.workflow_state['approved_candidates'])} candidates")
        print(f"  Outreach: {len(orchestrator.workflow_state['outreach_results'])} sent")
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_full_workflow():
    """Test the complete 6-step workflow end-to-end"""
    
    print("\n" + "="*60)
    print("🧪 Testing Complete Workflow (All 6 Steps)")
    print("="*60 + "\n")
    
    # Create orchestrator
    print("🔧 Initializing orchestrator...")
    orchestrator = create_orchestrator()
    print("✅ Orchestrator initialized\n")
    
    # Define all prompts for the workflow
    prompts = [
        # Step 1: Skills Mapping
        """I need to find candidates for a Senior Machine Learning Engineer role.

Job Requirements:
- 5+ years experience in Python and machine learning
- Hands-on experience with Azure ML and MLOps practices
- Strong leadership and team collaboration skills
- Proven track record building production ML systems
- Experience with cloud platforms (Azure preferred)

Company: TechCorp Solutions
Location: Remote or San Francisco Bay Area""",
        
        # Step 2: Resume Sourcing
        "continue to search for candidates",
        
        # Step 3: Historical Feedback
        "continue to apply historical feedback",
        
        # Step 4: Profile Enrichment
        "continue to enrich profiles",
        
        # Step 5: TA Approval (HITL)
        "continue to present for approval",
        
        # Step 6: Outreach
        "approve all candidates and send outreach"
    ]
    
    step_names = [
        "Skills Mapping",
        "Resume Sourcing", 
        "Historical Feedback",
        "Profile Enrichment",
        "TA Approval (HITL)",
        "Outreach"
    ]
    
    # Execute each step
    for i, (prompt, step_name) in enumerate(zip(prompts, step_names), 1):
        print(f"\n{'='*60}")
        print(f"📍 STEP {i}/6: {step_name}")
        print(f"{'='*60}")
        print(f"\n📨 Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        print(f"\n{'─'*60}\n")
        
        try:
            result = await orchestrator.route(prompt)
            
            print(f"✅ Step {i} Complete")
            print(f"\n📊 Response Preview:")
            response_text = str(result)[:500]
            print(response_text + ("..." if len(str(result)) > 500 else ""))
            
            # Show current state
            state = orchestrator.workflow_state
            print(f"\n📈 Current State:")
            print(f"   ✓ Completed: {', '.join(state['completed_steps']) or 'None'}")
            print(f"   📊 Skills: {len(state['skills'])}")
            print(f"   👥 Candidates: {len(state['candidates'])}")
            print(f"   🔍 Filtered: {len(state['filtered_candidates'])}")
            print(f"   📝 Enriched: {len(state['enriched_candidates'])}")
            print(f"   ✅ Approved: {len(state['approved_candidates'])}")
            print(f"   📧 Outreach Sent: {len(state['outreach_results'])}")
            
        except Exception as e:
            print(f"\n❌ Error in Step {i}: {e}")
            import traceback
            traceback.print_exc()
            break
    
    # Final summary
    print(f"\n{'='*60}")
    print("🎉 WORKFLOW COMPLETE")
    print(f"{'='*60}")
    print(f"\n✅ All {len(orchestrator.workflow_state['completed_steps'])} steps completed")
    print(f"📧 {len(orchestrator.workflow_state['outreach_results'])} outreach messages sent")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        print("\n🔄 Running FULL workflow test (all 6 steps)...")
        asyncio.run(test_full_workflow())
    else:
        print("\n🔄 Running SINGLE step test (Skills Mapping only)")
        print("💡 Tip: Use '--full' flag to test complete workflow\n")
        asyncio.run(test_single_step())
