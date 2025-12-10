"""
Unit tests for property filter extraction.
"""
import pytest
from agents.listing.tools.filter_extractor import extract_property_filters


class TestFilterExtractor:
    def test_extract_city_filter(self):
        """Test city extraction from query"""
        query = "Find apartments in Islamabad"
        filters = extract_property_filters(query)
        
        assert filters.get("city") == "Islamabad"
        assert filters.get("property_type") == "apartment"
    
    def test_extract_price_range(self):
        """Test price range extraction"""
        query = "House under 1 crore in Lahore"
        filters = extract_property_filters(query)
        
        assert filters.get("city") == "Lahore"
        assert filters.get("price_max") == 10000000
        assert filters.get("property_type") == "house"
    
    def test_extract_bedroom_count(self):
        """Test bedroom count extraction"""
        query = "3 bedroom apartment in Karachi"
        filters = extract_property_filters(query)
        
        assert filters.get("bedrooms_min") == 3
        assert filters.get("bedrooms_max") == 3
        assert filters.get("city") == "Karachi"
    
    def test_no_filters_extracted(self):
        """Test query with no extractable filters"""
        query = "Show me properties"
        filters = extract_property_filters(query)
        
        assert filters == {} or filters is None
    
    def test_extract_price_range_lakh(self):
        """Test price extraction in lakhs"""
        query = "Apartment under 50 lakh"
        filters = extract_property_filters(query)
        
        assert filters.get("price_max") == 5000000
    
    def test_extract_multiple_filters(self):
        """Test extraction of multiple filters"""
        query = "3 bedroom house in Islamabad under 1 crore with 2 bathrooms"
        filters = extract_property_filters(query)
        
        assert filters.get("city") == "Islamabad"
        assert filters.get("bedrooms_min") == 3
        assert filters.get("bathrooms_min") == 2
        assert filters.get("price_max") == 10000000
        assert filters.get("property_type") == "house"

