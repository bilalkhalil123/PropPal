"""
Amenity enrichment service.

Orchestrates: fetch amenities from Overpass API → generate summary via Groq → 
save to Postgres → update Qdrant embedding + payload.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Groq summary generation
# ---------------------------------------------------------------------------

def generate_amenity_summary(amenities_json: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    Use Groq LLM to generate a concise, human-readable summary of nearby amenities.
    Falls back to a simple template if the Groq call fails.
    """
    if not amenities_json:
        return "No nearby amenities data available."

    # Build a compact representation for the LLM
    compact_lines: list[str] = []
    for category, items in amenities_json.items():
        for item in items[:5]:  # max 5 per category to keep prompt small
            name = item.get("name", "Unknown")
            dist = item.get("distance_m", 0)
            compact_lines.append(f"- {name} ({category}, {int(dist)}m away)")

    if not compact_lines:
        return "No nearby amenities data available."

    amenity_list_text = "\n".join(compact_lines)

    try:
        from groq import Groq

        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        chat_completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a real-estate assistant. Given a list of nearby amenities for a property, "
                        "write a concise 2-4 sentence summary highlighting the most useful ones. "
                        "Mention distances. Focus on schools, hospitals, grocery stores, and pharmacies. "
                        "Do NOT use bullet points — write flowing prose."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Nearby amenities:\n{amenity_list_text}",
                },
            ],
            temperature=0.3,
            max_tokens=200,
        )
        summary = chat_completion.choices[0].message.content.strip()
        return summary
    except Exception as e:
        logger.warning("Groq summary generation failed, using template fallback: %s", e)
        return _template_summary(amenities_json)


def _template_summary(amenities_json: Dict[str, List[Dict[str, Any]]]) -> str:
    """Simple template fallback if Groq is unavailable."""
    parts: list[str] = []
    for category, items in amenities_json.items():
        if items:
            top = items[0]
            parts.append(f"{top.get('name', 'Unknown')} ({category}, {int(top.get('distance_m', 0))}m)")
    if not parts:
        return "No nearby amenities data available."
    return "Nearby amenities include: " + ", ".join(parts[:6]) + "."


# ---------------------------------------------------------------------------
# Full enrichment pipeline
# ---------------------------------------------------------------------------

async def enrich_property_amenities(
    property_id: str,
    lat: float,
    lon: float,
    city: str = "",
    area: str = "",
) -> None:
    """
    End-to-end amenity enrichment for a single property:
    1. Fetch amenities from Overpass API
    2. Generate summary via Groq
    3. Save to Postgres (nearby_amenities + amenity_summary columns)
    4. Re-generate embedding with amenity text and update Qdrant payload
    """
    from jobs.amenities import fetch_nearby_amenities
    from common.db import get_db_session_ctx
    from db.models import Property as PropertyModel
    from sqlalchemy import select
    from services.embeddings.compose import compose_property_text
    from services.embeddings.service import embed_text
    from services.vector_search.qdrant_service import upsert_property_embedding

    logger.info("[AMENITY] Enriching property %s at (%s, %s)", property_id, lat, lon)

    # 1. Fetch amenities
    try:
        amenities_json = fetch_nearby_amenities(
            property_lat=lat,
            property_lon=lon,
            radius_m=2000,
            amenity_types=[
                "hospital", "clinic", "pharmacy", "dentist",
                "school", "university", "college",
                "supermarket", "marketplace", "mall",
                "police", "place_of_worship",
            ],
        )

    except Exception as e:
        logger.error("[AMENITY] Overpass fetch failed for property %s: %s", property_id, e)
        return

    # 2. Generate summary
    summary = generate_amenity_summary(amenities_json)
    logger.info("[AMENITY] Summary for %s: %s", property_id, summary[:120])

    # 3. Save to Postgres
    try:
        async with get_db_session_ctx() as session:
            result = await session.execute(
                select(PropertyModel).where(PropertyModel.id == property_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                logger.warning("[AMENITY] Property %s not found in DB", property_id)
                return

            row.nearby_amenities = amenities_json
            row.amenity_summary = summary
            await session.flush()

            # Build property dict for embedding text
            from common.repositories.property_repository import PropertyRepository
            repo = PropertyRepository(session)
            prop_dict = repo._row_to_dict(row)

            # 4. Re-generate embedding with amenity text included
            text_for_embedding = compose_property_text(prop_dict)
            embedding = embed_text(text_for_embedding)

            # Build Qdrant payload with location, amenity_summary, area, city
            qdrant_metadata = {
                "title": row.title,
                "city": row.city,
                "area": row.area,
                "property_type": row.property_type,
                "bedrooms": row.bedrooms,
                "bathrooms": row.bathrooms,
                "price": row.price,
                "amenity_summary": summary,
            }
            # Add geo location if coordinates are available
            if row.lat is not None and row.lng is not None:
                qdrant_metadata["location"] = {
                    "lat": row.lat,
                    "lon": row.lng,
                }

            await upsert_property_embedding(
                property_id=property_id,
                embedding=embedding,
                metadata=qdrant_metadata,
            )
            logger.info("[AMENITY] Qdrant updated for property %s", property_id)

    except Exception as e:
        logger.error("[AMENITY] DB/Qdrant update failed for property %s: %s", property_id, e)
