"""Hex Firestore models."""

from __future__ import annotations

from datetime import UTC, datetime
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


class FileRecord(BaseModel):
    """State record for a single file in the asset manifest.

    Tracks both GCS and Drive state so sync scripts can detect changes
    on either side without downloading file content.
    """

    # GCS state
    path: str = ""  # e.g. puzzles/wsj/abc123/abc123_puzzle.pdf
    gcs_md5: str = ""  # base64-encoded MD5 from GCS
    gcs_etag: str = ""  # changes on ANY blob property change
    gcs_metageneration: int = 0  # increments on metadata-only changes
    size: int = 0  # file size in bytes
    content_type: str = ""  # e.g. application/pdf

    # Drive state (source of truth for PDFs/SVGs)
    drive_file_id: str = ""  # Google Drive file ID
    drive_md5: str = ""  # hex-encoded MD5 from Drive API
    drive_modified_time: str = ""  # ISO timestamp from Drive


def _coerce_file_record(v: object) -> FileRecord | object:
    """Coerce legacy string/None file fields to FileRecord.

    Old Firestore data stores these as flat strings (e.g. 'abc_puzzle.pdf')
    or None. Convert to FileRecord with the path set.
    """
    if v is None:
        return FileRecord()
    if isinstance(v, str):
        return FileRecord(path=v) if v else FileRecord()
    return v


CoerceFileRecord = Annotated[FileRecord, BeforeValidator(_coerce_file_record)]


class PuzzleFiles(BaseModel):
    """GCS file manifest for puzzle assets.

    Each field tracks the full sync state for one file type,
    enabling idempotent sync without re-downloading content.
    """

    puzzle_pdf: CoerceFileRecord = Field(default_factory=FileRecord)
    puzzle_png: CoerceFileRecord = Field(default_factory=FileRecord)
    puzzle_svg: CoerceFileRecord = Field(default_factory=FileRecord)
    puzzle_thumb: CoerceFileRecord = Field(default_factory=FileRecord)
    solution_pdf: CoerceFileRecord = Field(default_factory=FileRecord)
    solution_png: CoerceFileRecord = Field(default_factory=FileRecord)
    solution_svg: CoerceFileRecord = Field(default_factory=FileRecord)
    solution_thumb: CoerceFileRecord = Field(default_factory=FileRecord)


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


class APIKey(Model):
    """An API key for the Hex API.

    The Firestore document ID **is** the key itself — a random string
    generated via uuid4().hex on creation.  Validation is a simple
    get_by_id() call.
    """

    __collection__ = "api_keys"

    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime | None = None
