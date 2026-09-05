"""Hex API — health check router."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict:
    """Health check endpoint.

    Named "/health" rather than "/healthz" — Cloud Run's shared front-end
    infrastructure intercepts the exact literal path "/healthz" before it
    reaches any container, always returning a generic Google 404 regardless
    of what the app defines there.
    """
    return {"status": "ok"}
