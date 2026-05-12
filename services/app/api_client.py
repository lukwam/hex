"""CoxRathvon App — Hex API client.

Thin HTTP wrapper around the Hex API. All puzzle data comes through here,
with a simple in-memory TTL cache to avoid hitting the API on every request.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Default cache TTL: 5 minutes
_DEFAULT_TTL = 300


class HexAPIClient:
    """HTTP client for the Hex API, with in-memory caching."""

    def __init__(self, base_url: str, api_key: str, ttl: int = _DEFAULT_TTL):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._ttl = ttl
        self._cache: dict[str, tuple[float, Any]] = {}

    # ── internal ──────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key}

    def _get(self, path: str) -> Any:
        """Perform a GET request and return parsed JSON."""
        url = f"{self._base_url}{path}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=30, allow_redirects=True)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            logger.exception("API request failed: %s", url)
            return None

    def _cached_get(self, key: str, path: str) -> Any:
        """Return cached data if fresh, otherwise fetch and cache."""
        now = time.time()
        if key in self._cache:
            ts, data = self._cache[key]
            if now - ts < self._ttl:
                return data

        data = self._get(path)
        if data is not None:
            self._cache[key] = (now, data)
        return data

    # ── public API ────────────────────────────────────────────────

    def list_puzzles(self) -> list[dict]:
        """Return all puzzles (cached)."""
        return self._cached_get("puzzles", "/puzzles/") or []

    def get_puzzle(self, puzzle_id: str) -> dict | None:
        """Return a single puzzle by ID (not cached — detail views)."""
        return self._get(f"/puzzles/{puzzle_id}")

    def list_publications(self) -> list[dict]:
        """Return all publications (cached)."""
        return self._cached_get("publications", "/publications/") or []

    def list_books(self) -> list[dict]:
        """Return all books (cached)."""
        return self._cached_get("books", "/books/") or []
