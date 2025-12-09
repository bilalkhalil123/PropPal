"""
Test script to verify Qdrant builder services search is working correctly.
"""
import asyncio
from services.vector_search.qdrant_service import search_builder_services
from services.embeddings.service import embed_text
from common.qdrant import get_qdrant_client, BUILDER_SERVICES_COLLECTION


async def test_search():
    """Test Qdrant builder services search functionality."""
    print("[TEST] Testing Qdrant builder services search...")
    
    # Check if collection exists and has data
    client = get_qdrant_client()
    try:
        collection_info = client.get_collection(BUILDER_SERVICES_COLLECTION)
        print(f"[TEST] Collection '{BUILDER_SERVICES_COLLECTION}' exists")
        print(f"[TEST] Points count: {collection_info.points_count}")
        
        if collection_info.points_count == 0:
            print("[ERROR] Collection is empty! Run migration first:")
            print("  python -m jobs.migrate_to_qdrant")
            return
    except Exception as e:
        print(f"[ERROR] Failed to get collection info: {e}")
        return
    
    # Test search
    query = "construction services"
    print(f"\n[TEST] Searching for: '{query}'")
    
    query_vec = embed_text(query)
    print(f"[TEST] Generated embedding (dimension: {len(query_vec)})")
    
    results = await search_builder_services(query_vec, limit=5)
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
    
    # Test with different query
    print("\n" + "="*60)
    print("[TEST] Testing with different query: 'interior design'")
    query2 = "interior design"
    query_vec2 = embed_text(query2)
    results2 = await search_builder_services(query_vec2, limit=5)
    print(f"[TEST] Search returned {len(results2)} results")
    
    if results2:
        print("\n[TEST] Results:")
        for i, result in enumerate(results2[:3], 1):
            print(f"  {i}. ID: {result['id']}, Score: {result['score']:.4f}")
            payload = result.get('payload', {})
            print(f"     Payload keys: {list(payload.keys())}")


if __name__ == "__main__":
    asyncio.run(test_search())

