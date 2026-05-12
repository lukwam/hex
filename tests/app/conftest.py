"""App service test fixtures.

Provides a Flask test client with mocked API and storage dependencies.
All network access is blocked by pytest-socket (--disable-socket).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure services/app/ is importable (it uses bare imports like `from api_client import ...`).
_app_dir = str(Path(__file__).resolve().parents[2] / "services" / "app")
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)


# ---------------------------------------------------------------------------
# Sample data factories
# ---------------------------------------------------------------------------

_MINIMAL_GRID = {
    "rows": ["ABC", "DEF", "GHI"],
    "cols": 3,
}


def make_puzzle(**overrides: Any) -> dict:
    """Build a realistic puzzle dict matching the Hex API response schema."""
    base: dict[str, Any] = {
        "id": "puzzle-abc123",
        "title": "Short and Sweet",
        "publication": "atlantic",
        "date": "2023-12-01",
        "author": "Emily Cox & Henry Rathvon",
        "editor": "",
        "instructions": "Solve the grid",
        "solution": "ABCDEFGHI",
        "grid": _MINIMAL_GRID,
        "clue_groups": [
            {
                "name": "Across",
                "clues": [
                    {"name": "1", "clue_text": "Start (3)"},
                ],
            },
        ],
        "settings": {},
        "unclued": [],
    }
    base.update(overrides)
    return base


def make_puzzle_list(n: int = 3, **overrides: Any) -> list[dict]:
    """Build a list of puzzle dicts with varied publications and dates."""
    pubs = ["atlantic", "wsj", "atlantic"]
    dates = ["2023-12-01", "2024-01-15", "1985-06-01"]
    puzzles = []
    for i in range(n):
        puzzles.append(
            make_puzzle(
                id=f"puzzle-{i}",
                title=f"Puzzle {i}",
                publication=pubs[i % len(pubs)],
                date=dates[i % len(dates)],
                **overrides,
            )
        )
    return puzzles


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_api():
    """Return a MagicMock pre-configured as a HexAPIClient."""
    api = MagicMock()
    api.list_puzzles.return_value = make_puzzle_list()
    api.get_puzzle.return_value = make_puzzle()
    return api


@pytest.fixture()
def app_client(mock_api, monkeypatch):
    """Flask test client with mocked API and storage.

    Patches the module-level _api in app.py and all storage functions
    so that no real network or GCS calls are made.
    """
    # Patch storage functions before importing app
    with (
        patch("app.get_puzzle_image_urls") as mock_images,
        patch("app.get_signed_url") as mock_signed_url,
        patch("app.download_blob") as mock_download,
    ):
        mock_images.return_value = {
            "puzzle_png": "https://storage.example.com/puzzle.png",
            "puzzle_pdf": "https://storage.example.com/puzzle.pdf",
            "solution_png": "https://storage.example.com/solution.png",
            "solution_pdf": "https://storage.example.com/solution.pdf",
            "puzzle_thumb": None,
            "solution_thumb": None,
        }
        mock_signed_url.return_value = "https://storage.example.com/signed"
        mock_download.return_value = b"%PDF-1.4 fake pdf content"

        import app as app_module

        monkeypatch.setattr(app_module, "_api", mock_api)

        app_module.app.config["TESTING"] = True
        with app_module.app.test_client() as client:
            yield client
