"""Hex shared package."""

from typing import Any

__all__ = ["HexConfig", "PuzzleNotFoundError"]


def __getattr__(name: str) -> Any:
    """Lazy attribute access."""
    if name == "HexConfig":
        from .config import HexConfig

        return HexConfig
    if name == "PuzzleNotFoundError":
        from .exceptions import PuzzleNotFoundError

        return PuzzleNotFoundError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
