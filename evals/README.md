# Evaluation Framework

Evaluation suite for the Talent Reconnect Agent.

> ⚠️ **Demo purposes only** - Simplified evaluation for demonstration.

## Overview

| Eval Type | Script | What it Tests |
|-----------|--------|---------------|
| **Search Quality** | `test_search_quality.py` | Precision/Recall of candidate search |
| **Agent Behavior** | `test_agent_behavior.py` | Workflow compliance (JD → Search → Email) |
| **E2E Scenarios** | `test_e2e_scenarios.py` | Full conversation flows |

## Quick Start

```bash
# Run all evals
python -m pytest evals/ -v

# Run specific eval
python evals/test_search_quality.py
python evals/test_agent_behavior.py
python evals/test_e2e_scenarios.py
```

## 1. Search Quality Evaluation

Tests how well the search finds relevant candidates.

**Metrics:**
- **Precision@5**: % of top-5 results that are relevant
- **MRR**: Mean Reciprocal Rank (how high is first good result?)
- **BM25 vs Semantic**: Compare search modes

```bash
python evals/test_search_quality.py
```

**Sample Output:**
```
Query: "Senior ML Engineer PyTorch Dubai"
  BM25 Precision@5: 40%
  Semantic Precision@5: 80%
  Semantic MRR: 0.83
```

## 2. Agent Behavior Evaluation

Tests if agent follows the HITL workflow correctly.

**Test Cases:**
| Input | Expected Behavior |
|-------|-------------------|
| "I need an ML engineer" | Generate JD or ask clarifying questions |
| "yes" (after JD) | Call `search_resumes` tool |
| "contact 1 and 3" | Call `send_outreach_email` tool |
| "refine for more senior" | Search again with updated criteria |

```bash
python evals/test_agent_behavior.py
```

## 3. End-to-End Scenarios

Tests full recruiting conversations.

**Scenarios:**
1. **Happy Path**: Requirements → JD → Search → Select → Email
2. **Refinement**: Search → "more senior" → Re-search
3. **Clarification**: Vague request → Agent asks questions

```bash
python evals/test_e2e_scenarios.py
```

## Golden Dataset

Test queries with expected behaviors in `golden_dataset.json`:

```json
{
  "search_queries": [
    {
      "query": "Senior Python developer Dubai 5 years",
      "relevant_skills": ["Python", "Django", "FastAPI"],
      "min_experience": 5,
      "location": "Dubai"
    }
  ],
  "behavior_tests": [
    {
      "input": "I need an ML engineer",
      "expected_action": "generate_jd_or_clarify"
    }
  ]
}
```

## Metrics Summary

After running evals:

```
┌─────────────────────────────────────────────────┐
│           Evaluation Results                    │
├─────────────────────────────────────────────────┤
│ Search Quality                                  │
│   Semantic Precision@5: 76%                     │
│   Semantic MRR: 0.81                            │
│   BM25 vs Semantic: +18% relevance              │
├─────────────────────────────────────────────────┤
│ Agent Behavior                                  │
│   Workflow Compliance: 9/10 tests passed        │
│   Tool Call Accuracy: 95%                       │
├─────────────────────────────────────────────────┤
│ E2E Scenarios                                   │
│   Happy Path: ✅ Pass                           │
│   Refinement Flow: ✅ Pass                      │
│   Edge Cases: 4/5 Pass                          │
└─────────────────────────────────────────────────┘
```

## Adding New Tests

1. Add test queries to `golden_dataset.json`
2. Run evals to establish baseline
3. Make changes to agent
4. Re-run evals to measure impact
