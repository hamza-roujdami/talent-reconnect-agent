"""Observability package for tracing, monitoring, and evaluation.

Uses Azure AI Foundry's native telemetry + Azure Monitor.
"""

from .tracing import setup_telemetry, get_tracer, enable_foundry_tracing, TracingMiddleware

# Evals are in observability.evals subpackage
# from observability.evals import AgentEvaluator

__all__ = [
    "setup_telemetry",
    "get_tracer", 
    "enable_foundry_tracing",
    "TracingMiddleware",
]
