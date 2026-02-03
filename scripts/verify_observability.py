"""Verify observability setup is working.

Run this to test tracing and monitoring are properly configured.

Usage:
    python scripts/verify_observability.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


async def verify_tracing():
    """Verify tracing setup."""
    print("\n" + "="*60)
    print("🔍 OBSERVABILITY VERIFICATION")
    print("="*60)
    
    results = {}
    
    # 1. Check App Insights connection string
    print("\n1️⃣  App Insights Connection String")
    conn_str = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    if conn_str:
        # Parse to get key info
        parts = dict(p.split("=", 1) for p in conn_str.split(";") if "=" in p)
        print(f"   ✅ Found (InstrumentationKey: {parts.get('InstrumentationKey', 'N/A')[:12]}...)")
        results["app_insights"] = True
    else:
        print("   ❌ Not set - telemetry disabled")
        results["app_insights"] = False
    
    # 2. Check Azure Monitor package
    print("\n2️⃣  Azure Monitor Package")
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        print("   ✅ azure-monitor-opentelemetry installed")
        results["azure_monitor"] = True
    except ImportError:
        print("   ❌ azure-monitor-opentelemetry not installed")
        results["azure_monitor"] = False
    
    # 3. Check Foundry telemetry (AIAgentsInstrumentor)
    print("\n3️⃣  Foundry Telemetry (AIAgentsInstrumentor)")
    try:
        from azure.ai.agents.telemetry import AIAgentsInstrumentor
        print("   ✅ AIAgentsInstrumentor available")
        results["foundry_telemetry"] = True
    except ImportError:
        print("   ❌ AIAgentsInstrumentor not available")
        results["foundry_telemetry"] = False
    
    # 4. Check OpenTelemetry tracing
    print("\n4️⃣  OpenTelemetry Tracing")
    try:
        from azure.core.tracing.ext.opentelemetry_span import OpenTelemetrySpan
        print("   ✅ azure-core-tracing-opentelemetry installed")
        results["otel_tracing"] = True
    except ImportError:
        print("   ❌ azure-core-tracing-opentelemetry not installed")
        results["otel_tracing"] = False
    
    # 5. Test actual telemetry setup
    print("\n5️⃣  Initialize Telemetry")
    try:
        from observability import setup_telemetry, enable_foundry_tracing
        
        if await setup_telemetry():
            print("   ✅ Azure Monitor configured")
            results["setup_telemetry"] = True
        else:
            print("   ⚠️  setup_telemetry returned False (check connection string)")
            results["setup_telemetry"] = False
        
        if enable_foundry_tracing():
            print("   ✅ Foundry tracing enabled")
            results["enable_foundry"] = True
        else:
            print("   ⚠️  enable_foundry_tracing returned False")
            results["enable_foundry"] = False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results["setup_telemetry"] = False
        results["enable_foundry"] = False
    
    # 6. Test a simple span
    print("\n6️⃣  Create Test Span")
    try:
        from opentelemetry import trace
        tracer = trace.get_tracer("observability-test")
        
        with tracer.start_as_current_span("test-verification-span") as span:
            span.set_attribute("test.type", "verification")
            span.set_attribute("test.source", "verify_observability.py")
            print("   ✅ Test span created successfully")
            results["test_span"] = True
    except Exception as e:
        print(f"   ❌ Failed to create span: {e}")
        results["test_span"] = False
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, passed_check in results.items():
        status = "✅" if passed_check else "❌"
        print(f"   {status} {check}")
    
    print(f"\n   Result: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All observability checks passed!")
        print("\n📋 Next steps:")
        print("   1. Start the app: python main.py")
        print("   2. Send some chat messages")
        print("   3. Go to Foundry portal → Your Agent → Monitor tab")
        print("   4. Or check App Insights → Transaction search")
    else:
        print("\n⚠️  Some checks failed. Review the output above.")
    
    return passed == total


async def verify_continuous_eval():
    """Show how to set up continuous evaluation."""
    print("\n" + "="*60)
    print("📈 CONTINUOUS EVALUATION (Optional)")
    print("="*60)
    
    print("""
To enable continuous evaluation in Foundry:

1. Assign permissions:
   - Go to Azure Portal → Your Foundry project resource
   - Access control (IAM) → Add role assignment
   - Role: "Azure AI User"
   - Member: Your Foundry project's managed identity

2. Create evaluation rule (Python SDK):

   from azure.ai.projects.models import (
       EvaluationRule,
       ContinuousEvaluationRuleAction,
       EvaluationRuleFilter,
       EvaluationRuleEventType,
   )
   
   # Create eval definition
   eval_object = openai_client.evals.create(
       name="Continuous Evaluation",
       data_source_config={"type": "azure_ai_source", "scenario": "responses"},
       testing_criteria=[
           {"type": "azure_ai_evaluator", "name": "violence_detection", 
            "evaluator_name": "builtin.violence"}
       ],
   )
   
   # Create rule that triggers on response completion
   rule = project_client.evaluation_rules.create_or_update(
       id="continuous-eval-rule",
       evaluation_rule=EvaluationRule(
           display_name="Continuous Eval",
           action=ContinuousEvaluationRuleAction(
               eval_id=eval_object.id, 
               max_hourly_runs=100
           ),
           event_type=EvaluationRuleEventType.RESPONSE_COMPLETED,
           filter=EvaluationRuleFilter(agent_name="orchestrator"),
           enabled=True,
       ),
   )

3. View results:
   - Foundry portal → Agent → Monitor tab
   - Or via SDK: openai_client.evals.runs.list(eval_id=eval_object.id)
""")


if __name__ == "__main__":
    print("\n🔬 Talent Reconnect - Observability Verification\n")
    
    success = asyncio.run(verify_tracing())
    asyncio.run(verify_continuous_eval())
    
    sys.exit(0 if success else 1)
