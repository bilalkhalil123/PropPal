#!/usr/bin/env python3
"""
Seed builder profiles and builder services from data/builder_profiles_extended.json
and data/builder_services_extended.json into:
  1. PostgreSQL  (builder_profiles + builder_services tables)
  2. Qdrant      (builder_profiles + builder_services collections)

The JSON files use MongoDB hex _id values. This script generates fresh UUIDs for
every row and keeps an internal mapping (mongo_id -> new_uuid) so that the
builder_services.builder_id FK always points to the correct builder_profile.

Since BuilderProfile has a NOT NULL FK to users.id, a stub User row is created
for each builder (role="builder") with a generated UUID. If a user with the same
UUID already exists it is skipped (idempotent).

Usage (from repo root or apps/backend):
  cd apps/backend && python scripts/seed_builders.py
  cd apps/backend && python scripts/seed_builders.py --skip-vectors   # DB only
  cd apps/backend && python scripts/seed_builders.py --batch-size 32  # tune batch
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional

# ── Import root setup ─────────────────────────────────────────────────────────
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent.parent  # PropPal/
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

_DATA_DIR = _REPO_ROOT / "data"
_PROFILES_FILE = _DATA_DIR / "builder_profiles_extended.json"
_SERVICES_FILE = _DATA_DIR / "builder_services_extended.json"


# ── Embedding text helpers ────────────────────────────────────────────────────

def _profile_text(p: dict) -> str:
    """Compose a rich text string from a builder profile for embedding."""
    parts = [p.get("company_name", "")]
    specs = p.get("specialization") or []
    if specs:
        parts.append("Specializations: " + ", ".join(specs))
    about = p.get("about") or ""
    if about:
        parts.append(about)
    loc = p.get("location") or {}
    city = loc.get("city") or ""
    if city:
        parts.append(f"Located in {city}")
    exp = p.get("experience_years")
    if exp is not None:
        parts.append(f"{exp} years of experience")
    return ". ".join(filter(None, parts))


def _service_text(s: dict) -> str:
    """Compose a rich text string from a builder service for embedding."""
    parts = [
        s.get("title", ""),
        s.get("description", ""),
        f"Category: {s.get('category', '')}",
    ]
    feats = s.get("service_features") or []
    if feats:
        parts.append("Features: " + ", ".join(feats))
    price_unit = s.get("price_unit") or ""
    base_price = s.get("base_price")
    if base_price is not None and price_unit:
        parts.append(f"Price: {base_price} {price_unit}")
    duration = s.get("estimated_duration") or ""
    if duration:
        parts.append(f"Duration: {duration}")
    return ". ".join(filter(None, parts))


# ── Main seeding logic ────────────────────────────────────────────────────────

async def _run(args: argparse.Namespace) -> None:
    from datetime import datetime, timezone

    from sqlalchemy import select

    from common.db import get_db_session_ctx
    from db.models import BuilderProfile as BPModel
    from db.models import BuilderService as BSModel
    from db.models import User as UserModel

    # Lazy-import vectorization helpers only when needed
    if not args.skip_vectors:
        from common.qdrant import ensure_collections_exist
        from services.embeddings.service import embed_batch
        from services.vector_search.qdrant_service import (
            upsert_builder_profile_embeddings_batch,
            upsert_builder_service_embeddings_batch,
        )

    # ── Load JSON ─────────────────────────────────────────────────────────────
    print(f"[SEED] Loading profiles from {_PROFILES_FILE} …")
    profiles_raw: List[dict] = json.loads(_PROFILES_FILE.read_text(encoding="utf-8"))
    print(f"[SEED] Loaded {len(profiles_raw)} builder profiles")

    print(f"[SEED] Loading services from {_SERVICES_FILE} …")
    services_raw: List[dict] = json.loads(_SERVICES_FILE.read_text(encoding="utf-8"))
    print(f"[SEED] Loaded {len(services_raw)} builder services")

    # ── Ensure Qdrant collections exist ───────────────────────────────────────
    if not args.skip_vectors:
        print("[SEED] Ensuring Qdrant collections exist …")
        await ensure_collections_exist()

    now = datetime.now(timezone.utc)

    # ── Maps for FK wiring: mongo_hex_id -> new_uuid ──────────────────────────
    # mongo_id  -> { "pg_user_id": uuid, "pg_profile_id": uuid }
    mongo_to_uuids: Dict[str, dict] = {}

    for p in profiles_raw:
        mongo_id = p["_id"]
        pg_user_id = p.get("user_id") or str(uuid.uuid4())
        pg_profile_id = str(uuid.uuid4())
        mongo_to_uuids[mongo_id] = {
            "pg_user_id": pg_user_id,
            "pg_profile_id": pg_profile_id,
        }

    # ── Phase 1: Insert Users + BuilderProfiles into Postgres ─────────────────
    profiles_inserted = 0
    profiles_skipped = 0

    async with get_db_session_ctx() as session:
        for p in profiles_raw:
            mongo_id = p["_id"]
            pg_user_id = mongo_to_uuids[mongo_id]["pg_user_id"]
            pg_profile_id = mongo_to_uuids[mongo_id]["pg_profile_id"]

            # --- Upsert stub User -------------------------------------------------
            existing_user = await session.get(UserModel, pg_user_id)
            if existing_user is None:
                company = p.get("company_name", "Builder")
                stub_user = UserModel(
                    id=pg_user_id,
                    name=company,
                    email=f"builder-{pg_user_id}@proppal.seed",
                    role="builder",
                    created_at=now,
                    updated_at=now,
                )
                session.add(stub_user)
                await session.flush()

            # --- Upsert BuilderProfile --------------------------------------------
            existing_profile = await session.get(BPModel, pg_profile_id)
            if existing_profile is not None:
                profiles_skipped += 1
                continue  # already seeded this run (shouldn't normally happen)

            # Check by user_id (unique constraint) to handle reruns
            q = select(BPModel).where(BPModel.user_id == pg_user_id)
            res = await session.execute(q)
            existing_by_user = res.scalar_one_or_none()
            if existing_by_user is not None:
                # Update maps to use the already-persisted profile id
                mongo_to_uuids[mongo_id]["pg_profile_id"] = existing_by_user.id
                profiles_skipped += 1
                continue

            loc = p.get("location") or {}
            profile_row = BPModel(
                id=pg_profile_id,
                user_id=pg_user_id,
                company_name=p.get("company_name", ""),
                specialization=p.get("specialization") or [],
                experience_years=int(p.get("experience_years") or 0),
                portfolio_images=p.get("portfolio_images") or [],
                rating=float(p["rating"]) if p.get("rating") is not None else None,
                about=p.get("about"),
                founded_year=p.get("founded_year"),
                location=loc if loc else None,
                created_at=now,
                updated_at=now,
            )
            session.add(profile_row)
            profiles_inserted += 1

        # Flush so that profile PKs exist before services reference them
        await session.flush()

    print(
        f"[SEED] BuilderProfiles — inserted: {profiles_inserted}, skipped: {profiles_skipped}"
    )

    # ── Phase 2: Insert BuilderServices into Postgres ─────────────────────────
    services_inserted = 0
    services_skipped = 0
    # Keep track of (pg_service_id, service_raw_dict) for vectorization later
    service_records: List[tuple] = []  # (pg_service_id, raw_dict)

    async with get_db_session_ctx() as session:
        for s in services_raw:
            mongo_builder_id = s.get("builder_id", "")
            if mongo_builder_id not in mongo_to_uuids:
                print(
                    f"[WARN] Service '{s.get('title')}' references unknown builder_id "
                    f"'{mongo_builder_id}' — skipping."
                )
                services_skipped += 1
                continue

            pg_profile_id = mongo_to_uuids[mongo_builder_id]["pg_profile_id"]
            pg_service_id = str(uuid.uuid4())

            service_row = BSModel(
                id=pg_service_id,
                builder_id=pg_profile_id,
                title=s.get("title", ""),
                description=s.get("description", ""),
                category=s.get("category", ""),
                base_price=float(s.get("base_price") or 0),
                price_unit=s.get("price_unit", ""),
                estimated_duration=s.get("estimated_duration"),
                service_features=s.get("service_features") or [],
                service_images=s.get("service_images") or [],
                created_at=now,
                updated_at=now,
            )
            session.add(service_row)
            service_records.append((pg_service_id, s))
            services_inserted += 1

    print(
        f"[SEED] BuilderServices — inserted: {services_inserted}, skipped: {services_skipped}"
    )

    # ── Phase 3: Vectorize and upsert into Qdrant ─────────────────────────────
    if args.skip_vectors:
        print("[SEED] --skip-vectors flag set; skipping Qdrant upserts.")
        return

    batch_size = args.batch_size

    # --- Builder Profiles embeddings -------------------------------------------
    print(f"[SEED] Vectorizing {len(profiles_raw)} builder profiles (batch={batch_size}) …")
    profile_items_to_upsert: List[tuple] = []

    # Build profile list for vectorization (only inserted ones)
    profiles_for_vec = [
        p for p in profiles_raw
        if mongo_to_uuids[p["_id"]]["pg_profile_id"] != p.get("_id")  # always true
    ]

    for i in range(0, len(profiles_raw), batch_size):
        batch = profiles_raw[i : i + batch_size]
        texts = [_profile_text(p) for p in batch]
        vectors = embed_batch(texts)
        for p, vec in zip(batch, vectors):
            mongo_id = p["_id"]
            pg_profile_id = mongo_to_uuids[mongo_id]["pg_profile_id"]
            loc = p.get("location") or {}
            metadata = {
                "company_name": p.get("company_name", ""),
                "specialization": p.get("specialization") or [],
                "city": loc.get("city", ""),
                "rating": p.get("rating"),
                "experience_years": p.get("experience_years"),
            }
            profile_items_to_upsert.append((pg_profile_id, vec, metadata))
        print(f"  … embedded profiles {i + 1}–{min(i + batch_size, len(profiles_raw))}")

    await upsert_builder_profile_embeddings_batch(profile_items_to_upsert)
    print(f"[SEED] Upserted {len(profile_items_to_upsert)} profile vectors into Qdrant OK")

    # --- Builder Services embeddings -------------------------------------------
    print(f"[SEED] Vectorizing {len(service_records)} builder services (batch={batch_size}) …")
    service_items_to_upsert: List[tuple] = []

    for i in range(0, len(service_records), batch_size):
        batch = service_records[i : i + batch_size]
        texts = [_service_text(s_raw) for _, s_raw in batch]
        vectors = embed_batch(texts)
        for (pg_service_id, s_raw), vec in zip(batch, vectors):
            mongo_builder_id = s_raw.get("builder_id", "")
            pg_profile_id = mongo_to_uuids.get(mongo_builder_id, {}).get("pg_profile_id", "")
            metadata = {
                "title": s_raw.get("title", ""),
                "category": s_raw.get("category", ""),
                "builder_id": pg_profile_id,
                "company_name": s_raw.get("company_name", ""),
                "base_price": s_raw.get("base_price"),
                "price_unit": s_raw.get("price_unit", ""),
            }
            service_items_to_upsert.append((pg_service_id, vec, metadata))
        print(f"  … embedded services {i + 1}–{min(i + batch_size, len(service_records))}")

    await upsert_builder_service_embeddings_batch(service_items_to_upsert)
    print(f"[SEED] Upserted {len(service_items_to_upsert)} service vectors into Qdrant OK")

    print("\n[SEED] [SUCCESS] Done. Summary:")
    print(f"         Builder profiles inserted : {profiles_inserted}")
    print(f"         Builder profiles skipped  : {profiles_skipped}")
    print(f"         Builder services inserted : {services_inserted}")
    print(f"         Builder services skipped  : {services_skipped}")
    if not args.skip_vectors:
        print(f"         Profile vectors upserted : {len(profile_items_to_upsert)}")
        print(f"         Service vectors upserted : {len(service_items_to_upsert)}")


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed builder profiles + services into Postgres & Qdrant"
    )
    parser.add_argument(
        "--skip-vectors",
        action="store_true",
        default=False,
        help="Skip Qdrant vectorization (DB insert only)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Number of records to embed per API call (default: 32)",
    )
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
