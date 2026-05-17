"""Tests for HexAPIClient — HTTP client with in-memory TTL cache.

All HTTP calls are mocked via unittest.mock.patch on requests.get.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from api_client import HexAPIClient


@pytest.fixture()
def client():
    """Return an HexAPIClient with short TTL for testing."""
    return HexAPIClient(base_url="https://api.example.com", api_key="test-key", ttl=1)


class TestHexAPIClientHeaders:
    """Verify HTTP headers are set correctly."""

    def test_api_key_header(self, client):
        assert client._headers() == {"X-API-Key": "test-key"}

    def test_base_url_strips_trailing_slash(self):
        c = HexAPIClient(base_url="https://api.example.com/", api_key="k")
        assert c._base_url == "https://api.example.com"


class TestHexAPIClientGet:
    """Tests for the _get method (raw HTTP calls)."""

    @patch("api_client.requests.get")
    def test_success_returns_json(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "1"}]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = client._get("/puzzles/")
        assert result == [{"id": "1"}]
        mock_get.assert_called_once_with(
            "https://api.example.com/puzzles/",
            headers={"X-API-Key": "test-key"},
            timeout=30,
            allow_redirects=True,
        )

    @patch("api_client.requests.get")
    def test_http_error_returns_none(self, mock_get, client):
        import requests

        mock_get.side_effect = requests.RequestException("Connection failed")
        result = client._get("/puzzles/")
        assert result is None

    @patch("api_client.requests.get")
    def test_status_error_returns_none(self, mock_get, client):
        import requests

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("404")
        mock_get.return_value = mock_resp

        result = client._get("/puzzles/")
        assert result is None


class TestHexAPIClientCaching:
    """Tests for the _cached_get TTL cache."""

    @patch("api_client.requests.get")
    def test_cache_hit_within_ttl(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "1"}]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        # First call populates cache
        result1 = client.list_puzzles()
        # Second call should use cache
        result2 = client.list_puzzles()

        assert result1 == result2
        assert mock_get.call_count == 1  # Only one HTTP call

    @patch("api_client.requests.get")
    def test_cache_miss_after_ttl(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "1"}]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        client.list_puzzles()

        # Expire the cache by manipulating the timestamp
        key = "puzzles"
        ts, data = client._cache[key]
        client._cache[key] = (ts - 10, data)  # Shift timestamp back past TTL

        client.list_puzzles()
        assert mock_get.call_count == 2  # Two HTTP calls

    @patch("api_client.requests.get")
    def test_cache_not_stored_on_error(self, mock_get, client):
        import requests

        mock_get.side_effect = requests.RequestException("fail")
        client.list_puzzles()
        assert "puzzles" not in client._cache


class TestHexAPIClientPublicMethods:
    """Tests for the public API surface."""

    @patch("api_client.requests.get")
    def test_list_puzzles_returns_list(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "1"}, {"id": "2"}]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        client = HexAPIClient(base_url="https://api.example.com", api_key="k")
        result = client.list_puzzles()
        assert isinstance(result, list)
        assert len(result) == 2

    @patch("api_client.requests.get")
    def test_list_puzzles_error_returns_empty_list(self, mock_get):
        import requests

        mock_get.side_effect = requests.RequestException("fail")
        client = HexAPIClient(base_url="https://api.example.com", api_key="k")
        result = client.list_puzzles()
        assert result == []

    @patch("api_client.requests.get")
    def test_get_puzzle_not_cached(self, mock_get):
        """get_puzzle calls _get directly, not _cached_get."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "abc"}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        client = HexAPIClient(base_url="https://api.example.com", api_key="k")
        client.get_puzzle("abc")
        client.get_puzzle("abc")
        assert mock_get.call_count == 2  # No caching for detail views

    @patch("api_client.requests.get")
    def test_list_publications(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "atlantic"}]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        client = HexAPIClient(base_url="https://api.example.com", api_key="k")
        result = client.list_publications()
        assert result == [{"id": "atlantic"}]

    @patch("api_client.requests.get")
    def test_list_books(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "book1"}]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        client = HexAPIClient(base_url="https://api.example.com", api_key="k")
        result = client.list_books()
        assert result == [{"id": "book1"}]
