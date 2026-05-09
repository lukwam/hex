"""Hex Firestore models."""

from __future__ import annotations

from datetime import datetime

from firedantic import Model
from pydantic import Field


class Publication(Model):
    """A puzzle publication (e.g., WSJ, The Atlantic Puzzler)."""

    __collection__ = "publications"

    name: str
    url: str = ""


class Book(Model):
    """A published book of puzzles."""

    __collection__ = "books"

    title: str
    isbn_10: str = ""
    isbn_13: str = ""
    date: datetime | None = None
    pages: int = 0
    amazon_url: str = ""
    cover_url: str = ""
    images: dict[str, str] = Field(default_factory=dict)


class Puzzle(Model):
    """A single puzzle."""

    __collection__ = "puzzles"

    title: str
    pub: str = ""
    date: datetime | None = None
    issue: str = ""
    web_url: str = ""
    puzzle_url: str = ""
    answer_url: str = ""
    images: dict[str, str] = Field(default_factory=dict)


class Solve(Model):
    """A user's solve record for a puzzle."""

    __collection__ = "solves"

    user_id: str
    puzzle_id: str
    solved_at: datetime | None = None
    time_seconds: int | None = None


class User(Model):
    """An application user."""

    __collection__ = "users"

    email: str
    handle: str = ""
    is_admin: bool = False
    books_owned: list[str] = Field(default_factory=list)
    favorites: list[str] = Field(default_factory=list)
    puzzles_solved: list[str] = Field(default_factory=list)
