"""Tests for services.shared.models — validators, coercions, and model construction."""

from __future__ import annotations

from datetime import datetime

from services.shared.models import (
    Book,
    FileRecord,
    Publication,
    Puzzle,
    PuzzleFiles,
    PuzzleLinks,
    Solve,
    User,
    _coerce_file_record,
    _coerce_int,
    _none_to_str,
    _to_date_str,
)

# ---------------------------------------------------------------------------
# Validator helpers
# ---------------------------------------------------------------------------


class TestToDateStr:
    """Tests for _to_date_str() — Firestore timestamp coercion."""

    def test_datetime_to_date(self):
        dt = datetime(2023, 8, 26, 14, 30, 0)
        assert _to_date_str(dt) == "2023-08-26"

    def test_string_passthrough(self):
        assert _to_date_str("2023-08-26") == "2023-08-26"

    def test_short_date_passthrough(self):
        assert _to_date_str("2023-08") == "2023-08"

    def test_none_returns_empty(self):
        assert _to_date_str(None) == ""

    def test_empty_string_passthrough(self):
        assert _to_date_str("") == ""


class TestCoerceInt:
    """Tests for _coerce_int() — flexible int parsing."""

    def test_string_to_int(self):
        assert _coerce_int("42") == 42

    def test_int_passthrough(self):
        assert _coerce_int(42) == 42

    def test_none_returns_none(self):
        assert _coerce_int(None) is None

    def test_empty_string_returns_none(self):
        assert _coerce_int("") is None

    def test_zero_string(self):
        assert _coerce_int("0") == 0


class TestNoneToStr:
    """Tests for _none_to_str() — None→'' coercion."""

    def test_none_to_empty(self):
        assert _none_to_str(None) == ""

    def test_string_passthrough(self):
        assert _none_to_str("hello") == "hello"

    def test_empty_string_passthrough(self):
        assert _none_to_str("") == ""

    def test_other_types(self):
        assert _none_to_str(42) == "42"


class TestCoerceFileRecord:
    """Tests for _coerce_file_record() — legacy file field coercion."""

    def test_none_returns_empty_record(self):
        result = _coerce_file_record(None)
        assert isinstance(result, FileRecord)
        assert result.path == ""

    def test_string_sets_path(self):
        result = _coerce_file_record("abc/puzzle.pdf")
        assert isinstance(result, FileRecord)
        assert result.path == "abc/puzzle.pdf"

    def test_empty_string_returns_empty_record(self):
        result = _coerce_file_record("")
        assert isinstance(result, FileRecord)
        assert result.path == ""

    def test_dict_passthrough(self):
        data = {"path": "foo/bar.pdf", "size": 1234}
        result = _coerce_file_record(data)
        # Should pass through unchanged for Pydantic to handle
        assert result == data

    def test_file_record_passthrough(self):
        record = FileRecord(path="existing.pdf")
        result = _coerce_file_record(record)
        assert result is record


# ---------------------------------------------------------------------------
# Model construction
# ---------------------------------------------------------------------------


class TestFileRecord:
    """Tests for FileRecord model."""

    def test_defaults(self):
        r = FileRecord()
        assert r.path == ""
        assert r.gcs_md5 == ""
        assert r.size == 0
        assert r.drive_file_id == ""

    def test_with_values(self):
        r = FileRecord(path="puzzles/wsj/abc/abc_puzzle.pdf", size=12345)
        assert r.path == "puzzles/wsj/abc/abc_puzzle.pdf"
        assert r.size == 12345


class TestPuzzleFiles:
    """Tests for PuzzleFiles manifest model."""

    def test_defaults(self):
        f = PuzzleFiles()
        assert isinstance(f.puzzle_pdf, FileRecord)
        assert f.puzzle_pdf.path == ""
        assert isinstance(f.solution_svg, FileRecord)

    def test_coercion_from_string(self):
        """Legacy data stores file paths as plain strings."""
        f = PuzzleFiles(puzzle_pdf="old/path.pdf")  # type: ignore[arg-type]
        assert isinstance(f.puzzle_pdf, FileRecord)
        assert f.puzzle_pdf.path == "old/path.pdf"


class TestPuzzleLinks:
    """Tests for PuzzleLinks model."""

    def test_defaults(self):
        links = PuzzleLinks()
        assert links.puzzle_link is None
        assert links.answer_link is None
        assert links.puzzle_pdf_url is None


class TestPublication:
    """Tests for Publication model."""

    def test_construction(self):
        pub = Publication(name="Wall Street Journal", code="wsj")
        assert pub.name == "Wall Street Journal"
        assert pub.code == "wsj"
        assert pub.url == ""


class TestBook:
    """Tests for Book model."""

    def test_minimal(self):
        book = Book(title="Atlantic Cryptics Vol. 1")
        assert book.title == "Atlantic Cryptics Vol. 1"
        assert book.code == ""
        assert book.isbn_10 == ""

    def test_isbn_alias(self):
        """isbn-10 field uses alias for Firestore compat."""
        book = Book(title="Test", isbn_10="0123456789")
        assert book.isbn_10 == "0123456789"


class TestPuzzle:
    """Tests for Puzzle model."""

    def test_minimal(self):
        puzzle = Puzzle(title="Test Puzzle")
        assert puzzle.title == "Test Puzzle"
        assert puzzle.author == ""
        assert puzzle.number is None
        assert puzzle.date == ""
        assert puzzle.books == []
        assert puzzle.clue_groups == []

    def test_date_coercion_from_datetime(self):
        dt = datetime(1977, 9, 1)
        puzzle = Puzzle(title="Short and Sweet", date=dt)  # type: ignore[arg-type]
        assert puzzle.date == "1977-09-01"

    def test_number_coercion_from_string(self):
        puzzle = Puzzle(title="Test", number="42")  # type: ignore[arg-type]
        assert puzzle.number == 42

    def test_none_string_fields(self):
        """Legacy data stores some string fields as None."""
        puzzle = Puzzle(title="Test", publication=None, shape=None)  # type: ignore[arg-type]
        assert puzzle.publication == ""
        assert puzzle.shape == ""

    def test_files_default(self):
        puzzle = Puzzle(title="Test")
        assert isinstance(puzzle.files, PuzzleFiles)
        assert isinstance(puzzle.links, PuzzleLinks)


class TestUser:
    """Tests for User model."""

    def test_construction(self):
        user = User(email="test@example.com", name="Test User")
        assert user.email == "test@example.com"
        assert user.admin is False

    def test_none_coercion(self):
        user = User(email="test@example.com", name=None)  # type: ignore[arg-type]
        assert user.name == ""


class TestSolve:
    """Tests for Solve model."""

    def test_construction(self):
        solve = Solve(user_id="user123", puzzle_id="puzzle456")
        assert solve.user_id == "user123"
        assert solve.puzzle_id == "puzzle456"
