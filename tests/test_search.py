"""
Integration tests for Azure AI Search tools.

Run with: pytest tests/test_search.py -v

Note: These tests require Azure AI Search to be configured.
Skip with: pytest tests/test_search.py -v -k "not integration"
"""
import os
import pytest

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not os.getenv("SEARCH_SERVICE_ENDPOINT"),
        reason="Azure AI Search not configured"
    ),
]


class TestCandidateSearch:
    """Tests for candidate search tool."""
    
    def test_search_candidates_returns_table(self):
        """Should return markdown table of candidates."""
        from tools.candidate_search import search_candidates
        
        result = search_candidates("Python developer in Dubai", top_k=3)
        assert result is not None
        assert "|" in result  # Contains table
    
    def test_search_candidates_handles_no_results(self):
        """Should handle queries with no matches gracefully."""
        from tools.candidate_search import search_candidates
        
        # Very specific query unlikely to match
        result = search_candidates("xyz123nonexistent skill never match", top_k=3)
        assert result is not None
        # Should return either empty table or "no candidates" message


class TestSearchConfiguration:
    """Tests for search configuration validation."""
    
    def test_endpoint_configured(self):
        """Search endpoint should be configured."""
        endpoint = os.getenv("SEARCH_SERVICE_ENDPOINT") or os.getenv("AZURE_SEARCH_ENDPOINT")
        assert endpoint is not None
        assert endpoint.startswith("https://")
    
    def test_index_configured(self):
        """Resume index should be configured."""
        index = (
            os.getenv("SEARCH_RESUME_INDEX") or 
            os.getenv("AZURE_SEARCH_INDEX_NAME") or
            os.getenv("AZURE_SEARCH_INDEX")
        )
        assert index is not None


class TestSearchIntegration:
    """Integration tests that hit Azure AI Search."""
    
    @pytest.mark.integration
    def test_search_candidates_returns_real_data(self):
        """Search should return real candidate data."""
        from tools.candidate_search import search_candidates
        
        result = search_candidates("Data Engineer Dubai", top_k=5)
        
        assert result is not None
        # Should contain real email domains
        assert "@gmail.com" in result or "@outlook.com" in result or "@yahoo.com" in result


class TestFeedbackIntegration:
    """Integration tests for feedback lookup."""
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("SEARCH_FEEDBACK_INDEX"),
        reason="Feedback index not configured"
    )
    def test_feedback_lookup_by_email(self):
        """Should be able to lookup feedback by email."""
        from tools.feedback_lookup import get_feedback_history
        
        # This will return None if no matching candidate
        # but shouldn't raise an error
        result = get_feedback_history("test@example.com")
        
        # Either None or a dict with expected structure
        if result is not None:
            assert "candidate_email" in result
            assert "total_interviews" in result
