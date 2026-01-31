"""
One-off migration: MongoDB → Neon PostgreSQL.

ID strategy: deterministic UUID5 from ObjectId (idempotent re-runs).
Same ObjectId always maps to the same UUID, so re-running does not create duplicates.

Usage:
  cd apps/backend
  python -m jobs.migrate_mongo_to_postgres              # run migration
  python -m jobs.migrate_mongo_to_postgres --dry-run   # no writes, only read Mongo and log
  python -m jobs.migrate_mongo_to_postgres --batch-size 200 --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from common.config import get_settings
from db.models import (
    Availability,
    BuilderBid,
    BuilderProfile,
    BuilderService,
    ChatHistory,
    Property,
    User,
    UserProject,
    Visit,
)

# ---------------------------------------------------------------------------
# ID strategy: deterministic UUID5 from ObjectId (idempotent)
# ---------------------------------------------------------------------------

MIGRATION_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "proppal.migration")


def oid_to_uuid(val: Any) -> Optional[str]:
    """
    Map MongoDB ObjectId (or legacy ID string) to a deterministic UUID string.
    Idempotent: same input always yields same UUID.
    """
    if val is None:
        return None
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        try:
            uuid.UUID(s)
            return s
        except ValueError:
            pass
        return str(uuid.uuid5(MIGRATION_NAMESPACE, s))
    if hasattr(val, "hex"):
        return str(uuid.uuid5(MIGRATION_NAMESPACE, val.hex))
    return str(uuid.uuid5(MIGRATION_NAMESPACE, str(val)))


def to_ts(val: Any) -> Optional[datetime]:
    """Normalize to timezone-aware datetime for Postgres (UTC if naive)."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    return None


def to_jsonb(val: Any) -> Any:
    """For JSONB: list/dict with nested datetimes serialized; other serializable or None."""
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    if isinstance(val, list):
        return [to_jsonb(x) for x in val]
    if isinstance(val, dict):
        return {k: to_jsonb(v) for k, v in val.items()}
    return val


# ---------------------------------------------------------------------------
# Mongo doc → Postgres row mappers (order matches FK dependencies)
# ---------------------------------------------------------------------------


def map_user(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": oid_to_uuid(doc.get("_id")),
        "name": doc.get("name") or "",
        "email": doc.get("email") or "",
        "phone": doc.get("phone"),
        "role": doc.get("role") or "buyer",
        "profile_image": doc.get("profile_image"),
        "clerk_id": doc.get("clerk_id"),
        "password_hash": doc.get("password_hash"),
        "deleted_at": to_ts(doc.get("deleted_at")),
        "created_at": to_ts(doc.get("created_at")) or datetime.now(timezone.utc),
        "updated_at": to_ts(doc.get("updated_at")) or datetime.now(timezone.utc),
    }


def map_property(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": oid_to_uuid(doc.get("_id")),
        "seller_id": oid_to_uuid(doc.get("seller_id")),
        "title": doc.get("title") or "",
        "description": doc.get("description") or "",
        "price": float(doc.get("price") or 0),
        "property_type": doc.get("property_type") or "house",
        "area_sqft": float(doc.get("area_sqft") or 0),
        "bedrooms": int(doc.get("bedrooms") or 0),
        "bathrooms": int(doc.get("bathrooms") or 0),
        "floors": int(doc.get("floors") or 1),
        "city": doc.get("city") or "",
        "area": doc.get("area") or "",
        "lng": float(doc["lng"]) if doc.get("lng") is not None else None,
        "lat": float(doc["lat"]) if doc.get("lat") is not None else None,
        "images": doc.get("images") if isinstance(doc.get("images"), list) else None,
        "metadata_": to_jsonb(doc.get("metadata")),
        "external_id": doc.get("external_id"),
        "source": doc.get("source"),
        "source_url": doc.get("source_url"),
        "date_added": to_ts(doc.get("date_added")),
        "last_indexed_at": to_ts(doc.get("last_indexed_at")),
        "created_at": to_ts(doc.get("created_at")) or datetime.now(timezone.utc),
        "updated_at": to_ts(doc.get("updated_at")) or datetime.now(timezone.utc),
    }


def map_builder_profile(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": oid_to_uuid(doc.get("_id")),
        "user_id": oid_to_uuid(doc.get("user_id")),
        "company_name": doc.get("company_name") or "",
        "specialization": doc.get("specialization") if isinstance(doc.get("specialization"), list) else [],
        "experience_years": int(doc.get("experience_years") or 0),
        "portfolio_images": doc.get("portfolio_images") if isinstance(doc.get("portfolio_images"), list) else None,
        "rating": float(doc["rating"]) if doc.get("rating") is not None else None,
        "about": doc.get("about"),
        "founded_year": int(doc["founded_year"]) if doc.get("founded_year") is not None else None,
        "location": to_jsonb(doc.get("location")),
        "created_at": to_ts(doc.get("created_at")) or datetime.now(timezone.utc),
        "updated_at": to_ts(doc.get("updated_at")) or datetime.now(timezone.utc),
    }


def map_builder_service(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": oid_to_uuid(doc.get("_id")),
        "builder_id": oid_to_uuid(doc.get("builder_id")),
        "title": doc.get("title") or "",
        "description": doc.get("description") or "",
        "category": doc.get("category") or "",
        "base_price": float(doc.get("base_price") or 0),
        "price_unit": doc.get("price_unit") or "fixed",
        "estimated_duration": doc.get("estimated_duration"),
        "service_features": doc.get("service_features") if isinstance(doc.get("service_features"), list) else None,
        "service_images": doc.get("service_images") if isinstance(doc.get("service_images"), list) else None,
        "created_at": to_ts(doc.get("created_at")) or datetime.now(timezone.utc),
        "updated_at": to_ts(doc.get("updated_at")) or datetime.now(timezone.utc),
    }


def map_user_project(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": oid_to_uuid(doc.get("_id")),
        "user_id": oid_to_uuid(doc.get("user_id")),
        "property_id": oid_to_uuid(doc.get("property_id")),
        "title": doc.get("title") or "",
        "description": doc.get("description") or "",
        "project_type": doc.get("project_type") or "",
        "budget_min": float(doc.get("budget_min") or 0),
        "budget_max": float(doc.get("budget_max") or 0),
        "location": doc.get("location") or "",
        "status": doc.get("status") or "open",
        "created_at": to_ts(doc.get("created_at")) or datetime.now(timezone.utc),
        "updated_at": to_ts(doc.get("updated_at")) or datetime.now(timezone.utc),
    }


def map_builder_bid(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": oid_to_uuid(doc.get("_id")),
        "project_id": oid_to_uuid(doc.get("project_id")),
        "builder_id": oid_to_uuid(doc.get("builder_id")),
        "proposal_title": doc.get("proposal_title") or "",
        "proposal_details": doc.get("proposal_details") or "",
        "estimated_cost": float(doc.get("estimated_cost") or 0),
        "estimated_duration": doc.get("estimated_duration") or "",
        "attachments": doc.get("attachments") if isinstance(doc.get("attachments"), list) else [],
        "status": doc.get("status") or "pending",
        "created_at": to_ts(doc.get("created_at")) or datetime.now(timezone.utc),
        "updated_at": to_ts(doc.get("updated_at")) or datetime.now(timezone.utc),
    }


def map_chat_history(doc: Dict[str, Any]) -> Dict[str, Any]:
    messages = doc.get("messages")
    if not isinstance(messages, list):
        messages = []
    return {
        "id": oid_to_uuid(doc.get("_id")),
        "user_id": oid_to_uuid(doc.get("user_id")),
        "session_id": doc.get("session_id"),
        "messages": to_jsonb(messages),
        "created_at": to_ts(doc.get("created_at")) or datetime.now(timezone.utc),
        "updated_at": to_ts(doc.get("updated_at")) or datetime.now(timezone.utc),
    }


def map_availability(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": oid_to_uuid(doc.get("_id")),
        "property_id": oid_to_uuid(doc.get("property_id")),
        "seller_id": oid_to_uuid(doc.get("seller_id")),
        "slots": to_jsonb(doc.get("slots")),
    }


def map_visit(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": oid_to_uuid(doc.get("_id")),
        "buyer_id": oid_to_uuid(doc.get("buyer_id")),
        "property_id": oid_to_uuid(doc.get("property_id")),
        "builder_id": oid_to_uuid(doc.get("builder_id")),
        "proposed_time_slots": doc.get("proposed_time_slots") if isinstance(doc.get("proposed_time_slots"), list) else [],
        "confirmed_time": to_ts(doc.get("confirmed_time")),
        "status": doc.get("status") or "pending",
        "agent_notes": doc.get("agent_notes"),
        "created_at": to_ts(doc.get("created_at")) or datetime.now(timezone.utc),
        "updated_at": to_ts(doc.get("updated_at")) or datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# Migration runner
# ---------------------------------------------------------------------------


async def fetch_ids(session: AsyncSession, model: type) -> set:
    """Return set of all id strings in the given Postgres table (for FK validation)."""
    result = await session.execute(select(model.id))
    return {str(r) for r in result.scalars().all()}


async def migrate_collection(
    mongo_db: Any,
    pg_session: AsyncSession,
    collection_name: str,
    model: type,
    mapper: Callable[[Dict[str, Any]], Dict[str, Any]],
    batch_size: int,
    dry_run: bool,
    log: logging.Logger,
    fk_filter: Optional[Callable[[Dict[str, Any]], bool]] = None,
) -> int:
    """
    Read from MongoDB, map rows, batch insert into Postgres.
    If fk_filter is set, skip rows for which fk_filter(row) is False (avoids FK violations from orphan refs).
    Returns count inserted.
    """
    coll = mongo_db[collection_name]
    total = 0
    skipped_fk = 0
    batch: List[Dict[str, Any]] = []
    cursor = coll.find({})
    async for doc in cursor:
        try:
            row = mapper(doc)
            if row.get("id") is None:
                log.warning("Skipping %s doc with no id: %s", collection_name, doc.get("_id"))
                continue
            if fk_filter is not None and not fk_filter(row):
                skipped_fk += 1
                if skipped_fk <= 5:
                    log.warning(
                        "Skipping %s doc id=%s (FK not present in Postgres)",
                        collection_name,
                        row.get("id"),
                    )
                continue
            batch.append(row)
            if len(batch) >= batch_size:
                if not dry_run:
                    stmt = pg_insert(model).on_conflict_do_nothing(index_elements=["id"])
                    await pg_session.execute(stmt, batch)
                    await pg_session.commit()
                total += len(batch)
                log.info("%s: inserted batch of %d (total %d)", collection_name, len(batch), total)
                batch = []
        except Exception as e:
            log.exception("Error mapping/inserting doc from %s: %s", collection_name, e)
            raise
    if batch:
        if not dry_run:
            stmt = pg_insert(model).on_conflict_do_nothing(index_elements=["id"])
            await pg_session.execute(stmt, batch)
            await pg_session.commit()
        total += len(batch)
        log.info("%s: inserted final batch of %d (total %d)", collection_name, len(batch), total)
    if skipped_fk:
        log.info("%s: skipped %d rows (missing FK in Postgres)", collection_name, skipped_fk)
    return total


async def run(
    dry_run: bool,
    batch_size: int,
    verbose: bool,
) -> None:
    settings = get_settings()
    log = logging.getLogger("migrate_mongo_to_postgres")
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    if not log.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        log.addHandler(h)

    postgres_url = settings.get_postgres_url()
    if not postgres_url:
        log.error("DATABASE_URL or POSTGRES_URL must be set.")
        sys.exit(1)
    if not postgres_url.startswith("postgresql+asyncpg://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if not postgres_url.startswith("postgresql+asyncpg://"):
        postgres_url = "postgresql+asyncpg://" + (postgres_url.split("://", 1)[-1] if "://" in postgres_url else postgres_url)

    mongo_url = os.environ.get("MONGODB_URL", "").strip()
    mongo_db_name = os.environ.get("MONGODB_DB_NAME", "proppal").strip() or "proppal"
    if not mongo_url:
        log.error("MONGODB_URL must be set in the environment for this one-off migration script.")
        sys.exit(1)

    log.info("MongoDB: %s", mongo_url[:50] + "...")
    log.info("Postgres: %s", postgres_url.split("@")[-1] if "@" in postgres_url else postgres_url)
    log.info("Dry run: %s | Batch size: %d", dry_run, batch_size)

    # MongoDB (read-only) - uses env vars (not in app config after Phase 6)
    mongo_client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=10000)
    try:
        await mongo_client.admin.command("ping")
    except Exception as e:
        log.error("MongoDB ping failed: %s", e)
        sys.exit(1)
    mongo_db = mongo_client[mongo_db_name]

    # Postgres
    engine = create_async_engine(postgres_url, pool_pre_ping=True, echo=verbose)
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )

    total_all = 0
    async with async_session_factory() as session:
        steps = [
            ("users", User, map_user, None),
            ("properties", Property, map_property, None),  # filter set after users
            ("builder_profiles", BuilderProfile, map_builder_profile, None),
            ("builder_services", BuilderService, map_builder_service, None),
            ("user_projects", UserProject, map_user_project, None),
            ("builder_bids", BuilderBid, map_builder_bid, None),
            ("chat_histories", ChatHistory, map_chat_history, None),
            ("availability", Availability, map_availability, None),
            ("visits", Visit, map_visit, None),
        ]
        valid_user_ids: set = set()
        valid_property_ids: set = set()
        valid_builder_ids: set = set()
        valid_project_ids: set = set()

        try:
            # 1. Users (no FK)
            n = await migrate_collection(
                mongo_db, session, "users", User, map_user, batch_size, dry_run, log
            )
            total_all += n
            if not dry_run:
                valid_user_ids = await fetch_ids(session, User)
            else:
                # Dry run: build valid_user_ids from Mongo users we would have inserted
                async for doc in mongo_db["users"].find({}, {"_id": 1}):
                    u = oid_to_uuid(doc.get("_id"))
                    if u:
                        valid_user_ids.add(u)

            # 2. Properties (seller_id must exist in users)
            n = await migrate_collection(
                mongo_db,
                session,
                "properties",
                Property,
                map_property,
                batch_size,
                dry_run,
                log,
                fk_filter=lambda row: (row.get("seller_id") or "") in valid_user_ids,
            )
            total_all += n
            if not dry_run:
                valid_property_ids = await fetch_ids(session, Property)
            else:
                async for doc in mongo_db["properties"].find({}, {"_id", "seller_id"}):
                    sid = oid_to_uuid(doc.get("seller_id"))
                    if sid and sid in valid_user_ids:
                        pid = oid_to_uuid(doc.get("_id"))
                        if pid:
                            valid_property_ids.add(pid)

            # 3. Builder profiles (user_id must exist in users)
            n = await migrate_collection(
                mongo_db,
                session,
                "builder_profiles",
                BuilderProfile,
                map_builder_profile,
                batch_size,
                dry_run,
                log,
                fk_filter=lambda row: (row.get("user_id") or "") in valid_user_ids,
            )
            total_all += n
            if not dry_run:
                valid_builder_ids = await fetch_ids(session, BuilderProfile)
            else:
                async for doc in mongo_db["builder_profiles"].find({}, {"_id", "user_id"}):
                    uid = oid_to_uuid(doc.get("user_id"))
                    if uid and uid in valid_user_ids:
                        bid = oid_to_uuid(doc.get("_id"))
                        if bid:
                            valid_builder_ids.add(bid)

            # 4. Builder services (builder_id must exist in builder_profiles)
            n = await migrate_collection(
                mongo_db,
                session,
                "builder_services",
                BuilderService,
                map_builder_service,
                batch_size,
                dry_run,
                log,
                fk_filter=lambda row: (row.get("builder_id") or "") in valid_builder_ids,
            )
            total_all += n

            # 5. User projects (user_id in users; property_id optional but must exist if set)
            n = await migrate_collection(
                mongo_db,
                session,
                "user_projects",
                UserProject,
                map_user_project,
                batch_size,
                dry_run,
                log,
                fk_filter=lambda row: (row.get("user_id") or "") in valid_user_ids
                and (
                    row.get("property_id") is None
                    or (row.get("property_id") or "") in valid_property_ids
                ),
            )
            total_all += n
            if not dry_run:
                valid_project_ids = await fetch_ids(session, UserProject)
            else:
                async for doc in mongo_db["user_projects"].find({}, {"_id", "user_id", "property_id"}):
                    uid = oid_to_uuid(doc.get("user_id"))
                    pid = oid_to_uuid(doc.get("property_id"))
                    if uid and uid in valid_user_ids and (not pid or pid in valid_property_ids):
                        proj_id = oid_to_uuid(doc.get("_id"))
                        if proj_id:
                            valid_project_ids.add(proj_id)

            # 6. Builder bids (project_id, builder_id must exist)
            n = await migrate_collection(
                mongo_db,
                session,
                "builder_bids",
                BuilderBid,
                map_builder_bid,
                batch_size,
                dry_run,
                log,
                fk_filter=lambda row: (row.get("project_id") or "") in valid_project_ids
                and (row.get("builder_id") or "") in valid_builder_ids,
            )
            total_all += n

            # 7. Chat histories (user_id must exist)
            n = await migrate_collection(
                mongo_db,
                session,
                "chat_histories",
                ChatHistory,
                map_chat_history,
                batch_size,
                dry_run,
                log,
                fk_filter=lambda row: (row.get("user_id") or "") in valid_user_ids,
            )
            total_all += n

            # 8. Availability (property_id, seller_id optional but must exist if set)
            n = await migrate_collection(
                mongo_db,
                session,
                "availability",
                Availability,
                map_availability,
                batch_size,
                dry_run,
                log,
                fk_filter=lambda row: (
                    row.get("property_id") is None
                    or (row.get("property_id") or "") in valid_property_ids
                )
                and (
                    row.get("seller_id") is None
                    or (row.get("seller_id") or "") in valid_user_ids
                ),
            )
            total_all += n

            # 9. Visits (buyer_id must exist; property_id, builder_id optional)
            n = await migrate_collection(
                mongo_db,
                session,
                "visits",
                Visit,
                map_visit,
                batch_size,
                dry_run,
                log,
                fk_filter=lambda row: (row.get("buyer_id") or "") in valid_user_ids
                and (
                    row.get("property_id") is None
                    or (row.get("property_id") or "") in valid_property_ids
                )
                and (
                    row.get("builder_id") is None
                    or (row.get("builder_id") or "") in valid_builder_ids
                ),
            )
            total_all += n
        except Exception as e:
            log.exception("Migration failed: %s", e)
            await session.rollback()
    await engine.dispose()
    mongo_client.close()

    log.info("Done. Total rows migrated: %d", total_all)
    if dry_run:
        log.info("(Dry run: no data was written to Postgres.)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate MongoDB collections to Neon PostgreSQL (deterministic UUID5).")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Postgres; only read from MongoDB and log.")
    parser.add_argument("--batch-size", type=int, default=100, help="Insert batch size (default 100).")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging.")
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run, batch_size=args.batch_size, verbose=args.verbose))


if __name__ == "__main__":
    main()
