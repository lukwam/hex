"""Hex persistence layer."""

from __future__ import annotations

from firedantic import ModelNotFoundError

from .exceptions import BookNotFoundError, PublicationNotFoundError, PuzzleNotFoundError, UserNotFoundError
from .models import Book, Publication, Puzzle, User


class PuzzleRepo:
    """Thin wrapper around Puzzle model for testability."""

    def list_all(self) -> list[Puzzle]:
        """Return all puzzles."""
        return Puzzle.find({})

    def get(self, puzzle_id: str) -> Puzzle:
        """Return a puzzle by ID or raise."""
        try:
            return Puzzle.get_by_id(puzzle_id)
        except ModelNotFoundError as e:
            raise PuzzleNotFoundError(f"Puzzle not found: {puzzle_id}") from e

    def find_by_pub(self, pub: str) -> list[Puzzle]:
        """Return puzzles for a publication."""
        return Puzzle.find({"pub": pub})


class BookRepo:
    """Thin wrapper around Book model for testability."""

    def list_all(self) -> list[Book]:
        """Return all books."""
        return Book.find({})

    def get(self, book_id: str) -> Book:
        """Return a book by ID or raise."""
        try:
            return Book.get_by_id(book_id)
        except ModelNotFoundError as e:
            raise BookNotFoundError(f"Book not found: {book_id}") from e


class PublicationRepo:
    """Thin wrapper around Publication model for testability."""

    def list_all(self) -> list[Publication]:
        """Return all publications."""
        return Publication.find({})

    def get(self, pub_id: str) -> Publication:
        """Return a publication by ID or raise."""
        try:
            return Publication.get_by_id(pub_id)
        except ModelNotFoundError as e:
            raise PublicationNotFoundError(f"Publication not found: {pub_id}") from e


class UserRepo:
    """Thin wrapper around User model for testability."""

    def get(self, user_id: str) -> User:
        """Return a user by ID or raise."""
        try:
            return User.get_by_id(user_id)
        except ModelNotFoundError as e:
            raise UserNotFoundError(f"User not found: {user_id}") from e

    def get_by_email(self, email: str) -> User | None:
        """Return a user by email or None."""
        results = User.find({"email": email})
        return results[0] if results else None
