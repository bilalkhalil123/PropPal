from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.db import get_db_session_ctx
from common.qdrant import ensure_collections_exist
from common.repositories.builder_profile_repository import BuilderProfileRepository
from common.repositories.builder_service_repository import BuilderServiceRepository
from services.embeddings.compose import compose_builder_services_text
from services.embeddings.service import embed_batch
from services.vector_search.qdrant_service import upsert_builder_service_embeddings_batch


async def _fetch_builder_profiles(profile_repo: BuilderProfileRepository, page_size: int = 500) -> Dict[str, str]:
    company_to_builder_id: Dict[str, str] = {}
    skip = 0
    while True:
        rows = await profile_repo.list_all(skip=skip, limit=page_size)
        if not rows:
            break
        for row in rows:
            company_name = row.get("company_name")
            if not company_name:
                continue
            if company_name not in company_to_builder_id:
                company_to_builder_id[company_name] = row.get("id") or row.get("_id")
        skip += page_size
        if len(rows) < page_size:
            break
    return company_to_builder_id


def _clean_service_data(service_data: Dict[str, Any]) -> Dict[str, Any]:
    allowed_keys = {
        "title",
        "service_name",
        "description",
        "category",
        "base_price",
        "price_unit",
        "estimated_duration",
        "service_features",
        "service_images",
        "company_name",
    }
    clean = {k: v for k, v in service_data.items() if k in allowed_keys}
    if not clean.get("title") and clean.get("service_name"):
        clean["title"] = clean.get("service_name")
    return clean


async def populate_builder_services(file_path: str, batch_size: int, limit: Optional[int]) -> None:
    """
    Populates Postgres builder_services with data from a JSON file,
    linking services to builders using their company_name, and upserts embeddings to Qdrant.
    """
    await ensure_collections_exist()

    # 1. Read builder services from JSON file
    print(f"[POPULATE] Reading builder services from {file_path}...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            services_data = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Data file not found at: {file_path}")
        return
    except json.JSONDecodeError:
        print(f"[ERROR] Could not decode JSON from file: {file_path}")
        return

    if limit is not None:
        services_data = services_data[: max(limit, 0)]

    processed = 0
    created = 0
    pending_services: List[Dict[str, Any]] = []

    async with get_db_session_ctx() as session:
        profile_repo = BuilderProfileRepository(session)
        service_repo = BuilderServiceRepository(session)

        company_to_builder_id = await _fetch_builder_profiles(profile_repo)
        print(f"[POPULATE] Found {len(company_to_builder_id)} builder profiles.")

        if not company_to_builder_id:
            print("[ERROR] No builder profiles found in Postgres. Cannot create services.")
            return

        for service_data in services_data:
            if limit is not None and created >= limit:
                break

            clean_data = _clean_service_data(service_data)
            company_name = clean_data.get("company_name")
            if not company_name:
                print("[WARNING] Skipping service with missing company_name.")
                continue

            builder_id = company_to_builder_id.get(company_name)
            if not builder_id:
                print(f"[WARNING] No builder profile found for company_name: {company_name}. Skipping.")
                continue

            if not clean_data.get("title") or not clean_data.get("description"):
                print("[WARNING] Skipping service with missing title or description.")
                continue

            if clean_data.get("base_price") is None or not clean_data.get("price_unit"):
                print("[WARNING] Skipping service with missing base_price or price_unit.")
                continue

            create_data = {
                "builder_id": builder_id,
                "title": clean_data.get("title"),
                "description": clean_data.get("description"),
                "category": clean_data.get("category", ""),
                "base_price": clean_data.get("base_price"),
                "price_unit": clean_data.get("price_unit"),
                "estimated_duration": clean_data.get("estimated_duration"),
                "service_features": clean_data.get("service_features"),
                "service_images": clean_data.get("service_images"),
            }
            row = await service_repo.create(create_data)
            created += 1

            pending_services.append({
                "service_id": row.id,
                "data": create_data,
            })

            if len(pending_services) >= batch_size:
                texts = [compose_builder_services_text(s["data"]) for s in pending_services]
                vectors = embed_batch(texts)
                items = []
                for pending, vec in zip(pending_services, vectors):
                    items.append((
                        pending["service_id"],
                        vec,
                        {
                            "title": pending["data"].get("title", ""),
                            "category": pending["data"].get("category", ""),
                            "builder_id": str(pending["data"].get("builder_id", "")),
                        },
                    ))
                await upsert_builder_service_embeddings_batch(items)
                processed += len(pending_services)
                print(f"[POPULATE] Builder services: {processed} embeddings upserted to Qdrant")
                pending_services = []

        if pending_services:
            texts = [compose_builder_services_text(s["data"]) for s in pending_services]
            vectors = embed_batch(texts)
            items = []
            for pending, vec in zip(pending_services, vectors):
                items.append((
                    pending["service_id"],
                    vec,
                    {
                        "title": pending["data"].get("title", ""),
                        "category": pending["data"].get("category", ""),
                        "builder_id": str(pending["data"].get("builder_id", "")),
                    },
                ))
            await upsert_builder_service_embeddings_batch(items)
            processed += len(pending_services)
            print(f"[POPULATE] Builder services: {processed} embeddings upserted to Qdrant")

    print(f"[POPULATE] Done. Created {created} builder services.")


def main() -> None:
    """Main function to run the builder services population script."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        type=str,
        default="../../../data/builder_services_extended.json",
        help="Path to the builder services data JSON file relative to the jobs directory.",
    )
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    jobs_dir = Path(__file__).resolve().parent
    file_path = (jobs_dir / args.file).resolve()

    asyncio.run(populate_builder_services(str(file_path), args.batch_size, args.limit))


if __name__ == "__main__":
    main()
