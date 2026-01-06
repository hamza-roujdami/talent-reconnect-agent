"""
Integration tests for Azure AI Search providers.

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


class TestSearchProviderCreation:
    """Tests for search provider instantiation."""
    
    def test_build_search_context_provider(self):
        """Should create search context provider from env."""
        from tools.search_provider import build_search_context_provider
        
        provider = build_search_context_provider()
        assert provider is not None
    
    def test_build_resume_search_provider(self):
        """Should create resume search provider from env."""
        from tools.search_provider import build_resume_search_provider
        
        provider = build_resume_search_provider()
        assert provider is not None
    
    def test_build_hybrid_agentic_provider(self):
        """Should create hybrid agentic provider from env."""
        from tools.search_provider import build_hybrid_agentic_provider
        
        provider = build_hybrid_agentic_provider()
        assert provider is not None


class TestFeedbackProviderCreation:
    """Tests for feedback provider instantiation."""
    
    @pytest.mark.skipif(
        not os.getenv("SEARCH_FEEDBACK_INDEX"),
        reason="Feedback index not configured"
    )
    def test_build_feedback_context_provider(self):
        """Should create feedback context provider from env."""
        from tools.feedback_lookup import build_feedback_context_provider
        
        provider = build_feedback_context_provider()
        assert provider is not None


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
    async def test_semantic_search_returns_results(self):
        """Semantic search should return candidate results."""
        from agent_framework import ChatMessage, Role
        from tools.search_provider import build_resume_search_provider
        
        provider = build_resume_search_provider(top_k=3)
        
        # Create a test query message
        messages = [ChatMessage(role=Role.USER, text="Python developer in Dubai")]
        
        context = await provider.invoking(messages)
        
        assert context is not None
        assert context.messages is not None
        assert len(context.messages) > 0
    
    @pytest.mark.integration
    async def test_hybrid_search_includes_real_ids(self):
        """Hybrid search should include real document IDs."""
        from agent_framework import ChatMessage, Role
        from tools.search_provider import build_hybrid_agentic_provider
        
        provider = build_hybrid_agentic_provider(top_k=3)
        
        messages = [ChatMessage(role=Role.USER, text="Data Engineer with Azure experience")]
        
        context = await provider.invoking(messages)
        
        # Should have context with field data
        assert context is not None
        if context.messages:
            all_text = " ".join(m.text or "" for m in context.messages)
            # Should contain structured field data
            assert "id=" in all_text or "email=" in all_text


class TestFeedbackIntegration:
    """Integration tests for feedback lookup."""
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("SEARCH_FEEDBACK_INDEX"),
        reason="Feedback index not configured"
    )
    async def test_feedback_lookup_by_email(self):
        """Should be able to lookup feedback by email."""
        from tools.feedback_lookup import get_feedback_history
        
        # This will return None if no matching candidate
        # but shouldn't raise an error
        result = get_feedback_history("test@example.com")
        
        # Either None or a dict with expected structure
        if result is not None:
            assert "candidate_email" in result
            assert "total_interviews" in result
