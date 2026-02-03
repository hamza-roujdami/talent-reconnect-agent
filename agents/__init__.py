"""Talent Reconnect Agents - 6-agent recruiting system.

- Orchestrator: routes to specialized agents, handles greetings, rejects off-topic
- RoleCrafter: builds job profiles before search
- TalentScout: finds candidates (resumes index)
- InsightPulse: interview history (feedback index)
- ConnectPilot: sends emails
- MarketRadar: web research (optional)

Usage:
    from agents import AgentFactory
    
    async with AgentFactory() as factory:
        agent_key, response = await factory.orchestrate("Hi")
        if response:
            print(response)
        else:
            print(await factory.chat("Hi", agent_key))
"""

from .factory import AgentFactory, Agent

__all__ = ["AgentFactory", "Agent"]
