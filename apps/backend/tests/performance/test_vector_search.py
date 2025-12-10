"""
Performance tests for vector search operations.
"""
import pytest
import time
import concurrent.futures
from agents.listing.tools.property_search import property_search_tool


class TestVectorSearchPerformance:
    def test_search_latency(self, benchmark):
        """Benchmark search latency"""
        def search():
            return property_search_tool("Modern apartment in Islamabad")
        
        result = benchmark(search)
        
        assert result["success"] is True
        # Mean should be less than 2 seconds
        assert benchmark.stats["mean"] < 2.0
    
    def test_concurrent_searches(self):
        """Test concurrent search performance"""
        queries = [
            "Apartment in Islamabad",
            "House in Lahore",
            "Villa in Karachi",
            "Plot in Rawalpindi"
        ] * 10  # 40 concurrent searches
        
        start = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(property_search_tool, queries))
        
        duration = time.time() - start
        
        assert all(r["success"] for r in results)
        # All searches should complete in 30 seconds
        assert duration < 30
    
    def test_embedding_generation_speed(self):
        """Test embedding generation performance"""
        from services.embeddings.service import embed_text
        
        start = time.time()
        embed_text("Test property description")
        duration = time.time() - start
        
        # Should complete in less than 100ms
        assert duration < 0.1

