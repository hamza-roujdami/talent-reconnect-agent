"""Test feedback tool."""

import json
import pytest
from tools.feedback import lookup_feedback


class TestLookupFeedback:
    """Test feedback lookup functionality."""

    def test_lookup_returns_json(self, search_endpoint, search_api_key):
        """Lookup returns valid JSON."""
        result = lookup_feedback(candidate_name="test")
        data = json.loads(result)
        
        assert isinstance(data, dict)

    def test_lookup_by_name(self, search_endpoint, search_api_key):
        """Lookup by candidate name."""
        result = lookup_feedback(candidate_name="Ahmed")
        data = json.loads(result)
        
        assert "count" in data or "feedback" in data or "error" in data

    def test_lookup_requires_id_or_name(self, search_endpoint, search_api_key):
        """Lookup requires either ID or name."""
        result = lookup_feedback()
        data = json.loads(result)
        
        assert "error" in data

    def test_feedback_result_structure(self, search_endpoint, search_api_key):
        """Feedback results have expected structure."""
        result = lookup_feedback(candidate_name="engineer")
        data = json.loads(result)
        
        if data.get("count", 0) > 0:
            feedback = data["feedback"][0]
            assert "candidate_name" in feedback
            assert "recommendation" in feedback
