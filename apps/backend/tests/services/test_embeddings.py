"""
Unit tests for embedding generation service.
"""
import pytest
from services.embeddings.service import embed_text, embed_batch


class TestEmbeddingService:
    def test_embed_text_returns_vector(self):
        """Test that embed_text returns a 384-dimensional vector"""
        text = "Modern apartment in Islamabad"
        result = embed_text(text)
        
        assert isinstance(result, list)
        assert len(result) == 384
        assert all(isinstance(x, float) for x in result)
    
    def test_embed_batch_multiple_texts(self):
        """Test batch embedding with multiple texts"""
        texts = [
            "3 bedroom house",
            "Luxury villa",
            "Apartment for rent"
        ]
        results = embed_batch(texts)
        
        assert len(results) == 3
        assert all(len(vec) == 384 for vec in results)
    
    def test_embed_text_empty_string(self):
        """Test embedding empty string"""
        result = embed_text("")
        
        assert isinstance(result, list)
        assert len(result) == 384
    
    def test_embed_batch_empty_list(self):
        """Test batch embedding with empty list"""
        results = embed_batch([])
        
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_embed_text_special_characters(self):
        """Test embedding text with special characters"""
        text = "Property @ $500,000 with 3BR & 2BA!"
        result = embed_text(text)
        
        assert isinstance(result, list)
        assert len(result) == 384

