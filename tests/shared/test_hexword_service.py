"""Tests for services.shared.hexword_service — Puzzle→Hexword conversion."""

from __future__ import annotations

from unittest.mock import patch

from hexword import ClueGroup, Grid, Hexword

from services.shared.hexword_service import puzzle_to_hexword, puzzle_to_svg
from services.shared.models import Puzzle


class TestPuzzleToHexword:
    """Tests for puzzle_to_hexword() — field mapping."""

    def test_basic_mapping(self):
        puzzle = Puzzle(
            title="Test Puzzle",
            author="Test Author",
            editor="Test Editor",
            instructions="Solve this!",
            solution="The solution.",
        )
        hw = puzzle_to_hexword(puzzle)
        assert isinstance(hw, Hexword)
        assert hw.title == "Test Puzzle"
        assert hw.author == "Test Author"
        assert hw.editor == "Test Editor"
        assert hw.instructions == "Solve this!"
        assert hw.solution == "The solution."

    def test_none_fields_default_to_empty(self):
        """None-able fields should become empty strings in Hexword."""
        puzzle = Puzzle(title="Test", editor=None, instructions=None, solution=None)
        hw = puzzle_to_hexword(puzzle)
        assert hw.editor == ""
        assert hw.instructions == ""
        assert hw.solution == ""

    def test_clue_groups_mapped(self):
        puzzle = Puzzle(
            title="Test",
            clue_groups=[
                ClueGroup(name="Across", clues=[]),
            ],
        )
        hw = puzzle_to_hexword(puzzle)
        assert len(hw.clue_groups) == 1
        assert hw.clue_groups[0].name == "Across"


class TestPuzzleToSvg:
    """Tests for puzzle_to_svg() — SVG rendering."""

    def test_no_grid_returns_none(self):
        puzzle = Puzzle(title="Test")
        result = puzzle_to_svg(puzzle)
        assert result is None

    def test_empty_grid_returns_none(self):
        puzzle = Puzzle(title="Test", grid=Grid(rows=[]))
        result = puzzle_to_svg(puzzle)
        assert result is None

    @patch("services.shared.hexword_service.render_svg")
    def test_valid_grid_returns_svg(self, mock_render):
        mock_render.return_value = "<svg>test</svg>"
        puzzle = Puzzle(
            title="Test",
            grid=Grid(rows=["AB", "CD"]),
        )
        result = puzzle_to_svg(puzzle)
        assert result == "<svg>test</svg>"
        mock_render.assert_called_once()

    @patch("services.shared.hexword_service.render_svg")
    def test_render_error_returns_none(self, mock_render):
        mock_render.side_effect = RuntimeError("render failed")
        puzzle = Puzzle(
            title="Test",
            grid=Grid(rows=["AB"]),
        )
        result = puzzle_to_svg(puzzle)
        assert result is None

    @patch("services.shared.hexword_service.render_svg")
    def test_show_solution_passed_through(self, mock_render):
        mock_render.return_value = "<svg/>"
        puzzle = Puzzle(
            title="Test",
            grid=Grid(rows=["A"]),
        )
        puzzle_to_svg(puzzle, show_solution=True)
        _, kwargs = mock_render.call_args
        assert kwargs["show_solution"] is True
