"""
Super Backfill: Reset Qdrant and re-populate all properties for 100% data consistency.

Steps:
1. Deletes and re-creates the Qdrant 'properties' collection.
2. Fetches all properties from Neon DB.
3. For properties with no amenity_summary: Runs full enrichment (Overpass + Groq + Qdrant).
4. For properties with existing enrichment: Re-embeds and updates Qdrant (fast path).

Usage (run from apps/backend):
  python -m jobs.super_backfill
  python -m jobs.super_backfill --limit 10
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Fix relative imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.db import get_db_session_ctx
from common.repositories.property_repository import get_property_repository
from db.models import Property as PropertyModel
from sqlalchemy import select
from services.amenities.service import enrich_property_amenities
from services.vector_search.qdrant_service import recreate_properties_collection, upsert_property_embedding
from services.embeddings.service import embed_text
from services.embeddings.compose import compose_property_text


async def super_backfill(limit: int | None = None, force: bool = False):
    # 1. (Skipped) Reset Qdrant - user requested not to delete collection records anymore.
    print("\n[SUPER_BACKFILL] Step 1: Skipping Qdrant collection reset...")

    # 2. Fetch all properties
    print("\n[SUPER_BACKFILL] Step 2: Fetching all properties from Neon DB...")
    async with get_db_session_ctx() as session:
        # Initialize repo with the active session
        from common.repositories.property_repository import PropertyRepository
        repo = PropertyRepository(session)

        # Filter for Islamabad properties only
        query = select(PropertyModel).where(
            PropertyModel.city.ilike("%islamabad%")
        ).order_by(PropertyModel.date_added.desc())
        if limit:
            query = query.limit(limit)
        
        result = await session.execute(query)
        properties = result.scalars().all()
        # To avoid holding connections indefinitely, we can convert rows to dicts here
        # so that we don't need the session anymore for "Quick Sync".
        properties_data = [repo._row_to_dict(p) for p in properties]
    
    total = len(properties_data)
    print(f"[SUPER_BACKFILL] Found {total} properties to process.")
    print(f"[SUPER_BACKFILL] Closed initial DB connection. Starting processing loop...")

    processed = 0
    full_enrichments = 0
    quick_syncs = 0
    errors = 0

    # 3. Main Loop
    for p_dict in properties_data:
        processed += 1
        p_id = p_dict["id"]
        p_city = p_dict.get("city")
        p_area = p_dict.get("area")
        p_lat = p_dict.get("lat")
        p_lng = p_dict.get("lng")
        p_title = p_dict.get("title")
        p_property_type = p_dict.get("property_type")
        p_bedrooms = p_dict.get("bedrooms")
        p_bathrooms = p_dict.get("bathrooms")
        p_price = p_dict.get("price")
        
        # Current amenity data in the DB
        p_amenity_summary = p_dict.get("amenity_summary")
        p_nearby_amenities = p_dict.get("nearby_amenities")

        print(f"\n[{processed}/{total}] Processing {p_id} ({p_city}/{p_area})...")
            
        try:
            # Check if full enrichment is needed (Overpass + Groq)
            # If force is True, we ALWAYS do full enrichment
            if force or p_amenity_summary is None or p_nearby_amenities is None:
                if p_lat is not None and p_lng is not None:
                    print(f" -> Full enrichment required (fetching from Overpass/Groq)...")
                    # NOTE: enrich_property_amenities creates its own session ctx
                    await enrich_property_amenities(
                        property_id=p_id,
                        lat=float(p_lat),
                        lon=float(p_lng),
                        city=p_city or "",
                        area=p_area or "",
                    )
                    full_enrichments += 1
                    # Respect Overpass rate limits (3s gap)
                    await asyncio.sleep(3.0)
                else:
                    print(f" -> Skipping: No coordinates found.")
                    errors += 1
            else:
                # Quick Sync: Just re-embed and update Qdrant (already in Postgres)
                print(f" -> Quick Sync (already enriched): Updating Qdrant payload...")
                text = compose_property_text(p_dict)
                embedding = embed_text(text)
                
                await upsert_property_embedding(
                    property_id=p_id,
                    embedding=embedding,
                    metadata={
                        "title": p_title,
                        "city": p_city,
                        "area": p_area,
                        "property_type": p_property_type,
                        "bedrooms": p_bedrooms,
                        "bathrooms": p_bathrooms,
                        "price": float(p_price) if p_price is not None else None,
                        "location": {"lat": float(p_lat), "lon": float(p_lng)} if p_lat is not None and p_lng is not None else None,
                        "amenity_summary": p_amenity_summary
                    }
                )
                quick_syncs += 1
                # Small sleep to be kind to OpenAI/Networking
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n[SUPER_BACKFILL] Interrupted by user. Saving progress and stopping...")
            break
        except Exception as e:
            print(f" -> ERROR processing {p_id}: {e}")
            errors += 1
            # Sleep briefly after an error before trying the next property
            await asyncio.sleep(2.0)
            continue


    print("\n" + "="*50)
    print("SUPER BACKFILL COMPLETE")
    print(f"Total processed:   {processed}")
    print(f"Full Enrichments: {full_enrichments}")
    print(f"Quick Syncs:      {quick_syncs}")
    print(f"Errors/Skipped:    {errors}")
    print("="*50 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Super Backfill for PropPal")
    parser.add_argument("--limit", type=int, help="Limit the number of properties processed")
    parser.add_argument("--force", action="store_true", help="Force re-enrichment from APIs")
    args = parser.parse_args()
    
    try:
        asyncio.run(super_backfill(args.limit, args.force))
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")

