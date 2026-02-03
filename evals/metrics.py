"""Evaluation metrics for agent responses.

These are fallback heuristic metrics used when Foundry evaluators
are not available. For production, use the Foundry GPT-based evaluators.
"""

import re
from typing import Optional


def relevance_score(query: str, response: str) -> float:
    """Score how relevant the response is to the query.
    
    Checks if query terms appear in the response.
    Scale: 0-5 (5 = highly relevant)
    """
    # Extract meaningful words (skip common words)
    stop_words = {"a", "an", "the", "is", "are", "in", "on", "for", "to", "of", "and", "or", "with"}
    
    query_terms = {
        w.lower() for w in re.findall(r'\b\w+\b', query)
        if w.lower() not in stop_words and len(w) > 2
    }
    
    if not query_terms:
        return 3.0  # Neutral if no meaningful terms
    
    response_lower = response.lower()
    matches = sum(1 for term in query_terms if term in response_lower)
    
    # Scale to 0-5
    ratio = matches / len(query_terms)
    return min(5.0, ratio * 5)


def groundedness_score(response: str, context: Optional[str] = None) -> float:
    """Score how grounded the response is in the provided context.
    
    Checks if response claims are supported by context.
    Scale: 0-5 (5 = fully grounded)
    """
    if not context:
        return 3.0  # Neutral if no context provided
    
    # Extract key phrases from response
    response_phrases = set(re.findall(r'\b\w{4,}\b', response.lower()))
    context_lower = context.lower()
    
    if not response_phrases:
        return 3.0
    
    grounded = sum(1 for phrase in response_phrases if phrase in context_lower)
    ratio = grounded / len(response_phrases)
    
    return min(5.0, ratio * 5)


def coherence_score(response: str) -> float:
    """Score the coherence and structure of the response.
    
    Checks for logical structure, formatting, and organization.
    Scale: 0-5 (5 = highly coherent)
    """
    score = 2.0  # Base score
    
    # Bonus for structured content
    if any(marker in response for marker in ["\n", ":", "-", "•"]):
        score += 1.0
    
    # Bonus for numbered lists
    if re.search(r'\d+\.', response):
        score += 0.5
    
    # Bonus for paragraph structure
    if response.count(". ") >= 2:
        score += 0.5
    
    # Bonus for headers
    if re.search(r'\*\*[^*]+\*\*', response) or re.search(r'^#+\s', response, re.MULTILINE):
        score += 0.5
    
    # Penalty for very short responses
    if len(response) < 50:
        score -= 1.0
    
    # Penalty for overly long responses without structure
    if len(response) > 1000 and "\n" not in response:
        score -= 1.0
    
    return max(0.0, min(5.0, score))


def fluency_score(response: str) -> float:
    """Score the fluency and readability of the response.
    
    Checks for proper sentence structure and flow.
    Scale: 0-5 (5 = highly fluent)
    """
    score = 3.0  # Base score
    
    # Count sentences
    sentences = re.split(r'[.!?]+', response)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return 2.0
    
    # Check sentence length distribution
    avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
    
    # Ideal sentence length: 10-25 words
    if 10 <= avg_length <= 25:
        score += 1.0
    elif avg_length < 5 or avg_length > 40:
        score -= 1.0
    
    # Check for common fluency issues
    issues = 0
    
    # Repeated words
    words = response.lower().split()
    for i in range(len(words) - 1):
        if words[i] == words[i + 1] and words[i] not in {"the", "a", "and"}:
            issues += 1
    
    # Missing capitalization at sentence start
    for sentence in sentences:
        if sentence and not sentence[0].isupper():
            issues += 1
    
    score -= min(2.0, issues * 0.3)
    
    return max(0.0, min(5.0, score))


def overall_score(
    query: str,
    response: str,
    context: Optional[str] = None,
    weights: dict = None,
) -> dict:
    """Calculate all scores and weighted overall score.
    
    Args:
        query: User query
        response: Agent response
        context: Optional grounding context
        weights: Optional custom weights for each metric
        
    Returns:
        Dict with individual scores and weighted overall
    """
    if weights is None:
        weights = {
            "relevance": 0.3,
            "groundedness": 0.25,
            "coherence": 0.25,
            "fluency": 0.2,
        }
    
    scores = {
        "relevance": relevance_score(query, response),
        "groundedness": groundedness_score(response, context),
        "coherence": coherence_score(response),
        "fluency": fluency_score(response),
    }
    
    weighted = sum(scores[k] * weights.get(k, 0.25) for k in scores)
    scores["overall"] = weighted
    
    return scores
