"""
Create payload indexes in Qdrant collections for filtering.

This script creates indexes on fields that are used for filtering,
such as 'city' in properties and builder_profiles collections.
"""
import asyncio
from qdrant_client.models import PayloadSchemaType
from common.qdrant import (
    get_qdrant_client,
    PROPERTIES_COLLECTION,
    BUILDER_PROFILES_COLLECTION,
    BUILDER_SERVICES_COLLECTION,
)


async def create_indexes():
    """Create payload indexes for filtering."""
    print("[INDEX] Creating Qdrant payload indexes...")
    
    client = get_qdrant_client()
    loop = asyncio.get_event_loop()
    
    # Index for city in properties collection
    try:
        await loop.run_in_executor(
            None,
            lambda: client.create_payload_index(
                collection_name=PROPERTIES_COLLECTION,
                field_name="city",
                field_schema=PayloadSchemaType.KEYWORD,
            )
        )
        print(f"[INDEX] ✓ Created index on 'city' for '{PROPERTIES_COLLECTION}'")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"[INDEX] - Index on 'city' for '{PROPERTIES_COLLECTION}' already exists")
        else:
            print(f"[INDEX] ✗ Error creating city index for properties: {e}")
    
    # Index for city in builder_profiles collection
    try:
        await loop.run_in_executor(
            None,
            lambda: client.create_payload_index(
                collection_name=BUILDER_PROFILES_COLLECTION,
                field_name="city",
                field_schema=PayloadSchemaType.KEYWORD,
            )
        )
        print(f"[INDEX] ✓ Created index on 'city' for '{BUILDER_PROFILES_COLLECTION}'")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"[INDEX] - Index on 'city' for '{BUILDER_PROFILES_COLLECTION}' already exists")
        else:
            print(f"[INDEX] ✗ Error creating city index for builder_profiles: {e}")
    
    # Index for price in properties collection (for range queries)
    try:
        await loop.run_in_executor(
            None,
            lambda: client.create_payload_index(
                collection_name=PROPERTIES_COLLECTION,
                field_name="price",
                field_schema=PayloadSchemaType.FLOAT,
            )
        )
        print(f"[INDEX] ✓ Created index on 'price' for '{PROPERTIES_COLLECTION}'")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"[INDEX] - Index on 'price' for '{PROPERTIES_COLLECTION}' already exists")
        else:
            print(f"[INDEX] ✗ Error creating price index for properties: {e}")
    
    print("\n[INDEX] Index creation complete!")


if __name__ == "__main__":
    asyncio.run(create_indexes())

