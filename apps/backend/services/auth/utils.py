from __future__ import annotations

import asyncio
import time
import httpx
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

# Add parent directory to path to import common and models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.config import get_settings
from common.repositories.user_repository import UserRepository, get_user_repository
from models.users import User

bearer_scheme = HTTPBearer(auto_error=False)

# JWKS cache: populated once and refreshed after JWKS_TTL_SECONDS.
# An asyncio.Lock prevents concurrent stampedes on cache miss.
_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0.0
_jwks_lock = asyncio.Lock()

JWKS_TTL_SECONDS = 3600       # re-fetch public keys every hour
JWKS_FETCH_TIMEOUT = 15.0     # seconds before giving up on Clerk
JWKS_MAX_RETRIES = 3


async def get_jwks() -> dict:
    """
    Return Clerk's JWKS, fetching it if the cache is empty or stale.

    Uses an asyncio.Lock so only one coroutine fetches at a time; all
    others wait and then reuse the result.
    """
    global _jwks_cache, _jwks_fetched_at

    now = time.monotonic()
    if _jwks_cache and (now - _jwks_fetched_at) < JWKS_TTL_SECONDS:
        return _jwks_cache

    async with _jwks_lock:
        # Re-check inside the lock: another coroutine may have just refreshed.
        now = time.monotonic()
        if _jwks_cache and (now - _jwks_fetched_at) < JWKS_TTL_SECONDS:
            return _jwks_cache

        settings = get_settings()
        jwks_url = settings.CLERK_JWKS_URL
        if not jwks_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CLERK_JWKS_URL is not configured.",
            )

        last_exc: Exception | None = None
        async with httpx.AsyncClient(timeout=JWKS_FETCH_TIMEOUT) as client:
            for attempt in range(1, JWKS_MAX_RETRIES + 1):
                try:
                    response = await client.get(jwks_url)
                    response.raise_for_status()
                    _jwks_cache = response.json()
                    _jwks_fetched_at = time.monotonic()
                    return _jwks_cache
                except (httpx.TimeoutException, httpx.ConnectError) as exc:
                    last_exc = exc
                    if attempt < JWKS_MAX_RETRIES:
                        await asyncio.sleep(0.5 * attempt)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not reach Clerk JWKS endpoint after {JWKS_MAX_RETRIES} attempts: {last_exc}",
        )

async def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """
    FastAPI dependency to authenticate a user.

    In DEBUG mode, it allows bypassing JWT validation via a special header.
    Otherwise, it decodes and verifies a JWT from the Authorization header.
    """
    settings = get_settings()

    # --- DEVELOPMENT ONLY: Bypass JWT validation with a test header ---
    if settings.DEBUG and "X-Test-User-ID" in request.headers:
        clerk_id = request.headers["X-Test-User-ID"]
        user = await user_repo.get_user_by_clerk_id(clerk_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test user with Clerk ID '{clerk_id}' not found.",
            )
        return user

    # --- PRODUCTION: Standard JWT validation ---
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = creds.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        jwks = await get_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        clerk_id: Optional[str] = payload.get("sub")
        if clerk_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await user_repo.get_user_by_clerk_id(clerk_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with Clerk ID {clerk_id} not found in the database.",
        )
    return user

async def get_optional_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
) -> Optional[User]:
    """
    FastAPI dependency to optionally authenticate a user.
    Returns None if no credentials are provided or if validation fails.
    """
    if creds is None:
        return None
    try:
        return await get_current_user(request, creds, user_repo)
    except HTTPException:
        return None
