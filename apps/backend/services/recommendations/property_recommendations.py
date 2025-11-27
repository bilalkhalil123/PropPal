"""
Property recommendation service based on user's chat history.

This service analyzes a user's chat history to extract property search patterns
and generate personalized property recommendations.
"""
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from services.embeddings.service import embed_text
from services.vector_search.qdrant_service import search_properties as qdrant_search_properties


async def get_recommended_properties(
    user_id: str,
    db: AsyncIOMotorDatabase,
    limit: int = 12,
    days_back: int = 30,
) -> Dict[str, Any]:
    """
    Generate property recommendations based on user's chat history.
    
    Args:
        user_id: User's MongoDB ObjectId as string
        db: MongoDB database instance
        limit: Maximum number of recommendations to return
        days_back: How many days of history to analyze (default: 30)
        
    Returns:
        Dictionary with:
            - properties: List of recommended properties
            - count: Number of properties returned
            - source: "recent_searches" or "popular" (fallback)
    """
    try:
        # Convert user_id to ObjectId if valid
        query_id: Any = user_id
        if ObjectId.is_valid(user_id):
            query_id = ObjectId(user_id)
        
        # Query chat history documents for this user (limit to recent ones for performance)
        # Only get documents updated in the last 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        cursor = db["chat_histories"].find({
            "user_id": query_id,
            "updated_at": {"$gte": cutoff_date}
        }).sort("updated_at", -1).limit(20)  # Limit to 20 most recent documents
        docs = await cursor.to_list(length=20)
        
        if not docs:
            # No chat history - return popular properties as fallback
            return await get_popular_properties(db, limit)
        
        # Extract search queries and property results from chat history
        search_data = _extract_search_data(docs, days_back)
        
        if not search_data["queries"] and not search_data["property_ids"]:
            # No property searches found - return popular properties
            return await get_popular_properties(db, limit)
        
        # Generate recommendations using vector search
        recommendations = await _generate_recommendations(
            search_data,
            db,
            limit,
        )
        
        if recommendations["count"] > 0:
            return {
                **recommendations,
                "source": "recent_searches",
            }
        else:
            # Fallback to popular properties if no recommendations found
            return await get_popular_properties(db, limit)
            
    except Exception as e:
        # On error, return popular properties as fallback
        print(f"[RECOMMENDATIONS] Error generating recommendations: {e}")
        return await get_popular_properties(db, limit)


def _extract_search_data(
    docs: List[Dict[str, Any]],
    days_back: int = 30,
) -> Dict[str, Any]:
    """
    Extract property search queries and results from chat history documents.
    
    Returns:
        Dictionary with:
            - queries: List of search query strings with timestamps
            - property_ids: Set of property IDs from search results
            - cities: Set of cities from search results
            - property_types: Set of property types from search results
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    
    queries: List[Dict[str, Any]] = []
    property_ids: Set[str] = set()
    cities: Set[str] = set()
    property_types: Set[str] = set()
    
    for doc in docs:
        messages = doc.get("messages", [])
        
        # Process messages in pairs (user message + AI response)
        for i in range(len(messages)):
            msg = messages[i]
            
            # Only process user messages
            if msg.get("role") != "user":
                continue
            
            timestamp = msg.get("timestamp")
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except:
                    continue
            
            # Skip messages older than cutoff
            if timestamp and timestamp < cutoff_date:
                continue
            
            # Check if the next message (AI response) contains property search results
            if i + 1 < len(messages):
                ai_response = messages[i + 1]
                payload = ai_response.get("_payload", {})
                
                if payload.get("classification") == "listing_agent":
                    # This was a property search
                    query_text = msg.get("content", "").strip()
                    if query_text:
                        queries.append({
                            "query": query_text,
                            "timestamp": timestamp or datetime.utcnow(),
                        })
                    
                    # Extract property IDs and metadata from results
                    properties = payload.get("properties", [])
                    for prop in properties:
                        prop_id = prop.get("_id") or prop.get("id")
                        if prop_id:
                            property_ids.add(str(prop_id))
                        
                        if prop.get("city"):
                            cities.add(prop.get("city"))
                        if prop.get("property_type"):
                            property_types.add(prop.get("property_type"))
    
    # Sort queries by timestamp (most recent first)
    queries.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
    
    return {
        "queries": queries[:10],  # Use last 10 queries
        "property_ids": list(property_ids),
        "cities": list(cities),
        "property_types": list(property_types),
    }


async def _generate_recommendations(
    search_data: Dict[str, Any],
    db: AsyncIOMotorDatabase,
    limit: int,
) -> Dict[str, Any]:
    """
    Generate property recommendations using vector search on recent queries.
    
    Args:
        search_data: Extracted search data from chat history
        db: MongoDB database instance
        limit: Maximum number of recommendations
        
    Returns:
        Dictionary with properties and count
    """
    queries = search_data["queries"]
    seen_property_ids = set(search_data["property_ids"])
    
    if not queries:
        return {"properties": [], "count": 0}
    
    # Use the most recent queries for vector search (limit to 3 for speed)
    recent_queries = queries[:3]  # Use top 3 most recent queries (reduced from 5)
    
    # If we have seen property IDs from chat history, use those first
    if seen_property_ids:
        # Fetch those properties directly (fast)
        property_oids = []
        for prop_id in list(seen_property_ids)[:limit]:
            try:
                if ObjectId.is_valid(prop_id):
                    property_oids.append(ObjectId(prop_id))
            except:
                continue
        
        if property_oids:
            properties_cursor = db["properties"].find(
                {"_id": {"$in": property_oids}},
                {
                    "_id": 1,
                    "title": 1,
                    "price": 1,
                    "city": 1,
                    "area": 1,
                    "property_type": 1,
                    "bedrooms": 1,
                    "bathrooms": 1,
                    "area_sqft": 1,
                    "images": 1,
                }
            )
            direct_properties = await properties_cursor.to_list(length=limit)
            
            # Convert ObjectId to string
            for prop in direct_properties:
                if "_id" in prop and isinstance(prop["_id"], ObjectId):
                    prop["_id"] = str(prop["_id"])
            
            if len(direct_properties) >= limit:
                return {
                    "properties": direct_properties[:limit],
                    "count": len(direct_properties[:limit]),
                }
    
    # Aggregate results from multiple queries
    all_results: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set(seen_property_ids)  # Start with already seen IDs
    
    for query_data in recent_queries:
        query_text = query_data["query"]
        
        try:
            # Generate embedding for the query
            query_vec = embed_text(query_text)
            
            # Search Qdrant for similar properties (reduced limit for speed)
            qdrant_results = await qdrant_search_properties(
                query_vector=query_vec,
                limit=limit,  # Reduced from limit * 2
                filters=None,
            )
            
            # Add results that we haven't seen yet
            for result in qdrant_results:
                prop_id = result.get("id")
                if prop_id and prop_id not in seen_ids:
                    seen_ids.add(prop_id)
                    all_results.append({
                        "id": prop_id,
                        "score": result.get("score", 0.0),
                        "timestamp": query_data.get("timestamp"),
                    })
        except Exception as e:
            print(f"[RECOMMENDATIONS] Error searching for query '{query_text}': {e}")
            continue
    
    if not all_results:
        return {"properties": [], "count": 0}
    
    # Sort by score (relevance) and recency
    def _sort_key(result: Dict[str, Any]) -> tuple:
        score = result.get("score", 0.0)
        timestamp = result.get("timestamp", datetime.min)
        # Higher score and more recent = better
        return (-score, timestamp.timestamp() if isinstance(timestamp, datetime) else 0)
    
    all_results.sort(key=_sort_key)
    
    # Get top N unique property IDs
    top_property_ids = [r["id"] for r in all_results[:limit * 2]]
    
    # Fetch full property documents from MongoDB
    property_oids = []
    for prop_id in top_property_ids:
        try:
            if ObjectId.is_valid(prop_id):
                property_oids.append(ObjectId(prop_id))
        except:
            continue
    
    if not property_oids:
        return {"properties": [], "count": 0}
    
    # Fetch properties from MongoDB
    properties_cursor = db["properties"].find(
        {"_id": {"$in": property_oids}},
        {
            "_id": 1,
            "title": 1,
            "price": 1,
            "city": 1,
            "area": 1,
            "property_type": 1,
            "bedrooms": 1,
            "bathrooms": 1,
            "area_sqft": 1,
            "images": 1,
        }
    )
    
    properties = await properties_cursor.to_list(length=limit * 2)
    
    # Convert ObjectId to string for JSON serialization
    for prop in properties:
        if "_id" in prop and isinstance(prop["_id"], ObjectId):
            prop["_id"] = str(prop["_id"])
    
    # Maintain order from Qdrant results
    property_map = {str(prop["_id"]): prop for prop in properties}
    ordered_properties = []
    for prop_id in top_property_ids:
        if prop_id in property_map:
            ordered_properties.append(property_map[prop_id])
            if len(ordered_properties) >= limit:
                break
    
    return {
        "properties": ordered_properties,
        "count": len(ordered_properties),
    }


async def get_popular_properties(
    db: AsyncIOMotorDatabase,
    limit: int,
) -> Dict[str, Any]:
    """
    Get popular/recent properties as fallback when user has no search history.
    
    Args:
        db: MongoDB database instance
        limit: Maximum number of properties to return
        
    Returns:
        Dictionary with properties and count
    """
    try:
        # Get recent properties (sorted by creation date or updated date)
        cursor = db["properties"].find(
            {},
            {
                "_id": 1,
                "title": 1,
                "price": 1,
                "city": 1,
                "area": 1,
                "property_type": 1,
                "bedrooms": 1,
                "bathrooms": 1,
                "area_sqft": 1,
                "images": 1,
            }
        ).sort("created_at", -1).limit(limit)
        
        properties = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        for prop in properties:
            if "_id" in prop and isinstance(prop["_id"], ObjectId):
                prop["_id"] = str(prop["_id"])
        
        return {
            "properties": properties,
            "count": len(properties),
            "source": "popular",
        }
    except Exception as e:
        print(f"[RECOMMENDATIONS] Error fetching popular properties: {e}")
        return {
            "properties": [],
            "count": 0,
            "source": "popular",
        }

