"""
Search tools for the Builder Agent.
"""
import asyncio
from typing import Any, Dict, List
from langchain_core.tools import tool
from motor.motor_asyncio import AsyncIOMotorClient
from services.embeddings.service import embed_text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_client():
    """Create a fresh database client for each request."""
    mongodb_url = os.getenv("MONGODB_URL")
    if not mongodb_url:
        raise ValueError("MONGODB_URL environment variable is required")
    return AsyncIOMotorClient(mongodb_url)

async def _search_async(query: str, collection_name: str, index_name: str, project_fields: Dict[str, Any], k: int = 5) -> Dict[str, Any]:
    """
    Generic vector search function for a given collection.
    """
    client = None
    try:
        if not query:
            return {"success": True, "query": query, "results": [], "count": 0}

        client = get_database_client()
        db = client["proppal"]

        query_vec = embed_text(query)


        pipeline: List[Dict[str, Any]] = [
            {
                "$vectorSearch": {
                    "index": index_name,
                    "path": "embeddings",
                    "queryVector": query_vec,
                    "numCandidates": max(100, k * 10),
                    "limit": k,
                }
            },
            {
                "$project": {
                    "score": {"$meta": "vectorSearchScore"},
                    **project_fields
                }
            },
        ]

        results = await db[collection_name].aggregate(pipeline).to_list(k)

        # Normalize ids for JSON serialization
        for r in results:
            if "_id" in r:
                r["_id"] = str(r["_id"])
            # Some service docs include a foreign key builder_id as ObjectId
            if "builder_id" in r and r["builder_id"] is not None:
                try:
                    r["builder_id"] = str(r["builder_id"])
                except Exception:
                    pass

        # Optional debug output to terminal for service queries
        if collection_name == "builder_services":
            try:
                import json
                print("--- [Builder Search Tool] Services payload ---")
                print(json.dumps({
                    "query": query,
                    "count": len(results),
                    "results": results
                }, ensure_ascii=False, indent=2)[:8000])
            except Exception:
                pass

        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "query": query, "results": [], "count": 0}
    finally:
        if client:
            client.close()

def _run_async_search(search_coro):
    """Helper to run asyncio code from a sync context (safe in running loops)."""
    try:
        asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, search_coro)
            return future.result()
    except RuntimeError:
        return asyncio.run(search_coro)
    except Exception as e:
        return {"success": False, "error": str(e), "results": [], "count": 0}

@tool
def builder_profile_search_tool(query: str) -> Dict[str, Any]:
    """
    Searches for builder profiles based on a natural language query.
    Use this to find builders, construction companies, or contractors.
    
    Args:
        query: The user's search query (e.g., "builders who specialize in residential homes").
    """
    project_fields = {
        "company_name": 1,
        "specialization": 1,
        "experience_years": 1,
        "city": 1,
        "contact_person": 1,
        "contact_email": 1,
        "contact_phone": 1,
    }
    search_coro = _search_async(
        query,
        collection_name="builder_profiles",
        index_name="builder_profile_index",
        project_fields=project_fields,
        k=5
    )
    return _run_async_search(search_coro)

@tool
def builder_service_search_tool(query: str) -> Dict[str, Any]:
    """
    Searches for specific services offered by builders.
    Use this to find services like 'kitchen remodeling', 'roof repair', or 'new home construction'.
    
    Args:
        query: The user's search query for a service (e.g., "who can do plumbing work").
    """
    project_fields = {
        "service_name": 1,
        "description": 1,
        "category": 1,
        "price_range_min": 1,
        "price_range_max": 1,
        "builder_id": 1, # To link back to the builder
    }
    search_coro = _search_async(
        query,
        collection_name="builder_services",
        index_name="builder_service_index",
        project_fields=project_fields,
        k=5
    )
    return _run_async_search(search_coro)
