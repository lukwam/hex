"""Hex API — health check router."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/healthz")
async def healthz() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
