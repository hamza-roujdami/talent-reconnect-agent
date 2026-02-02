"""Talent Reconnect Agents - Foundry V2 SDK.

Usage:
    from agents import AgentFactory, create_factory
    
    async with create_factory() as factory:
        response = await factory.chat("Find Python developers")
        print(response)
"""

from .factory import (
    AgentFactory,
    Agent,
    Session,
    create_factory,
    quick_chat,
    AGENTS,
)

__all__ = [
    "AgentFactory",
    "Agent", 
    "Session",
    "create_factory",
    "quick_chat",
    "AGENTS",
]
