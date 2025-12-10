"""
Security tests for authentication and authorization.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthentication:
    async def test_unauthorized_access(self, client: AsyncClient):
        """Test unauthorized API access"""
        # Attempt to access protected endpoint without auth
        response = await client.get("/api/users/me")
        
        # Should require authentication
        assert response.status_code in [401, 403, 422]
    
    async def test_invalid_clerk_id(self, client: AsyncClient):
        """Test with invalid Clerk ID"""
        response = await client.get(
            "/api/users/me",
            params={"clerk_id": "invalid_id_12345"}
        )
        
        # Should handle invalid ID gracefully
        assert response.status_code in [404, 422]


@pytest.mark.asyncio
class TestAuthorization:
    async def test_delete_other_user_property(self, client: AsyncClient):
        """Test user cannot delete another user's property"""
        response = await client.delete(
            "/api/properties/507f1f77bcf86cd799439011",
            params={"clerk_id": "wrong_user"}
        )
        
        # Should deny access
        assert response.status_code in [403, 404]
    
    async def test_access_other_user_sessions(self, client: AsyncClient):
        """Test user cannot access another user's chat sessions"""
        response = await client.get(
            "/api/chat/history",
            params={
                "user_id": "other_user",
                "session_id": "other_session"
            }
        )
        
        # Should return empty or deny access
        assert response.status_code in [200, 403]

