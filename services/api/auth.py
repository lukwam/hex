"""Hex API — API key authentication dependency."""

from __future__ import annotations

from fastapi import Header, HTTPException, Query, status
from firedantic import ModelNotFoundError

from ..shared.models import APIKey


async def require_api_key(
    x_api_key: str | None = Header(None),
    api_key: str | None = Query(None),
) -> APIKey:
    """FastAPI dependency that validates an API key.

    Accepts the key from either the ``X-API-Key`` header or the
    ``api_key`` query parameter. Raises 401 if missing or invalid.
    """
    key_id = x_api_key or api_key
    if not key_id or not key_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide via X-API-Key header or api_key query parameter.",
        )
    try:
        return APIKey.get_by_id(key_id.strip())
    except ModelNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        ) from e
