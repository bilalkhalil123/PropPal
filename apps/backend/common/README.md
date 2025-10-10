# Common Backend Utilities - Quick Reference

## 🎯 Purpose

Shared utilities for PropPal backend services providing:
- **Configuration Management** - Type-safe environment variable handling
- **Database Connectivity** - Async MongoDB operations with Motor
- **Error Handling** - Standardized error responses

## 📦 Modules

### `config.py` - Configuration Management

```python
from common.config import get_settings

settings = get_settings()

# Access configuration
db_url = settings.MONGODB_URL
db_name = settings.MONGODB_DB_NAME
origins = settings.get_allowed_origins_list()
```

**Available Settings**:
- `MONGODB_URL` - MongoDB Atlas connection string
- `MONGODB_DB_NAME` - Database name
- `SECRET_KEY` - JWT secret
- `NLP_SERVICE_URL` - NLP service endpoint
- `ALLOWED_ORIGINS` - CORS origins
- `DEBUG` - Debug mode flag
- And more...

### `db.py` - Database Connection

```python
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from common.db import get_database

@app.get("/items")
async def get_items(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Dependency injection of database"""
    items = await db.items.find().to_list(100)
    return items
```

**Key Functions**:
- `get_db_client()` - Returns AsyncIOMotorClient
- `get_database()` - Returns AsyncIOMotorDatabase

### `errors.py` - Error Handling

```python
from common.errors import ResourceNotFoundException, register_exception_handlers

# Register handlers in app initialization
app = FastAPI()
register_exception_handlers(app)

# Use in endpoints
@app.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise ResourceNotFoundException(
            message=f"User {user_id} not found",
            details={"resource_type": "user", "user_id": user_id}
        )
    return user
```

**Available Exceptions**:
- `ResourceNotFoundException` (404)
- `AuthenticationFailedException` (401)
- `ValidationErrorException` (422)
- `DatabaseConnectionException` (503)
- `UnauthorizedException` (403)

## 🚀 Quick Start

### 1. Setup Application with Lifespan

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from common.config import get_settings
from common.db import DatabaseClient
from common.errors import register_exception_handlers

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    DatabaseClient.client = AsyncIOMotorClient(settings.MONGODB_URL)
    DatabaseClient.database = DatabaseClient.client[settings.MONGODB_DB_NAME]
    await DatabaseClient.client.admin.command('ping')
    
    yield  # App runs
    
    # Shutdown
    DatabaseClient.client.close()

app = FastAPI(lifespan=lifespan)
register_exception_handlers(app)
```

### 2. Create Endpoint with Dependencies

```python
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from common.db import get_database
from common.errors import ResourceNotFoundException

@app.get("/properties/{id}")
async def get_property(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    prop = await db.properties.find_one({"_id": id})
    if not prop:
        raise ResourceNotFoundException(
            message=f"Property {id} not found",
            details={"property_id": id}
        )
    return prop
```

### 3. Environment Configuration

Create `.env` in `apps/backend/`:
```env
MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DB_NAME=proppal
SECRET_KEY=your-secret-key
NLP_SERVICE_URL=http://localhost:8001
ALLOWED_ORIGINS=http://localhost:3000
DEBUG=False
```

## 🔍 Common Patterns

### Database Query with Error Handling
```python
from common.db import get_database
from common.errors import DatabaseConnectionException

@app.get("/items")
async def list_items(db = Depends(get_database)):
    try:
        items = await db.items.find().to_list(100)
        return {"items": items, "count": len(items)}
    except Exception as e:
        raise DatabaseConnectionException(
            message="Failed to fetch items",
            details={"error": str(e)}
        )
```

### Using Configuration
```python
from common.config import get_settings

@app.post("/chat")
async def chat(query: str):
    settings = get_settings()
    # Use NLP service URL from config
    response = await call_nlp_service(
        settings.NLP_SERVICE_URL,
        query
    )
    return response
```

### Custom Validation Error
```python
from common.errors import ValidationErrorException

@app.post("/users")
async def create_user(data: dict):
    if not data.get("email"):
        raise ValidationErrorException(
            message="Email is required",
            details={"field": "email"}
        )
    # Process user creation
    ...
```

## 📝 Best Practices

1. **Always use dependency injection** for database access
2. **Use custom exceptions** for domain errors (not HTTPException)
3. **Access config through `get_settings()`** (singleton)
4. **Initialize database in lifespan context** manager
5. **Register exception handlers** on app initialization

## 🧪 Testing

Test endpoints are available in `services/main.py`:
- `GET /` - Health check
- `GET /health/database` - Database status
- `POST /test/insert` - Insert test document
- `GET /test/documents` - Fetch test documents
- `GET /test/demo-error` - Test error handling

## 📚 Additional Resources

- Full documentation: `../../BACKEND_COMMON_UTILITIES.md`
- FastAPI docs: https://fastapi.tiangolo.com
- Motor docs: https://motor.readthedocs.io
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

