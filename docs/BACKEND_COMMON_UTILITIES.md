# Backend Common Utilities Implementation

## Overview

This document describes the implementation of common backend utilities for the PropPal FastAPI services. These utilities provide essential functionality for configuration management, database connectivity, and error handling across all backend services.

## 📁 Directory Structure

```
apps/backend/
├── common/
│   ├── __init__.py          # Package exports
│   ├── config.py            # Configuration management using Pydantic Settings
│   ├── db.py                # MongoDB connection wrapper using Motor
│   └── errors.py            # Custom exceptions and error handlers
├── services/
│   └── main.py              # Main FastAPI application (updated)
├── models/                  # Pydantic models
├── requirements.txt         # Updated with motor and pydantic-settings
└── .env                     # Environment variables (not in git)
```

## 🔧 Implementation Details

### 1. Configuration Management (`common/config.py`)

**Purpose**: Centralized configuration using Pydantic BaseSettings with automatic environment variable loading.

**Key Features**:
- ✅ Type-safe configuration with Pydantic validation
- ✅ Automatic `.env` file loading
- ✅ Singleton pattern using `@lru_cache`
- ✅ Support for all required environment variables

**Configuration Fields**:
```python
MONGODB_URL              # MongoDB Atlas connection string
MONGODB_DB_NAME          # Database name (default: "proppal")
SECRET_KEY               # JWT secret key
ALGORITHM                # JWT algorithm (default: "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES  # Token expiration (default: 30)
NLP_SERVICE_URL          # NLP service URL (default: "http://localhost:8001")
ALLOWED_ORIGINS          # CORS origins (default: "http://localhost:3000")
APP_NAME                 # Application name
APP_VERSION              # Application version
DEBUG                    # Debug mode flag
HOST                     # Server host (default: "0.0.0.0")
PORT                     # Server port (default: 8000)
```

**Usage**:
```python
from common.config import get_settings

settings = get_settings()
print(settings.MONGODB_URL)
print(settings.get_allowed_origins_list())
```

### 2. Database Connection (`common/db.py`)

**Purpose**: MongoDB connection management using Motor (async driver) with FastAPI lifespan integration.

**Key Features**:
- ✅ Async MongoDB client using Motor
- ✅ Singleton pattern for client management
- ✅ FastAPI dependency injection support
- ✅ Proper connection lifecycle management

**DatabaseClient Class**:
```python
class DatabaseClient:
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    def get_client(cls) -> AsyncIOMotorClient
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase
```

**FastAPI Dependencies**:
```python
async def get_db_client() -> AsyncIOMotorClient
async def get_database() -> AsyncIOMotorDatabase
```

**Usage in Endpoints**:
```python
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from common.db import get_database

@app.get("/items")
async def get_items(db: AsyncIOMotorDatabase = Depends(get_database)):
    items = await db.items.find().to_list(100)
    return items
```

### 3. Error Handling (`common/errors.py`)

**Purpose**: Consistent error responses across all services with custom exception classes.

**Custom Exception Classes**:

| Exception | HTTP Status | Description |
|-----------|-------------|-------------|
| `PropPalException` | Base class | Base for all custom exceptions |
| `ResourceNotFoundException` | 404 | Resource not found |
| `AuthenticationFailedException` | 401 | Authentication failed |
| `ValidationErrorException` | 422 | Validation error |
| `DatabaseConnectionException` | 503 | Database connection error |
| `UnauthorizedException` | 403 | Insufficient permissions |

**Error Response Format**:
```json
{
    "error": "ResourceNotFound",
    "message": "User with ID 12345 not found",
    "details": {
        "resource_type": "user",
        "resource_id": "12345"
    },
    "path": "http://localhost:8000/api/users/12345"
}
```

**Registration**:
```python
from fastapi import FastAPI
from common.errors import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
```

**Usage in Endpoints**:
```python
from common.errors import ResourceNotFoundException

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise ResourceNotFoundException(
            message=f"User with ID {user_id} not found",
            details={"resource_type": "user", "resource_id": user_id}
        )
    return user
```

### 4. FastAPI Lifespan Integration (`services/main.py`)

**Purpose**: Modern FastAPI lifespan context manager for managing application lifecycle.

**Implementation**:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from common.config import get_settings
from common.db import DatabaseClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    settings = get_settings()
    
    DatabaseClient.client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=5000
    )
    DatabaseClient.database = DatabaseClient.client[settings.MONGODB_DB_NAME]
    
    await DatabaseClient.client.admin.command('ping')
    print(f"✅ Connected to MongoDB: {settings.MONGODB_DB_NAME}")
    
    yield  # Application runs
    
    # SHUTDOWN
    if DatabaseClient.client:
        DatabaseClient.client.close()
        print("📪 MongoDB connection closed")

app = FastAPI(lifespan=lifespan)
```

## 📦 Dependencies

**Updated `requirements.txt`**:
```txt
motor==3.6.0                # Async MongoDB driver
pydantic-settings==2.7.1    # Pydantic settings management
pymongo==4.9.2              # MongoDB driver (motor dependency)
email-validator==2.3.0      # Email validation for Pydantic
fastapi==0.118.0
uvicorn==0.37.0
python-dotenv==1.1.1
```

**Installation**:
```bash
cd apps/backend
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## 🧪 Testing

### Test Endpoints

The implementation includes test endpoints to verify functionality:

#### 1. Health Check
```bash
curl http://localhost:8000/
```
**Response**:
```json
{
    "status": "ok",
    "service": "PropPal API",
    "version": "1.0.0",
    "timestamp": "2025-10-10T10:08:42.734456"
}
```

#### 2. Database Health Check
```bash
curl http://localhost:8000/health/database
```
**Response**:
```json
{
    "status": "ok",
    "connected": true,
    "database": "proppal",
    "mongodb_version": "8.0.14",
    "collections_count": 0,
    "collections": [],
    "timestamp": "2025-10-10T10:08:50.011976"
}
```

#### 3. Test Document Insert
```bash
curl -X POST http://localhost:8000/test/insert
```
**Response**:
```json
{
    "status": "success",
    "message": "Test document inserted successfully",
    "inserted_id": "68e8db406b8071e0489bb7ee",
    "timestamp": "2025-10-10T10:09:04.559563"
}
```

#### 4. Test Document Retrieval
```bash
curl http://localhost:8000/test/documents
```
**Response**:
```json
{
    "status": "success",
    "count": 1,
    "documents": [
        {
            "_id": "68e8db406b8071e0489bb7ee",
            "message": "Test document from PropPal Gateway",
            "timestamp": "2025-10-10T10:09:04.364000",
            "type": "test",
            "service": "gateway"
        }
    ],
    "timestamp": "2025-10-10T10:09:10.531828"
}
```

#### 5. Test Custom Error Handling
```bash
curl http://localhost:8000/test/demo-error
```
**Response** (404):
```json
{
    "error": "ResourceNotFound",
    "message": "This is a demo error to test custom exception handling",
    "details": {
        "resource_type": "demo",
        "resource_id": "12345"
    },
    "path": "http://localhost:8000/test/demo-error"
}
```

## 🚀 Running the Server

### Development Mode
```bash
cd apps/backend
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
python services/main.py
```

### Production Mode
```bash
cd apps/backend
source venv/bin/activate
uvicorn services.main:app --host 0.0.0.0 --port 8000
```

### Using Docker
```bash
# From project root
npm run docker:up
```

## 🔐 Environment Variables

Create a `.env` file in `apps/backend/`:

```env
# MongoDB Configuration
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=proppal

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Services
NLP_SERVICE_URL=http://localhost:8001

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# Application
APP_NAME=PropPal API
APP_VERSION=1.0.0
DEBUG=False

# Server
HOST=0.0.0.0
PORT=8000
```

## ✅ Implementation Checklist

- [x] Create `common/` directory structure
- [x] Implement `config.py` with Pydantic BaseSettings
  - [x] All required fields defined
  - [x] Singleton pattern with `@lru_cache`
  - [x] `.env` file loading configured
- [x] Implement `db.py` with Motor
  - [x] DatabaseClient singleton class
  - [x] FastAPI dependency functions
  - [x] Proper error handling
- [x] Implement `errors.py`
  - [x] Custom exception classes
  - [x] FastAPI exception handlers
  - [x] Registration function
- [x] Update `services/main.py`
  - [x] Lifespan context manager
  - [x] Apply common utilities
  - [x] Register exception handlers
- [x] Update `requirements.txt`
  - [x] Add motor
  - [x] Add pydantic-settings
- [x] Test all endpoints
  - [x] Health check
  - [x] Database health
  - [x] Document operations
  - [x] Error handling

## 📚 Usage Examples

### Creating a New Endpoint with Dependencies

```python
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from common.db import get_database
from common.errors import ResourceNotFoundException

@app.get("/properties/{property_id}")
async def get_property(
    property_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    property_doc = await db.properties.find_one({"_id": property_id})
    
    if not property_doc:
        raise ResourceNotFoundException(
            message=f"Property {property_id} not found",
            details={"resource_type": "property", "resource_id": property_id}
        )
    
    return property_doc
```

### Using Configuration in Services

```python
from common.config import get_settings

settings = get_settings()

@app.get("/config")
async def get_config():
    return {
        "nlp_service": settings.NLP_SERVICE_URL,
        "debug": settings.DEBUG,
        "app_version": settings.APP_VERSION
    }
```

### Custom Error Handling

```python
from common.errors import ValidationErrorException

@app.post("/properties")
async def create_property(data: dict):
    if not data.get("title"):
        raise ValidationErrorException(
            message="Property title is required",
            details={"field": "title", "value": None}
        )
    
    # Process property creation
    ...
```

## 🔄 Next Steps

1. **Agent Implementation**: Use these utilities in the agent services (Listing, Builder, etc.)
2. **Authentication**: Implement JWT authentication using the SECRET_KEY from config
3. **NLP Integration**: Connect to the NLP service using the configured URL
4. **API Documentation**: Expand FastAPI automatic docs with examples
5. **Monitoring**: Add logging and monitoring using the common utilities

## 🐛 Troubleshooting

### Issue: Database Connection Failed
**Solution**: Check your `MONGODB_URL` in `.env` and ensure MongoDB Atlas allows connections from your IP.

### Issue: Import Errors
**Solution**: Ensure you're running from the correct directory and the virtual environment is activated.

### Issue: Type Errors
**Solution**: Ensure all dependencies are installed correctly with `pip install -r requirements.txt`.

---

**Implementation Complete** ✅

All common backend utilities are now implemented and tested. The backend is ready for agent logic development.

