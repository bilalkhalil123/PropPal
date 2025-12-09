"""
Search tools for the Builder Agent.
"""
import asyncio
from typing import Any, Dict, List, Optional
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

async def _search_async(
    query: str,
    collection_name: str,
    index_name: str,
    project_fields: Dict[str, Any],
    k: int = 5,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generic vector search function using Qdrant for builder profiles and services.
    """
    client = None
    try:
        if not query:
            return {"success": True, "query": query, "results": [], "count": 0}

        from bson import ObjectId
        from services.vector_search.qdrant_service import (
            search_builder_profiles,
            search_builder_services,
        )

        query_vec = embed_text(query)

        # Determine which Qdrant collection to search
        if collection_name == "builder_profiles":
            qdrant_results = await search_builder_profiles(
                query_vector=query_vec,
                limit=k,
                filters=None,
            )
        elif collection_name == "builder_services":
            qdrant_results = await search_builder_services(
                query_vector=query_vec,
                limit=k,
                filters=None,
            )
        else:
            return {"success": False, "error": f"Unknown collection: {collection_name}", "query": query, "results": [], "count": 0}

        if not qdrant_results:
            return {"success": True, "query": query, "results": [], "count": 0}

        # Get database client and database
        client = get_database_client()
        db = client["proppal"]

        # Fetch full documents from MongoDB using the IDs from Qdrant
        doc_ids = [ObjectId(result["id"]) for result in qdrant_results]
        
        # Fetch documents from MongoDB
        cursor = db[collection_name].find(
            {"_id": {"$in": doc_ids}},
            project_fields
        )
        
        docs = await cursor.to_list(length=k)
        
        # Create a map of _id to score for ordering
        score_map = {result["id"]: result["score"] for result in qdrant_results}
        
        # Sort results by Qdrant score and add score to results
        results = []
        for doc in docs:
            doc_id_str = str(doc["_id"])
            if doc_id_str in score_map:
                doc["_id"] = doc_id_str
                doc["score"] = score_map[doc_id_str]
                # Some service docs include a foreign key builder_id as ObjectId
                if "builder_id" in doc and doc["builder_id"] is not None:
                    try:
                        doc["builder_id"] = str(doc["builder_id"])
                    except Exception:
                        pass
                results.append(doc)
        
        # Sort by score (descending)
        results.sort(key=lambda x: x.get("score", 0), reverse=True)

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

        print(f"[DEBUG] Search completed: {len(results)} results for query '{query}' with filters: {filters}")
        if filters and len(results) == 0:
            print(f"[WARNING] No results found with filters. This might indicate a filter issue.")
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        print(f"[ERROR] Search failed: {e}")
        import traceback
        traceback.print_exc()
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

def _builder_profile_search_impl(query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Internal implementation of builder profile search.
    """
    project_fields = {
        "company_name": 1,
        "specialization": 1,
        "experience_years": 1,
        "city": 1,
        "location": 1,  # Include location if it exists
        "rating": 1,
        "about": 1,
        "contact_person": 1,
        "contact_email": 1,
        "contact_phone": 1,
    }
    search_coro = _search_async(
        query,
        collection_name="builder_profiles",
        index_name="builder_profile_index",
        project_fields=project_fields,
        k=5,
        filters=filters
    )
    return _run_async_search(search_coro)

@tool
def builder_profile_search_tool(query: str) -> Dict[str, Any]:
    """
    Searches for builder profiles based on a natural language query.
    Automatically extracts filters (city, experience, specialization, rating) from the query.
    Use this to find builders, construction companies, or contractors.
    
    Args:
        query: The user's search query (e.g., "builders in Islamabad with 5+ years experience").
    """
    # Extract filters from the query, but don't fail if extraction fails
    filters = None
    try:
        from .filter_extractor import extract_builder_filters
        filters = extract_builder_filters(query)
        if not filters:
            filters = None
    except Exception as e:
        # If filter extraction fails, continue without filters
        print(f"Filter extraction failed (continuing without filters): {e}")
        filters = None
    
    return _builder_profile_search_impl(query, filters)

def _builder_service_search_impl(query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Internal implementation of builder service search.
    """
    project_fields = {
        "title": 1,  # The actual field name in the database
        "description": 1,
        "category": 1,
        "base_price": 1,  # Also include base_price
        "price_unit": 1,  # And price_unit
        "price_range_min": 1,
        "price_range_max": 1,
        "estimated_duration": 1,
        "service_features": 1,
        "builder_id": 1, # To link back to the builder
    }
    search_coro = _search_async(
        query,
        collection_name="builder_services",
        index_name="builder_service_index",
        project_fields=project_fields,
        k=5,
        filters=filters
    )
    return _run_async_search(search_coro)

@tool
def builder_service_search_tool(query: str) -> Dict[str, Any]:
    """
    Searches for specific services offered by builders.
    Automatically extracts filters (city, category, price range, duration) from the query.
    Use this to find services like 'kitchen remodeling', 'roof repair', or 'new home construction'.
    
    Args:
        query: The user's search query for a service (e.g., "plumbing services in Karachi under 50000").
    """
    # Extract filters from the query, but don't fail if extraction fails
    filters = None
    try:
        from .filter_extractor import extract_service_filters
        filters = extract_service_filters(query)
        if not filters:
            filters = None
    except Exception as e:
        # If filter extraction fails, continue without filters
        print(f"Filter extraction failed (continuing without filters): {e}")
        filters = None
    
    return _builder_service_search_impl(query, filters)
