# Agent Evaluations

Evaluation framework for testing agent quality and safety using Azure AI Foundry Evaluations.

## Quick Start

```bash
# Run evaluations against golden dataset
python -m evals.evaluator

# Or from Python
from evals import AgentEvaluator

evaluator = AgentEvaluator()
await evaluator.initialize()

result = await evaluator.evaluate(
    query="Find Python developers",
    response="I found 5 candidates...",
)
print(f"Relevance: {result.relevance}")
```

## Metrics

| Metric | Description | Threshold |
|--------|-------------|-----------|
| **Relevance** | How well the response addresses the query | 3.0/5.0 |
| **Groundedness** | Is the response grounded in provided context? | 3.0/5.0 |
| **Coherence** | Is the response well-structured and logical? | 3.0/5.0 |
| **Fluency** | Is the response readable and natural? | 3.0/5.0 |

## Golden Dataset

[golden_dataset.json](golden_dataset.json) contains test cases for:

- **Search queries** - Finding candidates with specific skills
- **Profile queries** - Defining job requirements  
- **Insights queries** - Checking interview feedback
- **Outreach queries** - Drafting emails
- **Edge cases** - Greetings, confirmations
- **Adversarial** - Prompt injection attempts

## Foundry Evaluators vs Heuristics

The evaluator automatically uses:

1. **Foundry GPT Evaluators** (if `azure-ai-evaluation` installed)
   - More accurate, uses GPT-4 for evaluation
   - Requires Foundry endpoint

2. **Heuristic Fallback** (default)
   - Basic keyword/structure matching
   - Good for quick local testing

Install Foundry evaluators:
```bash
pip install azure-ai-evaluation
```

## Running in CI/CD

```yaml
# GitHub Actions example
- name: Run Agent Evaluations
  run: |
    python -m evals.evaluator
  env:
    PROJECT_ENDPOINT: ${{ secrets.PROJECT_ENDPOINT }}
```

## Custom Evaluations

```python
from evals import AgentEvaluator, EvalResult

class CustomEvaluator(AgentEvaluator):
    THRESHOLDS = {
        "relevance": 4.0,  # Stricter
        "groundedness": 3.5,
        "coherence": 3.0,
        "fluency": 3.0,
    }
```
