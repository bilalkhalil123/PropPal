"""
Unit tests for property search tool.
"""
import pytest
from agents.listing.tools.property_search import property_search_tool


class TestPropertySearchTool:
    def test_search_with_filters(self):
        """Test property search with filters applied"""
        query = "Modern apartment in Islamabad under 1 crore"
        result = property_search_tool(query)
        
        assert result["success"] is True
        assert isinstance(result["results"], list)
        assert "filters_applied" in result
        assert result["count"] >= 0
    
    def test_search_returns_top_10(self):
        """Test search returns maximum 10 results"""
        query = "Properties in Lahore"
        result = property_search_tool(query)
        
        assert len(result["results"]) <= 10
    
    def test_search_result_structure(self):
        """Test search result has correct structure"""
        query = "House in Islamabad"
        result = property_search_tool(query)
        
        assert "success" in result
        assert "results" in result
        assert "count" in result
        
        if result["results"]:
            prop = result["results"][0]
            assert "_id" in prop
            assert isinstance(prop["_id"], str)  # ObjectId converted to string
            assert "title" in prop
            assert "price" in prop
            assert "city" in prop
    
    def test_search_empty_query(self):
        """Test search with empty query"""
        query = ""
        result = property_search_tool(query)
        
        assert result["success"] is True
        assert result["count"] == 0
    
    def test_search_no_results(self):
        """Test search that returns no results"""
        query = "Property in NonExistentCity with 100 bedrooms"
        result = property_search_tool(query)
        
        assert result["success"] is True
        assert result["count"] == 0
        assert result["results"] == []

