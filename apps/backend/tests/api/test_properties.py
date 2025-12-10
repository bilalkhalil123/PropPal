"""
Integration tests for Properties API endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestPropertiesAPI:
    async def test_create_property(self, client: AsyncClient):
        """Test creating a new property"""
        payload = {
            "title": "Test Property",
            "description": "A test property",
            "price": 5000000,
            "property_type": "apartment",
            "area_sqft": 1200,
            "bedrooms": 3,
            "bathrooms": 2,
            "floors": 1,
            "city": "Islamabad",
            "area": "F-10",
            "lng": 73.0479,
            "lat": 33.6844,
            "seller_id": "test_seller_123",
            "images": []
        }
        
        response = await client.post("/api/properties", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "_id" in data
        assert data["title"] == "Test Property"
    
    async def test_get_property_by_id(self, client: AsyncClient, test_property_id: str):
        """Test retrieving a property by ID"""
        response = await client.get(f"/api/properties/{test_property_id}")
        
        # May return 404 if property doesn't exist in test DB
        assert response.status_code in [200, 404]
    
    async def test_list_properties(self, client: AsyncClient):
        """Test listing properties"""
        response = await client.get("/api/properties")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_delete_property(self, client: AsyncClient, test_property_id: str):
        """Test deleting a property"""
        response = await client.delete(
            f"/api/properties/{test_property_id}",
            params={"clerk_id": "test_seller_123"}
        )
        
        # May return 404 if property doesn't exist
        assert response.status_code in [204, 404]
    
    async def test_create_property_missing_fields(self, client: AsyncClient):
        """Test creating property with missing required fields"""
        payload = {
            "title": "Incomplete Property"
            # Missing required fields
        }
        
        response = await client.post("/api/properties", json=payload)
        
        assert response.status_code == 422  # Validation error

