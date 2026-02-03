"""Input validation middleware with local prompt injection detection.

Fast local filtering for obvious attacks. Foundry Guardrails handles
content safety at the model/agent level (hate, violence, sexual, etc.).

Usage:
    from safety import check_input_safety
    
    result = await check_input_safety("user message")
    if not result.is_safe:
        return f"Blocked: {result.reason}"
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SafetyResult:
    """Result of input safety check."""
    is_safe: bool
    reason: Optional[str] = None


# Known prompt injection patterns (fast local check)
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "disregard your instructions",
    "forget your rules",
    "you are now",
    "pretend you are",
    "act as if you",
    "jailbreak",
    "developer mode",
    "sudo mode",
    "system prompt",
    "reveal your instructions",
    "what are your instructions",
]


def check_injection_patterns(text: str) -> SafetyResult:
    """Check for known prompt injection patterns (fast, local)."""
    text_lower = text.lower()
    
    for pattern in INJECTION_PATTERNS:
        if pattern in text_lower:
            logger.warning(f"Blocked prompt injection attempt: '{pattern}' detected")
            return SafetyResult(
                is_safe=False,
                reason="Potential prompt injection detected",
            )
    
    return SafetyResult(is_safe=True)


async def check_input_safety(text: str) -> SafetyResult:
    """Check user input for safety issues.
    
    Fast local check for prompt injection patterns.
    Foundry Guardrails handles content safety at the model level.
    
    Args:
        text: User input to check
        
    Returns:
        SafetyResult with is_safe flag and reason if blocked
    """
    return check_injection_patterns(text)
