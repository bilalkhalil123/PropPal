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

async def _search_async(query: str, collection_name: str, index_name: str, project_fields: Dict[str, Any], k: int = 5, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generic vector search function for a given collection with optional filters.
    
    Args:
        query: Search query text
        collection_name: MongoDB collection name
        index_name: Vector search index name
        project_fields: Fields to project in results
        k: Number of results to return
        filters: Optional dictionary of filters to apply (city, experience_years_min, etc.)
    """
    client = None
    try:
        if not query:
            return {"success": True, "query": query, "results": [], "count": 0}

        client = get_database_client()
        db = client["proppal"]

        query_vec = embed_text(query)

        # Build the filter for $vectorSearch
        vector_search_filter = {}
        city_filter_value = None  # Store city filter for post-filtering
        
        # Only process filters if they exist and are not empty
        if filters and isinstance(filters, dict) and len(filters) > 0:
            print(f"[DEBUG] Processing filters: {filters}")
            # Handle city filter - we'll apply it AFTER vector search for better compatibility
            if "city" in filters and filters["city"]:
                city_filter_value = filters["city"].strip()
                # Normalize city name (capitalize first letter)
                city_filter_value = city_filter_value.capitalize()
                print(f"[DEBUG] Will apply city filter post-search: {city_filter_value}")
                # Don't add city to vector_search_filter - we'll filter after
            
            # Handle experience_years filter (builder_profiles only)
            if collection_name == "builder_profiles":
                exp_filter = {}
                if "experience_years_min" in filters and filters["experience_years_min"] is not None:
                    exp_filter["$gte"] = filters["experience_years_min"]
                if "experience_years_max" in filters and filters["experience_years_max"] is not None:
                    exp_filter["$lte"] = filters["experience_years_max"]
                if exp_filter:
                    if "$or" in vector_search_filter:
                        # If we have $or, wrap everything in $and
                        if "$and" not in vector_search_filter:
                            vector_search_filter = {"$and": [vector_search_filter, {"experience_years": exp_filter}]}
                        else:
                            vector_search_filter["$and"].append({"experience_years": exp_filter})
                    else:
                        vector_search_filter["experience_years"] = exp_filter
                
                # Handle specialization filter
                if "specialization" in filters and filters["specialization"]:
                    spec_filter = {"specialization": {"$in": filters["specialization"]}}
                    if "$or" in vector_search_filter or "experience_years" in vector_search_filter:
                        if "$and" not in vector_search_filter:
                            vector_search_filter = {"$and": [vector_search_filter, spec_filter]}
                        else:
                            vector_search_filter["$and"].append(spec_filter)
                    else:
                        vector_search_filter.update(spec_filter)
                
                # Handle rating filter
                if "rating_min" in filters and filters["rating_min"] is not None:
                    rating_filter = {"rating": {"$gte": filters["rating_min"]}}
                    if "$or" in vector_search_filter or "experience_years" in vector_search_filter or "specialization" in vector_search_filter:
                        if "$and" not in vector_search_filter:
                            vector_search_filter = {"$and": [vector_search_filter, rating_filter]}
                        else:
                            vector_search_filter["$and"].append(rating_filter)
                    else:
                        vector_search_filter.update(rating_filter)
            
            # Handle service-specific filters
            if collection_name == "builder_services":
                service_filters = {}
                
                if "category" in filters and filters["category"]:
                    service_filters["category"] = filters["category"]
                
                if "price_min" in filters and filters["price_min"] is not None:
                    service_filters["price_range_min"] = {"$gte": filters["price_min"]}
                if "price_max" in filters and filters["price_max"] is not None:
                    if "price_range_min" in service_filters:
                        service_filters["price_range_min"]["$lte"] = filters["price_max"]
                    else:
                        service_filters["price_range_max"] = {"$lte": filters["price_max"]}
                
                if "base_price_min" in filters and filters["base_price_min"] is not None:
                    service_filters["base_price"] = {"$gte": filters["base_price_min"]}
                if "base_price_max" in filters and filters["base_price_max"] is not None:
                    if "base_price" in service_filters:
                        service_filters["base_price"]["$lte"] = filters["base_price_max"]
                    else:
                        service_filters["base_price"] = {"$lte": filters["base_price_max"]}
                
                if service_filters:
                    if vector_search_filter:
                        # Combine with existing filters using $and
                        if "$and" not in vector_search_filter:
                            vector_search_filter = {"$and": [vector_search_filter, service_filters]}
                        else:
                            vector_search_filter["$and"].append(service_filters)
                    else:
                        vector_search_filter.update(service_filters)

        # Build the vector search stage
        vector_search_stage = {
            "$vectorSearch": {
                "index": index_name,
                "path": "embeddings",
                "queryVector": query_vec,
                "numCandidates": max(100, k * 10),
                "limit": k * 2,  # Get more candidates for post-filtering
            }
        }
        
        # Add filter to vector search if present
        if vector_search_filter:
            vector_search_stage["$vectorSearch"]["filter"] = vector_search_filter

        pipeline: List[Dict[str, Any]] = [
            vector_search_stage,
            {
                "$project": {
                    "score": {"$meta": "vectorSearchScore"},
                    **project_fields
                }
            },
        ]
        
        # Apply city filter AFTER vector search (post-filtering for better compatibility)
        if city_filter_value:
            if collection_name == "builder_profiles":
                # Add a $match stage to filter by city (case-insensitive using regex)
                pipeline.append({
                    "$match": {
                        "$or": [
                            {"location.city": {"$regex": f"^{city_filter_value}$", "$options": "i"}},
                            {"city": {"$regex": f"^{city_filter_value}$", "$options": "i"}}
                        ]
                    }
                })
                print(f"[DEBUG] Added post-search city filter for builder_profiles: {city_filter_value}")
        
        # For services with city filter, we need to do a post-filter lookup
        if collection_name == "builder_services" and city_filter_value:
            # Add lookup to get builder's city (after vector search)
            pipeline.append({
                "$lookup": {
                    "from": "builder_profiles",
                    "localField": "builder_id",
                    "foreignField": "_id",
                    "as": "builder_info"
                }
            })
            pipeline.append({
                "$unwind": {
                    "path": "$builder_info",
                    "preserveNullAndEmptyArrays": True
                }
            })
            pipeline.append({
                "$match": {
                    "$or": [
                        {"builder_info.location.city": {"$regex": f"^{city_filter_value}$", "$options": "i"}},
                        {"builder_info.city": {"$regex": f"^{city_filter_value}$", "$options": "i"}}
                    ]
                }
            })
            print(f"[DEBUG] Added post-search city filter for services: {city_filter_value}")

        # Execute the pipeline
        print(f"[DEBUG] Executing pipeline with {len(pipeline)} stages")
        try:
            results = await db[collection_name].aggregate(pipeline).to_list(k * 2)
        except Exception as e:
            print(f"[ERROR] Pipeline execution failed: {e}")
            import traceback
            traceback.print_exc()
            # Try without filters as fallback
            if city_filter_value or vector_search_filter:
                print(f"[DEBUG] Retrying without filters as fallback")
                simple_pipeline = [
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
                results = await db[collection_name].aggregate(simple_pipeline).to_list(k)
            else:
                raise
        
        # Limit to k results after filtering
        results = results[:k]
        
        # If we have filters but no results, try without filters as a fallback
        if (city_filter_value or vector_search_filter) and len(results) == 0:
            print(f"[WARNING] No results with filters, trying without filters as fallback")
            try:
                fallback_pipeline = [
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
                fallback_results = await db[collection_name].aggregate(fallback_pipeline).to_list(k)
                if len(fallback_results) > 0:
                    print(f"[INFO] Fallback search found {len(fallback_results)} results")
                    results = fallback_results
            except Exception as e:
                print(f"[ERROR] Fallback search also failed: {e}")

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
