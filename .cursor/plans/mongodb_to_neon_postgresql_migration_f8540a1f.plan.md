---
name: MongoDB to Neon PostgreSQL Migration
overview: "Complete migration from MongoDB (Motor) to Neon PostgreSQL: add Neon and async PostgreSQL stack, define schema and migrations, replace the DB layer and all MongoDB usages with SQLAlchemy/asyncpg, adapt Qdrant for UUIDs, run data migration, then remove MongoDB. Uses Neon instead of Supabase for hosted Postgres."
todos: []
isProject: false
---

# MongoDB to Neon PostgreSQL Migration Plan

## Why Neon

Neon is serverless PostgreSQL (neon.tech). You get a connection string that typically resolves from more networks than Supabase's direct host; free tier includes 0.5 GB storage and optional branching. No "Session vs Direct" choice; one connection string works for migrations and the app. Same stack (asyncpg, SQLAlchemy, Alembic) applies.

## Current State

- **Backend:** FastAPI in [apps/backend](apps/backend); [common/db.py](apps/backend/common/db.py) uses Motor and exposes `get_database()` / `get_db_client()`.
- **Config:** [common/config.py](apps/backend/common/config.py) has `MONGODB_URL` and `MONGODB_DB_NAME`; no `DATABASE_URL`/`POSTGRES_URL` on this branch.
- **MongoDB usage:** 21 files use `get_database()` or raw `db["collection"]` (auth, users, properties, builder, chat, search, recommendations, agents, jobs).
- **Vector search:** Qdrant stays as-is; only the source-of-truth DB moves to PostgreSQL (Neon).

## Scope

**Collections to migrate:** `users`, `properties`, `builder_profiles`, `builder_services`, `user_projects`, `builder_bids`, `chat_histories`, `availability`, `visits` (and optionally `conversations`, `property_amenities`, `query_logs` if used).

**Touch points:** [common/db.py](apps/backend/common/db.py), [common/config.py](apps/backend/common/config.py), [services/main.py](apps/backend/services/main.py), all API routers and agents that use `db`, [common/repositories/user_repository.py](apps/backend/common/repositories/user_repository.py), [services/vector_search/qdrant_service.py](apps/backend/services/vector_search/qdrant_service.py), and jobs under [jobs/](apps/backend/jobs/).

---

## Phase 1: Neon and PostgreSQL stack

- **1.1** Create a Neon project at [neon.tech](https://neon.tech). In the dashboard, create a project and copy the **connection string** (PostgreSQL URI). Add to [apps/backend/.env](apps/backend/.env): `DATABASE_URL=postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require` (or use `POSTGRES_URL`; plan uses one name consistently, e.g. `DATABASE_URL`).
- **1.2** In [apps/backend/requirements.txt](apps/backend/requirements.txt) add: `asyncpg`, `sqlalchemy[asyncio]>=2.0`, `alembic`. Keep `motor` and `pymongo` until cutover.
- **1.3** In [common/config.py](apps/backend/common/config.py) add `DATABASE_URL: str = Field(default="", description="PostgreSQL connection string (Neon).")` and optionally `POSTGRES_URL: Optional[str] = Field(default=None)` as fallback. Add a helper e.g. `get_postgres_url() -> str` that returns `DATABASE_URL or POSTGRES_URL or ""`. Do not remove MongoDB settings yet.

---

## Phase 2: PostgreSQL schema and migrations

- **2.1** In `apps/backend/` run `alembic init alembic`. Configure [alembic.ini](apps/backend/alembic.ini) and `alembic/env.py`: read the Postgres URL from app config (`get_postgres_url()`); ensure URL uses `postgresql+asyncpg://` for async; in `env.py` use `async_engine_from_config` and `connection.run_sync(do_run_migrations)` so migrations run with the async engine.
- **2.2** Create a `db` package with [apps/backend/db/models.py](apps/backend/db/models.py): single declarative `Base`, one table per collection. Use **UUID primary keys** (`PG_UUID(as_uuid=False)` with default `str(uuid.uuid4())`). Map: ObjectId refs to UUID FKs, arrays to `ARRAY(Text)` or `JSONB`, optional JSON to `JSONB`, datetimes to `TIMESTAMPTZ`. Tables: **users**, **properties** (FK seller_id), **builder_profiles** (FK user_id), **builder_services** (FK builder_id), **user_projects** (FK user_id, property_id nullable), **builder_bids** (FK project_id, builder_id), **chat_histories** (FK user_id, messages JSONB, optional session_id), **availability** (property_id, seller_id, slots JSONB), **visits** (buyer_id, property_id, builder_id nullable, etc.). Add indexes (e.g. city, price, bedrooms, created_at on properties; clerk_id, email on users).
- **2.3** Generate the first migration from the declarative models (or add a hand-written migration that creates all tables). Run `alembic upgrade head` against Neon (or, if DNS/connection fails from your PC, provide a standalone SQL file to run in Neon's SQL Editor so schema is created without outbound connection from your machine). Optionally support local Postgres (Docker) for dev when Neon is unreachable.

---

## Phase 3: Database layer and dependency injection

- **3.1** In [common/db.py](apps/backend/common/db.py) (or a new module): create async engine from `settings.get_postgres_url()` via `create_async_engine` (asyncpg). Use `async_sessionmaker(..., expire_on_commit=False)`. Add an async context manager for a session and a FastAPI dependency `get_db_session()` that yields one session per request and closes it after. Keep existing MongoDB `DatabaseClient`, `get_database()`, and `get_db_client()` until Phase 6 so both DBs can coexist during migration.
- **3.2** (Optional) Introduce a single dependency (e.g. `get_db`) that returns the Postgres session for new repository code.

---

## Phase 4: Replace MongoDB usage with PostgreSQL

**Order (by dependency):** users and auth, then properties, then builder_profiles and builder_services, then user_projects and builder_bids (if present), then chat_histories, search, recommendations, then availability and visits (if present).

- **4.1 Repositories**  
  - [common/repositories/user_repository.py](apps/backend/common/repositories/user_repository.py): rewrite to use async SQLAlchemy session (e.g. `select(User).where(...)`, `session.add`, `session.commit`). Keep the same method names (e.g. `get_by_id`, `get_by_email`, `get_by_clerk_id`, `create`).  
  - Add or rewrite repositories for properties, builder_profiles, builder_services, user_projects, builder_bids, chat_histories, availability, visits so all use the Postgres session and return dicts or Pydantic-compatible structures with UUID string IDs.
- **4.2 API routers**  
Replace every `db["collection"]` and `get_database()` usage with the new repositories or direct session queries. Key files: [api/auth/router.py](apps/backend/api/auth/router.py), [api/properties/router.py](apps/backend/api/properties/router.py), [api/builder/router.py](apps/backend/api/builder/router.py), [api/chat/router.py](apps/backend/api/chat/router.py), [api/search/router.py](apps/backend/api/search/router.py), [api/recommendations/router.py](apps/backend/api/recommendations/router.py). Use UUID strings for `id` in request/response; validate path/query IDs as UUID and return 404 when invalid.
- **4.3 Agents and tools**  
  - [agents/listing/tools/property_search.py](apps/backend/agents/listing/tools/property_search.py): replace Motor `db["properties"].find(...)` with Postgres (session or repository). Build SQL WHERE from filters; `SELECT id FROM properties WHERE ...`; pass IDs to Qdrant; fetch full rows from Postgres by ID.  
  - [agents/listing/tools/property_creation.py](apps/backend/agents/listing/tools/property_creation.py), [agents/builder/tools/builder_search.py](apps/backend/agents/builder/tools/builder_search.py), [agents/builder/tools/builder_creation.py](apps/backend/agents/builder/tools/builder_creation.py): replace Motor with Postgres for users, properties, builder_profiles, builder_services.  
  - Booking/availability tools (if any): switch to Postgres for availability, visits, properties, users.
- **4.4 Services**  
  - [services/auth/utils.py](apps/backend/services/auth/utils.py): replace `get_database()` and `db["users"].find_one` with UserRepository or session.  
  - [services/recommendations/property_recommendations.py](apps/backend/services/recommendations/property_recommendations.py): replace all `db["..."]` with Postgres.
- **4.5 Pydantic and IDs**  
For the Postgres path use UUID for `id` and FKs in Pydantic (e.g. `uuid.UUID` or string); serialize to string in API. Add a small helper to parse UUID from path/query and 404 on invalid. Keep `PyObjectId` only for the data migration script if it still reads from MongoDB.
- **4.6 Qdrant**  
In [services/vector_search/qdrant_service.py](apps/backend/services/vector_search/qdrant_service.py): treat point ID as derived from string ID (e.g. rename `_object_id_to_qdrant_id` to `_string_id_to_qdrant_id` and accept UUID string). Store in Qdrant payload `property_id` (or `builder_id` / `service_id`) as UUID string. App fetches full rows from Postgres by that UUID after vector search.

---

## Phase 5: Data migration (MongoDB to Neon)

- **5.1** Choose ID strategy: (a) new UUIDs per row with a mapping file/table `mongo_id -> uuid`, or (b) deterministic UUID from ObjectId (e.g. UUID5) for idempotent re-runs.
- **5.2** One-off script (e.g. [jobs/migrate_mongo_to_postgres.py](apps/backend/jobs/migrate_mongo_to_postgres.py)): connect to MongoDB (Motor, read-only) and to Neon (asyncpg/SQLAlchemy). Migrate in order: users, properties, builder_profiles, builder_services, user_projects, builder_bids, chat_histories, availability, visits. Map ObjectId to UUID, map types (datetime, array, nested doc to JSONB), batch insert into Postgres. Support dry-run and logging.
- **5.3** After migration: re-run embedding backfills so Qdrant payloads use the new UUIDs; property/builder search then fetches by UUID from Postgres.
  - `jobs/backfill_property_embeddings.py`: reads from Postgres (PropertyRepository), upserts to Qdrant with `property_id` = UUID string.
  - `jobs/backfill_builder_profile_embeddings.py`: reads from Postgres (BuilderProfileRepository), upserts to Qdrant with `profile_id` = UUID string.
  - `jobs/backfill_builder_service_embeddings.py`: reads from Postgres (BuilderServiceRepository), upserts to Qdrant with `service_id` = UUID string.
  - `jobs/backfill_all_embeddings_from_postgres.py`: runs all three backfills in sequence. Usage: `python -m jobs.backfill_all_embeddings_from_postgres [--batch-size 100] [--limit N]`.

---

## Phase 6: Lifespan, health check, and cleanup

- **6.1** In [services/main.py](apps/backend/services/main.py): remove Motor client init/shutdown from lifespan; init Postgres async engine (or ensure it is created on first use) and dispose on shutdown. `get_db_session()` should use this engine/session factory.
- **6.2** Replace `/health/database`: run a simple Postgres check (e.g. `SELECT 1`) instead of MongoDB ping; return status and DB name/version from the Postgres URL.
- **6.3** Remove from config: `MONGODB_URL`, `MONGODB_DB_NAME`, `mongo_uri`. Keep only `DATABASE_URL` (and optional `POSTGRES_URL`). Remove `motor` and `pymongo` from [requirements.txt](apps/backend/requirements.txt). Refactor [common/db.py](apps/backend/common/db.py): remove MongoDB code; keep only Postgres engine and `get_db_session()`.
- **6.4** Update [jobs/](apps/backend/jobs/) (backfill_*, property_import, migrate_to_qdrant, etc.) to read/write from Postgres and write UUIDs to Qdrant. Update [tests/conftest.py](apps/backend/tests/conftest.py) to use a Postgres test DB (Neon branch or local Postgres), run Alembic in fixture, and use UUIDs in fixtures/assertions.

---

## Phase 7: Documentation and deploy

- Update [README.md](README.md) and any quick-start doc: remove MongoDB setup; add Neon setup (create project at neon.tech, set `DATABASE_URL` in `.env`, run `alembic upgrade head`). Add or update `.env.example` with `DATABASE_URL=` (Neon connection string) and no MongoDB vars.
- Update [infra/docker/docker-compose.yml](infra/docker/docker-compose.yml): ensure backend env has `DATABASE_URL` (Neon or local Postgres for dev). Remove or keep MongoDB service only if still needed for a temporary dual-run; otherwise remove.

---

## Neon-specific notes

- **Connection string:** Neon provides a URI like `postgresql://user:password@ep-xxx-xxx.region.aws.neon.tech/neondb?sslmode=require`. Use it as-is; normalize to `postgresql+asyncpg://...` in code for SQLAlchemy async.
- **Cold start:** Free tier can scale to zero; first request after idle may take a few seconds. For demos, consider keeping the project active or using a small paid tier.
- **Branching (optional):** Neon supports branches; you can create a branch for staging or per-feature DBs and point `DATABASE_URL` at the branch.
- **Local dev:** If Neon is unreachable from your PC (e.g. DNS), use a local Postgres (Docker) and set `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/proppal` for development; use Neon URL for production or when network allows.

---

## Architecture after migration

```mermaid
flowchart LR
  subgraph clients [Clients]
    Web[Web App]
    Mobile[Mobile]
  end
  subgraph backend [Backend]
    FastAPI[FastAPI]
  end
  subgraph data [Data]
    Neon[(Neon PostgreSQL)]
    Qdrant[Qdrant]
  end
  Web --> FastAPI
  Mobile --> FastAPI
  FastAPI -->|CRUD filters joins| Neon
  FastAPI -->|Vector search| Qdrant
  FastAPI -->|Fetch by ID from payload| Neon
```



All relational data lives in Neon; Qdrant only for vectors and payload IDs (UUID string). Same hybrid flow: filter in Postgres, get IDs, optional vector search in Qdrant, fetch full rows from Postgres by ID.

---

## Suggested implementation order (todos)

1. **Phase 1:** Neon project, `DATABASE_URL` in .env, add asyncpg + SQLAlchemy + Alembic to requirements; add `DATABASE_URL` (and optional `POSTGRES_URL`) + `get_postgres_url()` to config.
2. **Phase 2:** Alembic init, SQLAlchemy declarative models in `db/models.py`, first migration, run on Neon (or standalone SQL + local Postgres fallback for dev).
3. **Phase 3:** Async engine and session in common (db.py or new module), `get_db_session()` dependency.
4. **Phase 4:** Repositories and routers (users/auth first, then properties, builder, chat, search, recommendations, booking); then agents and services; Pydantic IDs and Qdrant ID handling.
5. **Phase 5:** Data migration script; run; re-backfill Qdrant with UUID payloads.
6. **Phase 6:** Lifespan and health check Postgres-only; remove Motor/config; update jobs and tests.
7. **Phase 7:** Docs (Neon setup, no MongoDB), docker-compose, .env.example.

