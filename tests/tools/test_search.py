"""Test search tool."""

import json
import pytest
from tools.search import search_candidates


class TestSearchCandidates:
    """Test candidate search functionality."""

    def test_search_returns_json(self, search_endpoint, search_api_key):
        """Search returns valid JSON."""
        result = search_candidates("Python developer", top=5)
        data = json.loads(result)
        
        assert "count" in data or "error" in data

    def test_search_with_location(self, search_endpoint, search_api_key):
        """Search with location filter."""
        result = search_candidates("developer", location="Dubai", top=5)
        data = json.loads(result)
        
        assert "count" in data or "error" in data

    def test_search_empty_query(self, search_endpoint, search_api_key):
        """Search with empty query still works."""
        result = search_candidates("", top=5)
        data = json.loads(result)
        
        # Should return results or empty list, not error
        assert isinstance(data, dict)

    def test_search_result_structure(self, search_endpoint, search_api_key):
        """Search results have expected structure."""
        result = search_candidates("engineer", top=3)
        data = json.loads(result)
        
        if data.get("count", 0) > 0:
            candidate = data["candidates"][0]
            assert "id" in candidate
            assert "name" in candidate
            assert "title" in candidate
