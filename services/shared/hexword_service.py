"""Hex — Hexword conversion service.

Converts Hex Puzzle (Firedantic) models into Hexword (library) models
so they can be rendered as SVG or otherwise processed by the hexword library.
"""

from __future__ import annotations

import logging

from hexword import Hexword, render_svg

from .models import Puzzle

logger = logging.getLogger(__name__)


def puzzle_to_hexword(puzzle: Puzzle) -> Hexword:
    """Convert a Hex Puzzle into a Hexword model.

    The Puzzle model is a superset of Hexword (it adds metadata like
    publication, date, links, files, etc.). This extracts only the
    hexword-relevant fields for rendering and analysis.
    """
    return Hexword(
        title=puzzle.title,
        author=puzzle.author,
        editor=puzzle.editor or "",
        instructions=puzzle.instructions or "",
        solution=puzzle.solution or "",
        clue_groups=puzzle.clue_groups,
        grid=puzzle.grid,
        settings=puzzle.settings,
        unclued=puzzle.unclued,
    )


def puzzle_to_svg(puzzle: Puzzle, show_solution: bool = False) -> str | None:
    """Render a Puzzle's grid as an SVG string.

    Returns None if the puzzle has no grid data.
    """
    if not puzzle.grid or not puzzle.grid.rows:
        return None

    try:
        hexword = puzzle_to_hexword(puzzle)
        return render_svg(hexword, show_solution=show_solution)
    except Exception:
        logger.exception("Failed to render SVG for puzzle %s (%s)", puzzle.id, puzzle.title)
        return None
