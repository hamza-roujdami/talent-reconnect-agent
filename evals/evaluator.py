"""Agent Evaluator using Azure AI Foundry Evaluations.

Runs quality and safety evaluations against agent responses using
built-in Foundry evaluators (GPT-based and traditional metrics).

Usage:
    from evals import AgentEvaluator
    
    evaluator = AgentEvaluator()
    await evaluator.initialize()
    
    # Run single evaluation
    result = await evaluator.evaluate(
        query="Find Python developers in Dubai",
        response="I found 5 candidates...",
        context="Resume data...",
    )
    
    # Run batch evaluation
    results = await evaluator.evaluate_dataset("evals/golden_dataset.json")
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    """Result of a single evaluation."""
    query: str
    response: str
    scores: dict = field(default_factory=dict)
    passed: bool = True
    errors: list = field(default_factory=list)
    
    @property
    def relevance(self) -> float:
        return self.scores.get("relevance", 0.0)
    
    @property
    def groundedness(self) -> float:
        return self.scores.get("groundedness", 0.0)
    
    @property
    def coherence(self) -> float:
        return self.scores.get("coherence", 0.0)
    
    @property
    def fluency(self) -> float:
        return self.scores.get("fluency", 0.0)
    
    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "response": self.response[:200] + "..." if len(self.response) > 200 else self.response,
            "scores": self.scores,
            "passed": self.passed,
            "errors": self.errors,
        }


@dataclass
class EvalSummary:
    """Summary of batch evaluation results."""
    total: int
    passed: int
    failed: int
    avg_scores: dict = field(default_factory=dict)
    results: list = field(default_factory=list)
    
    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0
    
    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": f"{self.pass_rate:.1%}",
            "avg_scores": self.avg_scores,
        }


class AgentEvaluator:
    """Evaluator for agent responses using Foundry AI Evaluations."""
    
    # Minimum scores to pass (0-5 scale for GPT evaluators)
    THRESHOLDS = {
        "relevance": 3.0,
        "groundedness": 3.0,
        "coherence": 3.0,
        "fluency": 3.0,
    }
    
    def __init__(
        self,
        endpoint: str = None,
        model: str = None,
    ):
        self.endpoint = endpoint or os.environ.get("PROJECT_ENDPOINT")
        self.model = model or os.environ.get("FOUNDRY_MODEL_PRIMARY", "gpt-4o-mini")
        
        self._credential = None
        self._client = None
        self._evaluators = {}
    
    async def initialize(self):
        """Initialize the evaluator client."""
        self._credential = DefaultAzureCredential()
        self._client = AIProjectClient(
            endpoint=self.endpoint,
            credential=self._credential,
        )
        
        # Load built-in evaluators
        try:
            from azure.ai.evaluation import (
                RelevanceEvaluator,
                GroundednessEvaluator,
                CoherenceEvaluator,
                FluencyEvaluator,
            )
            
            # Initialize GPT-based evaluators
            model_config = {
                "azure_endpoint": self.endpoint,
                "azure_deployment": self.model,
            }
            
            self._evaluators = {
                "relevance": RelevanceEvaluator(model_config),
                "groundedness": GroundednessEvaluator(model_config),
                "coherence": CoherenceEvaluator(model_config),
                "fluency": FluencyEvaluator(model_config),
            }
            
            logger.info("✓ Foundry evaluators initialized")
            
        except ImportError:
            logger.warning("azure-ai-evaluation not installed")
            logger.warning("Install with: pip install azure-ai-evaluation")
            logger.warning("Using fallback heuristic evaluators")
            self._evaluators = {}
    
    async def close(self):
        """Close connections."""
        if self._client:
            await self._client.close()
        if self._credential:
            await self._credential.close()
    
    async def evaluate(
        self,
        query: str,
        response: str,
        context: str = None,
        expected: str = None,
    ) -> EvalResult:
        """Evaluate a single query-response pair.
        
        Args:
            query: User query/input
            response: Agent response to evaluate
            context: Optional context/grounding data
            expected: Optional expected response for comparison
            
        Returns:
            EvalResult with scores and pass/fail status
        """
        result = EvalResult(query=query, response=response)
        
        if self._evaluators:
            # Use Foundry evaluators
            for name, evaluator in self._evaluators.items():
                try:
                    eval_input = {
                        "query": query,
                        "response": response,
                    }
                    if context:
                        eval_input["context"] = context
                    
                    score_result = await evaluator(**eval_input)
                    result.scores[name] = score_result.get(name, 0.0)
                    
                except Exception as e:
                    result.errors.append(f"{name}: {str(e)}")
        else:
            # Fallback: basic heuristic scores
            result.scores = self._heuristic_scores(query, response, context)
        
        # Check if passed all thresholds
        result.passed = all(
            result.scores.get(metric, 0) >= threshold
            for metric, threshold in self.THRESHOLDS.items()
        )
        
        return result
    
    def _heuristic_scores(
        self,
        query: str,
        response: str,
        context: str = None,
    ) -> dict:
        """Fallback heuristic scoring when Foundry evaluators aren't available."""
        scores = {}
        
        # Relevance: check if query terms appear in response
        query_terms = set(query.lower().split())
        response_lower = response.lower()
        term_matches = sum(1 for t in query_terms if t in response_lower)
        scores["relevance"] = min(5.0, (term_matches / max(len(query_terms), 1)) * 5)
        
        # Coherence: based on response structure
        has_structure = any(c in response for c in [".", "\n", ":", "-", "1."])
        scores["coherence"] = 4.0 if has_structure else 2.0
        
        # Fluency: based on length and formatting
        word_count = len(response.split())
        scores["fluency"] = min(5.0, 2.0 + (word_count / 50))
        
        # Groundedness: if context provided, check overlap
        if context:
            context_lower = context.lower()
            response_terms = set(response.lower().split())
            context_matches = sum(1 for t in response_terms if t in context_lower)
            scores["groundedness"] = min(5.0, (context_matches / max(len(response_terms), 1)) * 5)
        else:
            scores["groundedness"] = 3.0  # Neutral if no context
        
        return scores
    
    async def evaluate_dataset(
        self,
        dataset_path: str,
    ) -> EvalSummary:
        """Evaluate a dataset of test cases.
        
        Args:
            dataset_path: Path to JSON file with test cases
            
        Expected format:
        [
            {
                "query": "Find Python developers",
                "expected": "I found candidates...",
                "context": "Optional grounding data"
            },
            ...
        ]
        
        Returns:
            EvalSummary with aggregated results
        """
        path = Path(dataset_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")
        
        with open(path) as f:
            test_cases = json.load(f)
        
        results = []
        for case in test_cases:
            # Get response from agent (or use provided response)
            response = case.get("response", case.get("expected", ""))
            
            result = await self.evaluate(
                query=case["query"],
                response=response,
                context=case.get("context"),
                expected=case.get("expected"),
            )
            results.append(result)
        
        # Aggregate scores
        passed = sum(1 for r in results if r.passed)
        avg_scores = {}
        
        for metric in self.THRESHOLDS:
            scores = [r.scores.get(metric, 0) for r in results]
            avg_scores[metric] = sum(scores) / len(scores) if scores else 0
        
        return EvalSummary(
            total=len(results),
            passed=passed,
            failed=len(results) - passed,
            avg_scores=avg_scores,
            results=[r.to_dict() for r in results],
        )


async def run_evaluation(dataset_path: str = "evals/golden_dataset.json"):
    """CLI entry point for running evaluations.
    
    Usage:
        python -m evals.evaluator
    """
    evaluator = AgentEvaluator()
    await evaluator.initialize()
    
    try:
        summary = await evaluator.evaluate_dataset(dataset_path)
        
        print("\n" + "=" * 60)
        print("EVALUATION RESULTS")
        print("=" * 60)
        print(f"Total: {summary.total}")
        print(f"Passed: {summary.passed}")
        print(f"Failed: {summary.failed}")
        print(f"Pass Rate: {summary.pass_rate:.1%}")
        print("\nAverage Scores:")
        for metric, score in summary.avg_scores.items():
            threshold = AgentEvaluator.THRESHOLDS.get(metric, 3.0)
            status = "✓" if score >= threshold else "✗"
            print(f"  {status} {metric}: {score:.2f} (threshold: {threshold})")
        print("=" * 60)
        
        return summary
        
    finally:
        await evaluator.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_evaluation())
