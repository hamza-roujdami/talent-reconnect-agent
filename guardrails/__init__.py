"""Guardrails package.

Content safety is handled by Foundry Guardrails at the model/agent level.
See README.md for configuration details.
"""

# No local filters needed - Foundry Guardrails (Microsoft.DefaultV2) handles:
# - Hate, violence, sexual, self-harm content
# - Prompt attacks and indirect attacks
# - Protected material and PII
