"""Tests for pure helper functions in services/app/.

These test business logic that doesn't require Flask context or mocked I/O.
"""

from __future__ import annotations

import datetime
from unittest.mock import patch


class TestParseDate:
    """Tests for app._parse_date."""

    def _parse(self, s):
        from app import _parse_date

        return _parse_date(s)

    def test_valid_date(self):
        result = self._parse("2023-12-01")
        assert result == datetime.datetime(2023, 12, 1)

    def test_date_with_time_suffix(self):
        """Input like '2023-12-01T00:00:00Z' should still parse."""
        result = self._parse("2023-12-01T00:00:00Z")
        assert result == datetime.datetime(2023, 12, 1)

    def test_short_string(self):
        result = self._parse("2023")
        assert result is None

    def test_empty_string(self):
        result = self._parse("")
        assert result is None

    def test_none_value(self):
        result = self._parse(None)
        assert result is None

    def test_garbage_string(self):
        result = self._parse("not-a-date")
        assert result is None

    def test_partial_date(self):
        result = self._parse("2023-13-01")  # month 13
        assert result is None


class TestBuildHexword:
    """Tests for app._build_hexword."""

    def _build(self, puzzle):
        from app import _build_hexword

        return _build_hexword(puzzle)

    def test_valid_puzzle(self):
        from tests.app.conftest import make_puzzle

        puzzle = make_puzzle()
        result = self._build(puzzle)
        assert result is not None
        assert result.title == "Short and Sweet"

    def test_missing_grid(self):
        from tests.app.conftest import make_puzzle

        puzzle = make_puzzle(grid={})
        result = self._build(puzzle)
        assert result is None

    def test_no_grid_key(self):
        from tests.app.conftest import make_puzzle

        puzzle = make_puzzle()
        del puzzle["grid"]
        result = self._build(puzzle)
        assert result is None

    def test_empty_rows(self):
        from tests.app.conftest import make_puzzle

        puzzle = make_puzzle(grid={"rows": [], "cols": 0})
        result = self._build(puzzle)
        assert result is None

    def test_build_exception_returns_none(self):
        """If Hexword() raises an exception, _build_hexword returns None."""
        with patch("app.Hexword", side_effect=Exception("boom")):
            from tests.app.conftest import make_puzzle

            puzzle = make_puzzle()
            from app import _build_hexword

            result = _build_hexword(puzzle)
            assert result is None


class TestAssetsBucketName:
    """Tests for storage._assets_bucket_name."""

    def _bucket_name(self):
        from storage import _assets_bucket_name

        return _assets_bucket_name()

    def test_dev_env(self, monkeypatch):
        monkeypatch.setenv("HEX_ENV", "dev")
        assert self._bucket_name() == "lukwam-hex-assets-dev"

    def test_prod_env(self, monkeypatch):
        monkeypatch.setenv("HEX_ENV", "prod")
        assert self._bucket_name() == "lukwam-hex-assets"

    def test_staging_env(self, monkeypatch):
        monkeypatch.setenv("HEX_ENV", "staging")
        assert self._bucket_name() == "lukwam-hex-assets-staging"

    def test_default_env(self, monkeypatch):
        monkeypatch.delenv("HEX_ENV", raising=False)
        # Root conftest sets HEX_ENV=test
        result = self._bucket_name()
        assert "lukwam-hex-assets" in result


class TestGetPuzzleImageUrls:
    """Tests for storage.get_puzzle_image_urls path construction."""

    def test_path_construction(self):
        """Verify the URL dict keys and that paths are constructed correctly."""
        with patch("storage.get_signed_url") as mock_sign:
            # Return the path itself so we can verify construction
            mock_sign.side_effect = lambda p: f"signed:{p}"
            from storage import get_puzzle_image_urls

            result = get_puzzle_image_urls("abc123", "atlantic")

        expected_prefix = "puzzles/atlantic/abc123/abc123"
        assert result["puzzle_png"] == f"signed:{expected_prefix}_puzzle.png"
        assert result["puzzle_pdf"] == f"signed:{expected_prefix}_puzzle.pdf"
        assert result["solution_png"] == f"signed:{expected_prefix}_solution.png"
        assert result["solution_pdf"] == f"signed:{expected_prefix}_solution.pdf"
        assert result["puzzle_thumb"] == f"signed:{expected_prefix}_puzzle_thumb.png"
        assert result["solution_thumb"] == f"signed:{expected_prefix}_solution_thumb.png"

    def test_all_six_keys_present(self):
        with patch("storage.get_signed_url", return_value=None):
            from storage import get_puzzle_image_urls

            result = get_puzzle_image_urls("x", "wsj")
        assert set(result.keys()) == {
            "puzzle_png",
            "puzzle_pdf",
            "solution_png",
            "solution_pdf",
            "puzzle_thumb",
            "solution_thumb",
        }
