"""
Pytest configuration and fixtures for PropPal backend tests.
"""
import pytest
import asyncio
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from main import app
from common.config import get_settings

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_db():
    """Create a test database connection."""
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[f"{settings.MONGODB_DB_NAME}_test"]
    yield db
    # Cleanup
    await client.drop_database(f"{settings.MONGODB_DB_NAME}_test")
    client.close()

@pytest.fixture
def test_property_id():
    """Provide a test property ID."""
    return "507f1f77bcf86cd799439011"

@pytest.fixture
def test_user_id():
    """Provide a test user ID."""
    return "test_user_123"

@pytest.fixture
def test_clerk_id():
    """Provide a test Clerk ID."""
    return "user_test_123456"

