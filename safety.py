"""Content Safety middleware for input validation.

Uses Azure AI Content Safety to detect:
- Prompt injection attempts
- Jailbreak attempts
- Harmful content (hate, violence, sexual, self-harm)

Usage:
    from safety import ContentSafetyFilter
    
    filter = ContentSafetyFilter()
    await filter.initialize()
    
    result = await filter.check_input("user message")
    if not result.is_safe:
        return f"Blocked: {result.reason}"
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class SafetyResult:
    """Result of content safety check."""
    is_safe: bool
    reason: Optional[str] = None
    categories: dict = None
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = {}


class ContentSafetyFilter:
    """Azure AI Content Safety filter for input validation.
    
    Checks user inputs for harmful content and prompt injection attempts.
    Falls back to basic keyword filtering if Content Safety is not configured.
    """
    
    # Known prompt injection patterns (basic fallback)
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
    
    def __init__(
        self,
        endpoint: str = None,
        api_key: str = None,
    ):
        self.endpoint = endpoint or os.environ.get("CONTENT_SAFETY_ENDPOINT", "")
        self.api_key = api_key or os.environ.get("CONTENT_SAFETY_API_KEY", "")
        self._client = None
        self._enabled = False
    
    async def initialize(self):
        """Initialize the Content Safety client."""
        if not self.endpoint or not self.api_key:
            logger.info("Content Safety not configured - using basic keyword filter")
            return
        
        try:
            from azure.ai.contentsafety.aio import ContentSafetyClient
            from azure.core.credentials import AzureKeyCredential
            
            self._client = ContentSafetyClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key),
            )
            self._enabled = True
            logger.info("✓ Content Safety filter initialized")
            
        except ImportError:
            logger.warning("azure-ai-contentsafety not installed")
            logger.warning("Install with: pip install azure-ai-contentsafety")
        except Exception as e:
            logger.warning(f"Failed to initialize Content Safety: {e}")
    
    async def close(self):
        """Close the client."""
        if self._client:
            await self._client.close()
    
    async def check_input(self, text: str) -> SafetyResult:
        """Check user input for safety issues.
        
        Args:
            text: User input to check
            
        Returns:
            SafetyResult with is_safe flag and details
        """
        # First, check for prompt injection patterns (fast, local)
        injection_result = self._check_injection_patterns(text)
        if not injection_result.is_safe:
            return injection_result
        
        # If Content Safety is enabled, do full check
        if self._enabled and self._client:
            return await self._check_content_safety(text)
        
        # Default: allow if no issues found
        return SafetyResult(is_safe=True)
    
    def _check_injection_patterns(self, text: str) -> SafetyResult:
        """Check for known prompt injection patterns."""
        text_lower = text.lower()
        
        for pattern in self.INJECTION_PATTERNS:
            if pattern in text_lower:
                return SafetyResult(
                    is_safe=False,
                    reason=f"Potential prompt injection detected",
                    categories={"prompt_injection": True},
                )
        
        return SafetyResult(is_safe=True)
    
    async def _check_content_safety(self, text: str) -> SafetyResult:
        """Check content using Azure AI Content Safety API."""
        try:
            from azure.ai.contentsafety.models import AnalyzeTextOptions
            
            request = AnalyzeTextOptions(text=text)
            response = await self._client.analyze_text(request)
            
            # Check category scores (0-6 scale, 2+ is concerning)
            categories = {}
            blocked_categories = []
            
            for category in response.categories_analysis:
                categories[category.category.value] = category.severity
                if category.severity >= 2:  # Medium or higher
                    blocked_categories.append(category.category.value)
            
            if blocked_categories:
                return SafetyResult(
                    is_safe=False,
                    reason=f"Content flagged: {', '.join(blocked_categories)}",
                    categories=categories,
                )
            
            return SafetyResult(is_safe=True, categories=categories)
            
        except Exception as e:
            logger.warning(f"Content Safety check failed: {e}")
            # Fail open - allow if service is down
            return SafetyResult(is_safe=True, reason="Check skipped (service error)")


# Singleton instance
_filter: ContentSafetyFilter = None


async def get_safety_filter() -> ContentSafetyFilter:
    """Get or create the safety filter singleton."""
    global _filter
    if _filter is None:
        _filter = ContentSafetyFilter()
        await _filter.initialize()
    return _filter


async def check_input_safety(text: str) -> SafetyResult:
    """Convenience function to check input safety.
    
    Usage:
        result = await check_input_safety("user message")
        if not result.is_safe:
            return {"error": result.reason}
    """
    filter = await get_safety_filter()
    return await filter.check_input(text)
