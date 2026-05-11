"""Hex API — books router."""

from fastapi import APIRouter, Depends, HTTPException

from ...shared.exceptions import BookNotFoundError
from ...shared.repo import BookRepo
from ..auth import require_api_key

router = APIRouter(
    prefix="/books",
    tags=["Books"],
    dependencies=[Depends(require_api_key)],
)

_repo = BookRepo()


@router.get("/")
async def list_books() -> list[dict]:
    """Return all books."""
    books = _repo.list_all()
    return [b.model_dump() for b in books]


@router.get("/{book_id}")
async def get_book(book_id: str) -> dict:
    """Return a single book by ID."""
    try:
        book = _repo.get(book_id)
    except BookNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return book.model_dump()
