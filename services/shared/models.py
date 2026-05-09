"""Hex Firestore models."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from firedantic import Model
from pydantic import BeforeValidator, ConfigDict, Field


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


# Use on calendar date fields stored as strings (e.g. date).
DateStr = Annotated[str, BeforeValidator(_to_date_str)]

# Use on fields that may be stored as int or str in Firestore.
CoerceInt = Annotated[int | None, BeforeValidator(_coerce_int)]


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


class Puzzle(Model):
    """A single puzzle."""

    __collection__ = "puzzles"

    title: str
    pub: str = ""
    date: DateStr = ""
    issue: str = ""
    num: CoerceInt = None
    shape: str = ""
    year: str = ""
    month: str = ""
    books: list[str] = Field(default_factory=list)
    web_link: str | None = None
    puzzle_link: str | None = None
    answer_link: str | None = None
    googledoc_link: str | None = None
    puzzleme_link: str | None = None


class Solve(Model):
    """A user's solve record for a puzzle."""

    __collection__ = "solves"

    user_id: str
    puzzle_id: str


class User(Model):
    """An application user."""

    __collection__ = "users"

    email: str
    name: str = ""
    first_name: str = ""
    last_name: str = ""
    photo: str = ""
    admin: bool = False
