"""Hex domain exceptions."""


class HexError(Exception):
    """Base exception for Hex."""


class PuzzleNotFoundError(HexError):
    """Puzzle not found."""


class BookNotFoundError(HexError):
    """Book not found."""


class PublicationNotFoundError(HexError):
    """Publication not found."""


class UserNotFoundError(HexError):
    """User not found."""
