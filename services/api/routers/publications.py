"""Hex API — publications router."""

from fastapi import APIRouter, HTTPException

from ...shared.exceptions import PublicationNotFoundError
from ...shared.repo import PublicationRepo

router = APIRouter(
    prefix="/publications",
    tags=["Publications"],
)

_repo = PublicationRepo()


@router.get("/")
async def list_publications() -> list[dict]:
    """Return all publications."""
    pubs = _repo.list_all()
    return [p.model_dump() for p in pubs]


@router.get("/{pub_id}")
async def get_publication(pub_id: str) -> dict:
    """Return a single publication by ID."""
    try:
        pub = _repo.get(pub_id)
    except PublicationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return pub.model_dump()
