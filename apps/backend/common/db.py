"""
Database connection management for PropPal backend services.

PostgreSQL (Neon): async SQLAlchemy engine and session; use get_db_session() for API and repositories.
Engine/session are cached per event loop so tools run in a thread (e.g. LangGraph with asyncio.run)
get their own engine and avoid "Future attached to a different loop".
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings

# ---------------------------------------------------------------------------
# PostgreSQL (Neon) async engine and session (per event loop)
# ---------------------------------------------------------------------------

_engines_by_loop: Dict[int, Any] = {}
_factories_by_loop: Dict[int, async_sessionmaker[AsyncSession]] = {}


def _make_async_url(url: str) -> str:
    if not url or not url.strip():
        raise ValueError("DATABASE_URL or POSTGRES_URL must be set for PostgreSQL.")
    url = url.strip()
    if url.startswith("postgresql://"):
        return _normalize_asyncpg_params(url.replace("postgresql://", "postgresql+asyncpg://", 1))
    if url.startswith("postgresql+asyncpg://"):
        return _normalize_asyncpg_params(url)
    return _normalize_asyncpg_params(
        "postgresql+asyncpg://" + (url.split("://", 1)[-1] if "://" in url else url)
    )


def _normalize_asyncpg_params(url: str) -> str:
    """Convert sslmode query param to asyncpg-compatible ssl flag."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    
    # Remove channel_binding if present
    query.pop("channel_binding", None)
    
    # Extract existing sslmode
    sslmode = query.pop("sslmode", None)
    
    if sslmode and "ssl" not in query:
        # asyncpg expects specific strings like 'require' or 'disable', NOT 'true' or 'false'
        if sslmode.lower() in {"require", "verify-full", "verify-ca"}:
            query["ssl"] = "require"
        elif sslmode.lower() in {"disable", "allow", "prefer"}:
            query["ssl"] = "disable"
        else:
            query["ssl"] = sslmode
            
    new_query = urlencode(query)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

def get_async_session_factory(loop: Optional[asyncio.AbstractEventLoop] = None) -> async_sessionmaker[AsyncSession]:
    """
    Return async session factory for the given event loop (or current loop if None).
    Call from async code and pass asyncio.get_running_loop() when you need the current loop.
    Caches engine and factory per loop so threads using asyncio.run() get their own engine.
    """
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError("get_async_session_factory(loop=...) must be called with a loop or from async code")
    key = id(loop)
    if key in _factories_by_loop:
        return _factories_by_loop[key]
    settings = get_settings()
    url = _make_async_url(settings.get_postgres_url())
    engine = create_async_engine(url, pool_pre_ping=True, echo=False)
    _engines_by_loop[key] = engine
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    _factories_by_loop[key] = factory
    return factory


async def dispose_async_engine() -> None:
    """Dispose all cached async engines (call on app shutdown)."""
    global _engines_by_loop, _factories_by_loop
    for key, engine in list(_engines_by_loop.items()):
        try:
            await engine.dispose()
        except Exception:
            pass
    _engines_by_loop.clear()
    _factories_by_loop.clear()


@asynccontextmanager
async def get_db_session_ctx() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager yielding a single Postgres session (uses engine for current event loop)."""
    loop = asyncio.get_running_loop()
    factory = get_async_session_factory(loop)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield one Postgres session per request, close after."""
    async with get_db_session_ctx() as session:
        yield session


# Alias for repository code: use Depends(get_db) or Depends(get_db_session).
get_db = get_db_session
