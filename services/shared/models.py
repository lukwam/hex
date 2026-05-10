"""Hex Firestore models."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from firedantic import Model
from hexword import ClueGroup, Grid, PuzzleSettings
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _to_date_str(v: object) -> str:
    """Coerce Firestore Timestamps or datetimes to ISO date strings.

    Firestore may return DatetimeWithNanoseconds for fields that were
    previously stored as Timestamps. This converts them to 'YYYY-MM-DD'.
    """
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    return str(v) if v is not None else ""


def _coerce_int(v: str | int | None) -> int | None:
    """Coerce str or other types to int.

    Some legacy Firestore documents store numeric fields (e.g. puzzle
    number) as strings.  This normalizes them to ints so the model
    works regardless of stored type.
    """
    if v is None or v == "":
        return None
    return int(v)


def _none_to_str(v: object) -> str:
    """Coerce None to empty string.

    CoxRathvon stores some string fields as None instead of ''.
    """
    if v is None:
        return ""
    return str(v)


# Use on calendar date fields stored as strings (e.g. date).
DateStr = Annotated[str, BeforeValidator(_to_date_str)]

# Use on fields that may be stored as int or str in Firestore.
CoerceInt = Annotated[int | None, BeforeValidator(_coerce_int)]

# Use on string fields that may be None in legacy data.
NoneStr = Annotated[str, BeforeValidator(_none_to_str)]


class Publication(Model):
    """A puzzle publication (e.g., WSJ, The Atlantic Puzzler)."""

    __collection__ = "publications"

    name: str
    code: str = ""
    url: str = ""


class Book(Model):
    """A published book of puzzles."""

    __collection__ = "books"
    model_config = ConfigDict(populate_by_name=True)

    title: str
    code: str = ""
    date: DateStr = ""
    publisher: str = ""
    source: str = ""
    notes: str = ""
    isbn_10: str = Field(default="", alias="isbn-10")
    isbn_13: str = Field(default="", alias="isbn-13")
    amazon_link: str = ""
    cover: str = ""


class PuzzleLinks(BaseModel):
    """External links for a puzzle."""

    puzzle_link: str | None = None
    answer_link: str | None = None
    puzzle_pdf_url: str | None = None
    solution_pdf_url: str | None = None
    puzzle_svg_url: str | None = None
    solution_svg_url: str | None = None
    puzzle_grid_png_url: str | None = None
    solution_grid_png_url: str | None = None
    googledoc_link: str | None = None
    puzzleme_link: str | None = None
    web_link: str | None = None


class PuzzleFiles(BaseModel):
    """GCS file paths for puzzle assets."""

    puzzle_pdf: str | None = None
    puzzle_png: str | None = None
    puzzle_svg: str | None = None
    puzzle_thumbnail_png: str | None = None
    solution_pdf: str | None = None
    solution_png: str | None = None
    solution_svg: str | None = None
    solution_thumbnail_png: str | None = None


class Puzzle(Model):
    """A single puzzle (merged metadata + hexword content)."""

    __collection__ = "puzzles"

    # Core metadata
    title: str
    author: str = ""
    publication: NoneStr = ""
    number: CoerceInt = None
    date: DateStr = ""
    issue: NoneStr = ""
    editor: str | None = None
    shape: NoneStr = ""
    year: NoneStr = ""
    month: NoneStr = ""
    books: list[str] = Field(default_factory=list)

    # References
    links: PuzzleLinks = Field(default_factory=PuzzleLinks)
    files: PuzzleFiles = Field(default_factory=PuzzleFiles)

    # Grid/clue data (from hexword library)
    instructions: str | None = None
    solution: str | None = None
    clue_groups: list[ClueGroup] = Field(default_factory=list)
    grid: Grid = Field(default_factory=Grid)
    settings: PuzzleSettings = Field(default_factory=PuzzleSettings)
    unclued: list[str] = Field(default_factory=list)


class Solve(Model):
    """A user's solve record for a puzzle."""

    __collection__ = "solves"

    user_id: str
    puzzle_id: str


class User(Model):
    """An application user."""

    __collection__ = "users"

    email: str
    name: NoneStr = ""
    first_name: NoneStr = ""
    last_name: NoneStr = ""
    photo: NoneStr = ""
    admin: bool = False
