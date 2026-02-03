# Observability

Tracing, monitoring, and evaluation using Azure AI Foundry's native telemetry.

## Structure

```
observability/
├── __init__.py         # Package exports
├── tracing.py          # Foundry telemetry + Azure Monitor
├── README.md           # This file
└── evals/              # Agent evaluation framework
    ├── evaluator.py    # Foundry GPT evaluators
    ├── metrics.py      # Heuristic fallback metrics
    └── golden_dataset.json  # Test cases
```

## Foundry Native Tracing

Foundry SDK provides `enable_telemetry()` which auto-instruments:
- Azure AI Agents (`azure-ai-agents`)
- Azure AI Inference (`azure-ai-inference`)
- OpenAI calls
- LangChain (if installed)

### Setup

```python
from observability import setup_telemetry, enable_foundry_tracing

# At app startup
if await setup_telemetry():
    print("✓ Azure Monitor configured")
    
# Enable Foundry SDK tracing
enable_foundry_tracing()
```

### Environment Variables

```bash
# Required for Azure Monitor export
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...

# Optional: Enable content recording (prompts/completions)
AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED=true
```

### What Gets Traced

With Foundry tracing enabled, you automatically get:
- Agent creation and execution
- Tool calls and responses
- Model inference calls
- Token usage metrics

### View in Azure Portal

1. Go to your App Insights resource (`tragt-appi`)
2. **Transaction search** - see individual requests
3. **Application map** - visualize agent → tool → model calls
4. **Live metrics** - real-time monitoring

### Local Development

For local debugging without Azure:

```python
import sys
from observability import enable_foundry_tracing

# Print traces to console
enable_foundry_tracing(destination=sys.stdout)
```

Or use Aspire Dashboard:
```python
enable_foundry_tracing(destination="http://localhost:4317")
```

## Evaluations (evals/)

Framework for testing agent response quality.

### Metrics

| Metric | Description | Threshold |
|--------|-------------|-----------|
| Relevance | Does response address the query? | 3.0/5.0 |
| Groundedness | Is response based on context? | 3.0/5.0 |
| Coherence | Is response well-structured? | 3.0/5.0 |
| Fluency | Is response natural? | 3.0/5.0 |

### Run Evaluations

```python
from observability.evals import AgentEvaluator

evaluator = AgentEvaluator()
await evaluator.initialize()

result = await evaluator.evaluate(
    query="Find Python developers in Dubai",
    response="I found 5 candidates matching...",
    context="Resume data from search",
)

print(f"Relevance: {result.relevance}")
print(f"Pass: {result.passed}")
```

### Golden Dataset

[evals/golden_dataset.json](evals/golden_dataset.json) contains test cases for:

- Search queries
- Profile building
- Interview insights
- Outreach emails
- Adversarial inputs

### CI/CD Integration

```yaml
- name: Run Agent Evaluations
  run: python -m observability.evals.evaluator
  env:
    PROJECT_ENDPOINT: ${{ secrets.PROJECT_ENDPOINT }}
```
