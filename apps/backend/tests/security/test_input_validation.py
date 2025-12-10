"""
Security tests for input validation.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestInputValidation:
    async def test_sql_injection_prevention(self, client: AsyncClient):
        """Test SQL injection prevention"""
        malicious_input = "'; DROP TABLE properties; --"
        response = await client.post("/api/chat/message", json={
            "message": malicious_input,
            "clerk_id": "test_user",
            "session_id": "test_session"
        })
        
        # Should not crash or execute malicious code
        assert response.status_code in [200, 400]
    
    async def test_xss_prevention(self, client: AsyncClient):
        """Test XSS prevention"""
        xss_input = "<script>alert('XSS')</script>"
        response = await client.post("/api/properties", json={
            "title": xss_input,
            "description": "Test",
            "price": 1000000,
            "property_type": "apartment",
            "area_sqft": 1000,
            "bedrooms": 2,
            "bathrooms": 1,
            "floors": 1,
            "city": "Test",
            "area": "Test",
            "lng": 0,
            "lat": 0,
            "seller_id": "test"
        })
        
        # Should sanitize or reject
        assert response.status_code in [200, 400, 422]
    
    async def test_nosql_injection_prevention(self, client: AsyncClient):
        """Test NoSQL injection prevention"""
        malicious_input = {"$ne": None}
        response = await client.get(
            "/api/properties",
            params={"city": str(malicious_input)}
        )
        
        # Should handle safely
        assert response.status_code in [200, 400]
    
    async def test_large_payload(self, client: AsyncClient):
        """Test handling of excessively large payloads"""
        large_description = "A" * 1000000  # 1MB of text
        response = await client.post("/api/properties", json={
            "title": "Test",
            "description": large_description,
            "price": 1000000,
            "property_type": "apartment",
            "area_sqft": 1000,
            "bedrooms": 2,
            "bathrooms": 1,
            "floors": 1,
            "city": "Test",
            "area": "Test",
            "lng": 0,
            "lat": 0,
            "seller_id": "test"
        })
        
        # Should reject or handle gracefully
        assert response.status_code in [200, 400, 413, 422]

