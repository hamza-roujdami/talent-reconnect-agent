# Guardrails

Input validation and safety guardrails for the recruiting agent.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User Input    │ ──► │  Local Filter    │ ──► │ Foundry Agent   │
│                 │     │  (input_filter)  │     │   + Guardrails  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │                         │
                              ▼                         ▼
                        Fast local check         Microsoft.DefaultV2
                        (prompt injection)       policy handles:
                                                 - Hate, Violence
                                                 - Sexual, Self-harm
                                                 - Prompt attacks
                                                 - Protected material
```

## Two Layers of Protection

### 1. Local Filter (input_filter.py)

Fast pattern matching that runs **before** API calls:

```python
from guardrails import check_input_safety

result = await check_input_safety("user message")
if not result.is_safe:
    return f"Blocked: {result.reason}"
```

Catches obvious injection patterns like:
- "ignore previous instructions"
- "jailbreak", "developer mode"
- "reveal your instructions"

### 2. Foundry Guardrails (Built-in)

Your agents automatically use `Microsoft.DefaultV2` guardrail which scans:

| Intervention Point | What It Checks |
|-------------------|----------------|
| **User input** | Incoming prompts |
| **Tool call** | Tool invocations (agents only) |
| **Tool response** | Results from tools |
| **Output** | Final response |

For these risks:
- Hate & Fairness
- Sexual content
- Self-harm
- Violence
- Prompt attacks
- Indirect attacks
- Protected material (code/text)
- PII (preview)

## Configure Custom Guardrails

### Via Foundry Portal

1. Go to [ai.azure.com](https://ai.azure.com) → your project
2. Select **Build** → **Guardrails**
3. Click **Create Guardrail**
4. Add controls for specific risks
5. Assign to your model or agent

### Via API (Request-time override)

You can specify a guardrail per-request using headers:

```python
# Not yet exposed in our factory, but Foundry supports this
response = await client.chat.completions.create(
    ...,
    extra_headers={"x-ms-rai-policy-id": "your-custom-policy"}
)
```

## Adding Custom Injection Patterns

Edit `INJECTION_PATTERNS` in [input_filter.py](input_filter.py):

```python
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "your custom pattern here",
    ...
]
```

## Testing Guardrails

In Foundry portal:
1. Go to **Guardrails** → select your guardrail
2. Click **Try in Playground**
3. Send test queries to see what gets blocked

Blocked content shows details about which risk was detected.
