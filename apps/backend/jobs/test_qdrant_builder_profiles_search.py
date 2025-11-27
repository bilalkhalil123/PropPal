"""
Test script to verify Qdrant builder profiles search is working correctly.
"""
import asyncio
from services.vector_search.qdrant_service import search_builder_profiles
from services.embeddings.service import embed_text
from common.qdrant import get_qdrant_client, BUILDER_PROFILES_COLLECTION


async def test_search():
    """Test Qdrant builder profiles search functionality."""
    print("[TEST] Testing Qdrant builder profiles search...")
    
    # Check if collection exists and has data
    client = get_qdrant_client()
    try:
        collection_info = client.get_collection(BUILDER_PROFILES_COLLECTION)
        print(f"[TEST] Collection '{BUILDER_PROFILES_COLLECTION}' exists")
        print(f"[TEST] Points count: {collection_info.points_count}")
        
        if collection_info.points_count == 0:
            print("[ERROR] Collection is empty! Run migration first:")
            print("  python -m jobs.migrate_to_qdrant")
            return
    except Exception as e:
        print(f"[ERROR] Failed to get collection info: {e}")
        return
    
    # Test search
    query = "experienced builder in Lahore"
    print(f"\n[TEST] Searching for: '{query}'")
    
    query_vec = embed_text(query)
    print(f"[TEST] Generated embedding (dimension: {len(query_vec)})")
    
    results = await search_builder_profiles(query_vec, limit=5)
    print(f"\n[TEST] Search returned {len(results)} results")
    
    if results:
        print("\n[TEST] Sample results:")
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. ID: {result['id']}, Score: {result['score']:.4f}")
            print(f"     Payload: {result.get('payload', {})}")
    else:
        print("[ERROR] No results returned from search!")
        print("\nPossible issues:")
        print("  1. No data in Qdrant - run: python -m jobs.migrate_to_qdrant")
        print("  2. Embeddings don't match query")
        print("  3. Collection might be empty")
    
    # Test with city filter
    print("\n" + "="*60)
    print("[TEST] Testing with city filter: 'Lahore'")
    query2 = "experienced builder"
    query_vec2 = embed_text(query2)
    results2 = await search_builder_profiles(
        query_vec2, 
        limit=5, 
        filters={"city": "Lahore"}
    )
    print(f"[TEST] Filtered search returned {len(results2)} results")
    
    if results2:
        print("\n[TEST] Filtered results:")
        for i, result in enumerate(results2[:3], 1):
            print(f"  {i}. ID: {result['id']}, Score: {result['score']:.4f}")
            payload = result.get('payload', {})
            location = payload.get('location', {})
            city = location.get('city', 'N/A') if isinstance(location, dict) else 'N/A'
            print(f"     City: {city}, Payload keys: {list(payload.keys())}")


if __name__ == "__main__":
    asyncio.run(test_search())

