from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.db import get_db_session_ctx
from common.qdrant import ensure_collections_exist
from common.repositories.builder_profile_repository import BuilderProfileRepository
from common.repositories.user_repository import UserRepository
from services.embeddings.compose import compose_builder_profile_text
from services.embeddings.service import embed_batch
from services.vector_search.qdrant_service import upsert_builder_profile_embeddings_batch


async def _fetch_builder_users(user_repo: UserRepository, page_size: int = 500) -> List[str]:
    users: List[str] = []
    skip = 0
    while True:
        batch = await user_repo.get_users_by_role("builder", skip=skip, limit=page_size)
        if not batch:
            break
        users.extend([u.id for u in batch])
        skip += page_size
        if len(batch) < page_size:
            break
    return users


def _slugify_company(company_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", ".", company_name.strip().lower()).strip(".")
    return slug or "builder"


async def _create_builder_user(
    user_repo: UserRepository,
    company_name: str,
    index: int,
) -> str:
    base = _slugify_company(company_name)
    candidate = f"{base}@example.com"
    suffix = 1
    while await user_repo.get_user_by_email(candidate):
        candidate = f"{base}.{index}.{suffix}@example.com"
        suffix += 1
    user = await user_repo.create_user(
        {
            "name": company_name or f"Builder {index}",
            "email": candidate,
            "role": "builder",
        }
    )
    return user.id


def _clean_profile_data(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    allowed_keys = {
        "company_name",
        "specialization",
        "experience_years",
        "portfolio_images",
        "rating",
        "about",
        "founded_year",
        "location",
    }
    clean = {k: v for k, v in profile_data.items() if k in allowed_keys}
    return clean


async def populate_builder_profiles(file_path: str, batch_size: int, limit: Optional[int]) -> None:
    """
    Populates Postgres builder_profiles with data from a JSON file,
    links them to builder users, and upserts embeddings to Qdrant.
    """
    await ensure_collections_exist()

    # 1. Read builder profiles from JSON file
    print(f"[POPULATE] Reading builder profiles from {file_path}...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            all_profiles = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Data file not found at: {file_path}")
        return
    except json.JSONDecodeError:
        print(f"[ERROR] Could not decode JSON from file: {file_path}")
        return

    sample_profiles = all_profiles
    if limit is not None:
        sample_profiles = all_profiles[: max(limit, 0)]

    processed = 0
    created = 0
    pending_profiles: List[Dict[str, Any]] = []

    async with get_db_session_ctx() as session:
        user_repo = UserRepository(session)
        profile_repo = BuilderProfileRepository(session)

        user_ids = await _fetch_builder_users(user_repo)
        print(f"[POPULATE] Found {len(user_ids)} builder users to assign profiles to.")

        for i, profile_data in enumerate(sample_profiles):
            if limit is not None and created >= limit:
                break
            if i >= len(user_ids):
                company_name = profile_data.get("company_name", "")
                user_id = await _create_builder_user(user_repo, company_name, i + 1)
                user_ids.append(user_id)
                print(f"[POPULATE] Created builder user for {company_name or 'unknown'} -> {user_id}")

            user_id = user_ids[i]
            profile_data["user_id"] = user_id
            existing_profile = await profile_repo.get_by_user_id(user_id)
            if existing_profile:
                print(f"[POPULATE] Builder profile for user_id {user_id} already exists. Skipping.")
                continue

            clean_data = _clean_profile_data(profile_data)
            if not clean_data.get("company_name") or clean_data.get("experience_years") is None:
                print("[WARNING] Skipping profile with missing company_name or experience_years.")
                continue

            create_data = {**clean_data, "user_id": user_id}
            row = await profile_repo.create(create_data)
            created += 1

            pending_profiles.append({
                "profile_id": row.id,
                "data": create_data,
            })

            if len(pending_profiles) >= batch_size:
                texts = [compose_builder_profile_text(p["data"]) for p in pending_profiles]
                vectors = embed_batch(texts)
                items = []
                for pending, vec in zip(pending_profiles, vectors):
                    loc = pending["data"].get("location") or {}
                    city = loc.get("city", "") if isinstance(loc, dict) else ""
                    items.append((
                        pending["profile_id"],
                        vec,
                        {
                            "company_name": pending["data"].get("company_name", ""),
                            "city": city,
                        },
                    ))
                await upsert_builder_profile_embeddings_batch(items)
                processed += len(pending_profiles)
                print(f"[POPULATE] Builder profiles: {processed} embeddings upserted to Qdrant")
                pending_profiles = []

        if pending_profiles:
            texts = [compose_builder_profile_text(p["data"]) for p in pending_profiles]
            vectors = embed_batch(texts)
            items = []
            for pending, vec in zip(pending_profiles, vectors):
                loc = pending["data"].get("location") or {}
                city = loc.get("city", "") if isinstance(loc, dict) else ""
                items.append((
                    pending["profile_id"],
                    vec,
                    {
                        "company_name": pending["data"].get("company_name", ""),
                        "city": city,
                    },
                ))
            await upsert_builder_profile_embeddings_batch(items)
            processed += len(pending_profiles)
            print(f"[POPULATE] Builder profiles: {processed} embeddings upserted to Qdrant")

    print(f"[POPULATE] Done. Created {created} builder profiles.")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(all_profiles, f, ensure_ascii=False, indent=2)
        print(f"[POPULATE] Updated JSON user_id values at {file_path}")
    except Exception as exc:
        print(f"[WARNING] Could not write updated JSON file: {exc}")


def main() -> None:
    """Main function to run the builder profile population script."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        type=str,
        default="../../../data/builder_profiles_extended.json",
        help="Path to the builder profiles data JSON file relative to the jobs directory.",
    )
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    jobs_dir = Path(__file__).resolve().parent
    file_path = (jobs_dir / args.file).resolve()

    asyncio.run(populate_builder_profiles(str(file_path), args.batch_size, args.limit))


if __name__ == "__main__":
    main()