"""Hex API — puzzles router."""

from fastapi import APIRouter, HTTPException

from ...shared.exceptions import PuzzleNotFoundError
from ...shared.repo import PuzzleRepo

router = APIRouter(
    prefix="/puzzles",
    tags=["Puzzles"],
)

_repo = PuzzleRepo()


@router.get("/")
async def list_puzzles() -> list[dict]:
    """Return all puzzles."""
    puzzles = _repo.list_all()
    return [p.model_dump() for p in puzzles]


@router.get("/{puzzle_id}")
async def get_puzzle(puzzle_id: str) -> dict:
    """Return a single puzzle by ID."""
    try:
        puzzle = _repo.get(puzzle_id)
    except PuzzleNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return puzzle.model_dump()
