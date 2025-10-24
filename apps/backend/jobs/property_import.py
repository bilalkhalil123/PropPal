"""
CLI importer to ingest Zameen property listings JSON into MongoDB.

Usage (PowerShell):
  cd apps/backend
  .\\venv\\Scripts\\python.exe -m services.property_import --json-path ..\\..\\data\\zameen_listing_results.json --seller-id <ObjectId> --dry-run
  .\\venv\\Scripts\\python.exe -m services.property_import --json-path ..\\..\\data\\zameen_listing_results.json --seller-id <ObjectId>
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

# Local imports (absolute to support -m execution from apps/backend)
from common.config import get_settings
from common.db import DatabaseClient
from models.properties import PropertyCreate


def _parse_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _parse_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _extract_floors_from_description(description: str) -> int:
    if not description:
        return 1
    match = re.search(r"[Ff]loors\s*:\s*(\d+)", description)
    if match:
        return _parse_int(match.group(1), 1)
    return 1


def _first_area_from_location(location_detail: Optional[str]) -> str:
    if not location_detail:
        return ""
    return location_detail.split(",")[0].strip()


def _filter_image_urls(image_urls: Optional[List[str]]) -> List[str]:
    if not image_urls:
        return []
    result: List[str] = []
    for url in image_urls:
        if not isinstance(url, str):
            continue
        lower = url.lower()
        if lower.endswith(".svg"):
            continue
        result.append(url)
    return result


def transform_record(record: Dict[str, Any], seller_id: ObjectId) -> Optional[Dict[str, Any]]:
    """Transform one Zameen record into PropertyCreate-compatible dict.

    Returns None if required fields are missing/invalid.
    """
    title = (record.get("Title") or "").strip()
    description = (record.get("Description") or "").strip()
    price = _parse_float(record.get("Price"), 0.0)
    lat = _parse_float(record.get("Latitude"), math.nan)
    lng = _parse_float(record.get("Longitude"), math.nan)
    if not title or price <= 0 or math.isnan(lat) or math.isnan(lng):
        return None

    property_type_raw = (record.get("Property_Type") or "").strip()
    property_type = property_type_raw.lower() if property_type_raw else ""

    area_sqft = _parse_float(record.get("Area"), 0.0)
    bedrooms = _parse_int(record.get("Bedrooms"), 0)
    bathrooms = _parse_int(record.get("Bathrooms"), 0)
    floors = _extract_floors_from_description(description)
    city = (record.get("City") or "").strip()
    area = _first_area_from_location(record.get("Location_Detail"))
    images = _filter_image_urls(record.get("Image_URLs"))

    # Provenance
    external_id = str(record.get("Ad_ID")) if record.get("Ad_ID") is not None else None
    source = "zameen"
    source_url = record.get("URL")
    date_added_str = record.get("Date_Added")
    date_added: Optional[datetime] = None
    if date_added_str:
        try:
            date_added = datetime.fromisoformat(date_added_str)
        except Exception:
            date_added = None

    # Build payload
    payload: Dict[str, Any] = {
        "title": title,
        "description": description,
        "price": price,
        "property_type": property_type,
        "area_sqft": area_sqft,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "floors": floors if floors > 0 else 1,
        "city": city,
        "area": area,
        "lng": lng,
        "lat": lat,
        "seller_id": seller_id,
        "images": images,
        "metadata": {"raw": record},
        "external_id": external_id,
        "source": source,
        "source_url": source_url,
        "date_added": date_added,
    }

    # Validate using Pydantic to ensure shape
    try:
        _ = PropertyCreate(**payload)
    except Exception as e:
        # If validation fails, drop the record
        return None

    return payload


async def insert_records(db: AsyncIOMotorDatabase, records: List[Dict[str, Any]]) -> List[ObjectId]:
    if not records:
        return []
    result = await db["properties"].insert_many(records)
    return list(result.inserted_ids)


async def main_async(args: argparse.Namespace) -> None:
    settings = get_settings()
    # Ensure DB client is created like in lifespan
    if DatabaseClient.client is None:
        from motor.motor_asyncio import AsyncIOMotorClient

        DatabaseClient.client = AsyncIOMotorClient(settings.MONGODB_URL)
        DatabaseClient.database = DatabaseClient.client[settings.MONGODB_DB_NAME]

    db = DatabaseClient.database
    assert db is not None

    json_path = Path(args.json_path)
    if not json_path.exists():
        print(f"[ERROR] JSON file not found: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    seller_id = ObjectId(args.seller_id)

    transformed: List[Dict[str, Any]] = []
    skipped = 0
    for rec in data:
        payload = transform_record(rec, seller_id)
        if payload is None:
            skipped += 1
            continue
        transformed.append(payload)

    print(f"[INFO] Valid records: {len(transformed)}, Skipped: {skipped}")

    if args.dry_run:
        for sample in transformed[:3]:
            print({k: sample[k] for k in ["title", "price", "city", "area", "external_id"]})
        return

    if args.limit is not None and args.limit > 0:
        transformed = transformed[: args.limit]

    inserted_ids = await insert_records(db, transformed)
    print(f"[SUCCESS] Inserted: {len(inserted_ids)}")
    if inserted_ids:
        print(f"[FIRST_ID] {inserted_ids[0]}")
        print(f"[LAST_ID] {inserted_ids[-1]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Zameen listings JSON")
    parser.add_argument(
        "--json-path",
        type=str,
        required=True,
        help="Path to zameen_listing_results.json",
    )
    parser.add_argument(
        "--seller-id",
        type=str,
        required=True,
        help="Default seller ObjectId to attach to all listings",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and show sample payloads without inserting",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of records to insert (ignored in dry-run)",
    )
    return parser.parse_args()


def main() -> None:
    import asyncio

    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()


