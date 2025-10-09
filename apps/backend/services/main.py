from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv
from datetime import datetime
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# MongoDB Connection
MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "proppal")

# Global MongoDB client (will be initialized on startup)
mongo_client = None
db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI application.
    Handles startup and shutdown events.
    """
    global mongo_client, db
    
    # Startup: Initialize MongoDB connection
    if not MONGODB_URL:
        print("⚠️  WARNING: MONGODB_URL not set in environment variables")
    else:
        try:
            mongo_client = MongoClient(
                MONGODB_URL,
                server_api=ServerApi('1'),
                serverSelectionTimeoutMS=5000
            )
            # Test the connection
            mongo_client.admin.command('ping')
            db = mongo_client[MONGODB_DB_NAME]
            print(f"✅ Successfully connected to MongoDB database: {MONGODB_DB_NAME}")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            mongo_client = None
            db = None
    
    yield  # Application runs here
    
    # Shutdown: Close MongoDB connection
    if mongo_client:
        mongo_client.close()
        print("📪 MongoDB connection closed")


app = FastAPI(
    title="PropPal API Gateway",
    description="Multi-Agent AI-Powered Real Estate Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    """Basic health check endpoint"""
    return {
        "status": "ok",
        "service": "PropPal Gateway",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health/database")
def database_health_check():
    """Check MongoDB database connection status"""
    if not MONGODB_URL:
        return {
            "status": "error",
            "message": "MONGODB_URL not configured",
            "connected": False
        }
    
    if mongo_client is None or db is None:
        return {
            "status": "error",
            "message": "Database client not initialized",
            "connected": False
        }
    
    try:
        # Ping the database
        mongo_client.admin.command('ping')
        
        # Get server info
        server_info = mongo_client.server_info()
        
        # Count collections
        collection_count = len(db.list_collection_names())
        
        return {
            "status": "ok",
            "connected": True,
            "database": MONGODB_DB_NAME,
            "mongodb_version": server_info.get("version", "unknown"),
            "collections_count": collection_count,
            "collections": db.list_collection_names(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "connected": False,
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/test/insert")
def test_database_insert():
    """Test endpoint to insert a sample document"""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    try:
        test_collection = db["test_collection"]
        
        # Insert a test document
        test_doc = {
            "message": "Test document from PropPal",
            "timestamp": datetime.utcnow(),
            "type": "test"
        }
        
        result = test_collection.insert_one(test_doc)
        
        return {
            "status": "success",
            "message": "Test document inserted successfully",
            "inserted_id": str(result.inserted_id),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insert failed: {str(e)}")


@app.get("/test/documents")
def test_get_documents():
    """Test endpoint to retrieve documents from test collection"""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    try:
        test_collection = db["test_collection"]
        
        # Get all documents from test collection
        documents = list(test_collection.find().limit(10))
        
        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            doc["_id"] = str(doc["_id"])
            if "timestamp" in doc:
                doc["timestamp"] = doc["timestamp"].isoformat()
        
        return {
            "status": "success",
            "count": len(documents),
            "documents": documents,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.post("/chat")
def chat(query: dict):
    """Chat endpoint (placeholder for future NLP integration)"""
    return {
        "answer": f"You said: {query.get('query', 'nothing')}",
        "timestamp": datetime.utcnow().isoformat()
    }
