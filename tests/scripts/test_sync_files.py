"""Tests for scripts.sync_files — Drive→GCS sync logic."""

from __future__ import annotations

from scripts.sync_files import build_drive_name_index, build_object_metadata, map_drive_to_gcs

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_puzzle(
    puzzle_id: str,
    title: str,
    date: str,
    pub: str = "atlantic",
    number: int | None = None,
) -> dict:
    """Create a minimal puzzle dict for testing."""
    return {
        "id": puzzle_id,
        "title": title,
        "date": date,
        "pub": pub,
        "publication": pub,
        "number": number,
        "issue": "",
        "author": "Test Author",
    }


# ---------------------------------------------------------------------------
# build_drive_name_index
# ---------------------------------------------------------------------------


class TestBuildDriveNameIndex:
    """Tests for build_drive_name_index() — filename→puzzle lookup."""

    def test_yyyy_mm_dd_keys(self):
        puzzles = {"p1": _make_puzzle("p1", "Test Puzzle", "2023-08-26", "wsj")}
        index = build_drive_name_index(puzzles)
        assert "2023-08-26 Test Puzzle.pdf" in index
        assert "2023-08-26 Test Puzzle (solution).pdf" in index
        assert "2023-08-26 Test Puzzle.svg" in index
        assert "2023-08-26 Test Puzzle (solution).svg" in index

    def test_yyyy_mm_keys(self):
        """YYYY-MM prefix keys for monthly publications."""
        puzzles = {"p1": _make_puzzle("p1", "Short and Sweet", "1977-09-01", "atlantic")}
        index = build_drive_name_index(puzzles)
        # Both YYYY-MM-DD and YYYY-MM prefixes should be registered
        assert "1977-09-01 Short and Sweet.pdf" in index
        assert "1977-09 Short and Sweet.pdf" in index
        assert "1977-09 Short and Sweet (solution).svg" in index

    def test_hex_suffix_keys(self):
        """Files with (hex) suffix should match."""
        puzzles = {"p1": _make_puzzle("p1", "Eightsome Reels", "1978-01-01", "atlantic")}
        index = build_drive_name_index(puzzles)
        assert "1978-01 Eightsome Reels (hex).pdf" in index
        assert "1978-01-01 Eightsome Reels (hex).svg" in index

    def test_skips_incomplete_puzzles(self):
        """Puzzles without title, date, or pub are skipped."""
        puzzles = {
            "p1": {"id": "p1", "title": "", "date": "2023-01-01", "pub": "wsj"},
            "p2": {"id": "p2", "title": "Test", "date": "", "pub": "wsj"},
            "p3": {"id": "p3", "title": "Test", "date": "2023-01-01", "pub": ""},
        }
        index = build_drive_name_index(puzzles)
        assert len(index) == 0

    def test_duplicate_titles_different_dates(self):
        """Same title with different dates maps to different puzzles."""
        puzzles = {
            "p1": _make_puzzle("p1", "Shakedown", "1994-06-01", "atlantic"),
            "p2": _make_puzzle("p2", "Shakedown", "2023-09-24", "wsj"),
        }
        index = build_drive_name_index(puzzles)
        assert index["1994-06 Shakedown.pdf"]["id"] == "p1"
        assert index["2023-09-24 Shakedown.pdf"]["id"] == "p2"

    def test_doc_name_without_extension(self):
        """Base doc name (no extension) should also be indexed."""
        puzzles = {"p1": _make_puzzle("p1", "Test", "2023-01-15", "wsj")}
        index = build_drive_name_index(puzzles)
        assert "2023-01-15 Test" in index
        assert "2023-01 Test" in index


# ---------------------------------------------------------------------------
# map_drive_to_gcs
# ---------------------------------------------------------------------------


class TestMapDriveToGcs:
    """Tests for map_drive_to_gcs() — mapping Drive files to GCS paths."""

    def _make_drive_file(self, name: str, file_id: str = "file1") -> dict:
        return {"id": file_id, "name": name, "md5Checksum": "abc", "mimeType": "application/pdf"}

    def test_matched_puzzle_pdf(self):
        puzzles = {"p1": _make_puzzle("p1", "Test", "2023-08-26", "wsj")}
        index = build_drive_name_index(puzzles)
        drive_files = [self._make_drive_file("2023-08-26 Test.pdf")]
        mappings = map_drive_to_gcs(drive_files, index)
        assert len(mappings) == 1
        assert mappings[0]["object_name"] == "puzzles/wsj/p1/p1_puzzle.pdf"
        assert mappings[0]["file_type"] == "puzzle_pdf"

    def test_solution_pdf(self):
        puzzles = {"p1": _make_puzzle("p1", "Test", "2023-08-26", "wsj")}
        index = build_drive_name_index(puzzles)
        drive_files = [self._make_drive_file("2023-08-26 Test (solution).pdf")]
        mappings = map_drive_to_gcs(drive_files, index)
        assert len(mappings) == 1
        assert mappings[0]["file_type"] == "solution_pdf"
        assert "solution.pdf" in mappings[0]["object_name"]

    def test_svg_files(self):
        puzzles = {"p1": _make_puzzle("p1", "Test", "2023-08-26", "wsj")}
        index = build_drive_name_index(puzzles)
        drive_files = [
            {"id": "f1", "name": "2023-08-26 Test.svg", "mimeType": "image/svg+xml"},
        ]
        mappings = map_drive_to_gcs(drive_files, index)
        assert len(mappings) == 1
        assert mappings[0]["file_type"] == "puzzle_svg"
        assert mappings[0]["mime_type"] == "image/svg+xml"

    def test_pub_filter(self):
        puzzles = {
            "p1": _make_puzzle("p1", "Atlantic Puzzle", "1977-09-01", "atlantic"),
            "p2": _make_puzzle("p2", "WSJ Puzzle", "2023-08-26", "wsj"),
        }
        index = build_drive_name_index(puzzles)
        drive_files = [
            self._make_drive_file("1977-09 Atlantic Puzzle.pdf"),
            self._make_drive_file("2023-08-26 WSJ Puzzle.pdf", file_id="f2"),
        ]
        mappings = map_drive_to_gcs(drive_files, index, pub_filter="wsj")
        assert len(mappings) == 1
        assert mappings[0]["puzzle"]["id"] == "p2"

    def test_unmatched_files_skipped(self):
        index = {}
        drive_files = [self._make_drive_file("unknown_file.pdf")]
        mappings = map_drive_to_gcs(drive_files, index)
        assert len(mappings) == 0

    def test_non_pdf_svg_skipped(self):
        """Only PDF and SVG files produce mappings."""
        puzzles = {"p1": _make_puzzle("p1", "Test", "2023-08-26", "wsj")}
        index = build_drive_name_index(puzzles)
        drive_files = [
            {"id": "f1", "name": "2023-08-26 Test.png", "mimeType": "image/png"},
        ]
        mappings = map_drive_to_gcs(drive_files, index)
        assert len(mappings) == 0


# ---------------------------------------------------------------------------
# build_object_metadata
# ---------------------------------------------------------------------------


class TestBuildObjectMetadata:
    """Tests for build_object_metadata() — GCS custom metadata."""

    def test_structure(self):
        puzzle = _make_puzzle("p1", "Test Puzzle", "2023-08-26", "wsj")
        drive_file = {
            "id": "drive123",
            "name": "2023-08-26 Test Puzzle.pdf",
            "md5Checksum": "abc",
            "mimeType": "application/pdf",
            "modifiedTime": "2023-08-26T12:00:00Z",
            "size": "12345",
        }
        meta = build_object_metadata(puzzle, drive_file, "puzzle_pdf")
        assert meta["puzzle_id"] == "p1"
        assert meta["title"] == "Test Puzzle"
        assert meta["pub"] == "wsj"
        assert meta["file_type"] == "puzzle_pdf"
        assert meta["file_id"] == "drive123"
        assert meta["date"] == "2023-08-26"
