"""
Integration tests for Chat API endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestChatAPI:
    async def test_send_message_property_search(self, client: AsyncClient):
        """Test sending a property search message"""
        payload = {
            "message": "Find 3 bedroom apartments in Islamabad",
            "clerk_id": "test_user_123",
            "session_id": "test_session_456"
        }
        
        response = await client.post("/api/chat/message", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["classification"] in ["listing_agent", "builder_agent", "general_chat"]
    
    async def test_send_message_empty(self, client: AsyncClient):
        """Test sending empty message"""
        payload = {
            "message": "",
            "clerk_id": "test_user_123",
            "session_id": "test_session_456"
        }
        
        response = await client.post("/api/chat/message", json=payload)
        
        assert response.status_code == 400
    
    async def test_list_chat_sessions(self, client: AsyncClient):
        """Test listing chat sessions for a user"""
        response = await client.get(
            "/api/chat/sessions",
            params={"user_id": "test_user_123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "count" in data
        assert isinstance(data["sessions"], list)
    
    async def test_delete_chat_session(self, client: AsyncClient):
        """Test deleting a chat session"""
        response = await client.delete(
            "/api/chat/sessions/test_session_456",
            params={"user_id": "test_user_123"}
        )
        
        assert response.status_code == 204
    
    async def test_get_chat_history(self, client: AsyncClient):
        """Test retrieving chat history"""
        response = await client.get(
            "/api/chat/history",
            params={
                "user_id": "test_user_123",
                "session_id": "test_session_456"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)

