"""Test agent routing logic."""

import pytest
from agents.orchestrator import route


class TestRouting:
    """Test message routing to agents."""

    def test_route_search_keywords(self):
        """Search keywords route to search agent."""
        assert route("Find Python developers") == "search"
        assert route("search for candidates") == "search"
        assert route("who has experience in Azure") == "search"
        assert route("look for ML engineers") == "search"

    def test_route_insights_keywords(self):
        """Insights keywords route to insights agent."""
        assert route("What's the interview feedback for John?") == "insights"
        assert route("Show me candidate history") == "insights"
        assert route("How did she score in interviews?") == "insights"

    def test_route_outreach_keywords(self):
        """Outreach keywords route to outreach agent."""
        assert route("Write an email to Sarah") == "outreach"
        assert route("Draft outreach message") == "outreach"
        assert route("contact this candidate") == "outreach"
        assert route("reach out to them") == "outreach"

    def test_route_profile_keywords(self):
        """Profile keywords route to profile agent."""
        assert route("Define job requirements") == "profile"
        assert route("I need to create a role profile") == "profile"
        assert route("We're hiring for a PM position") == "profile"

    def test_route_default_to_orchestrator(self):
        """Unknown messages route to orchestrator."""
        assert route("Hello") == "orchestrator"
        assert route("What can you do?") == "orchestrator"
        assert route("Thanks for your help") == "orchestrator"
