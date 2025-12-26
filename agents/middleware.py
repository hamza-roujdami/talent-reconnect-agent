"""
Agent Middleware - Logging, Timing, and Error Handling

Provides middleware for monitoring agent and tool execution:
- LoggingMiddleware: Logs agent runs and tool calls with timing
- ErrorHandlingMiddleware: Graceful error recovery with user-friendly messages
"""
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, AsyncIterable

from agent_framework import (
    AgentMiddleware,
    AgentRunContext,
    FunctionMiddleware,
    FunctionInvocationContext,
    AgentRunResponse,
    AgentRunResponseUpdate,
)

logger = logging.getLogger("talent_reconnect.middleware")


class LoggingAgentMiddleware(AgentMiddleware):
    """Logs agent invocations with timing and message counts."""

    async def process(
        self,
        context: AgentRunContext,
        next: Callable[[AgentRunContext], Awaitable[None]],
    ) -> None:
        agent_name = context.agent.name
        message_count = len(context.messages) if context.messages else 0
        is_streaming = context.is_streaming

        logger.info(
            f"🤖 Agent '{agent_name}' invoked | messages={message_count} | streaming={is_streaming}"
        )
        start_time = time.perf_counter()

        try:
            await next(context)
            elapsed = time.perf_counter() - start_time
            logger.info(f"✅ Agent '{agent_name}' completed | duration={elapsed:.2f}s")
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"❌ Agent '{agent_name}' failed | duration={elapsed:.2f}s | error={e}")
            raise


class LoggingFunctionMiddleware(FunctionMiddleware):
    """Logs function/tool invocations with arguments and timing."""

    async def process(
        self,
        context: FunctionInvocationContext,
        next: Callable[[FunctionInvocationContext], Awaitable[None]],
    ) -> None:
        func_name = context.function.name if context.function else "unknown"
        # Truncate long arguments for readability
        args_preview = str(context.arguments)[:200] if context.arguments else "{}"

        logger.info(f"🔧 Tool '{func_name}' called | args={args_preview}")
        start_time = time.perf_counter()

        try:
            await next(context)
            elapsed = time.perf_counter() - start_time
            result_preview = str(context.result)[:100] if context.result else "None"
            logger.info(f"✅ Tool '{func_name}' completed | duration={elapsed:.2f}s | result={result_preview}...")
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"❌ Tool '{func_name}' failed | duration={elapsed:.2f}s | error={e}")
            raise


class ErrorHandlingFunctionMiddleware(FunctionMiddleware):
    """Catches tool errors and provides graceful fallback responses."""

    async def process(
        self,
        context: FunctionInvocationContext,
        next: Callable[[FunctionInvocationContext], Awaitable[None]],
    ) -> None:
        func_name = context.function.name if context.function else "unknown"

        try:
            await next(context)
        except Exception as e:
            logger.exception(f"Tool '{func_name}' raised an exception")
            # Provide user-friendly error instead of crashing
            context.result = f"⚠️ The {func_name} tool encountered an error: {str(e)[:100]}. Please try again."


# Convenience function-based middleware (alternative style)
async def timing_middleware(
    context: AgentRunContext,
    next: Callable[[AgentRunContext], Awaitable[None]],
) -> None:
    """Simple timing middleware for performance monitoring."""
    start = time.perf_counter()
    await next(context)
    elapsed = time.perf_counter() - start
    # Store in metadata for downstream use
    context.metadata["elapsed_seconds"] = elapsed


# Pre-configured middleware instances for easy import
logging_agent_middleware = LoggingAgentMiddleware()
logging_function_middleware = LoggingFunctionMiddleware()
error_handling_middleware = ErrorHandlingFunctionMiddleware()


def get_default_middleware() -> tuple[list, list]:
    """Return default middleware lists for agents and functions.
    
    Returns:
        Tuple of (agent_middleware_list, function_middleware_list)
    """
    return (
        [logging_agent_middleware],
        [logging_function_middleware, error_handling_middleware],
    )
