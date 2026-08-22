"""Hex — PDF generation service.

Renders puzzles as single-page US Letter PDFs using WeasyPrint.
Supports both solver (empty grid + clues) and solution (filled grid + annotations) modes.

Template variables
------------------
The Jinja2 template receives:
    puzzle          Puzzle model instance
    svg_data        SVG string of the rendered grid
    show_solution   bool — solver vs. solution mode
    columns         int — number of clue columns (2 or 3)
    font_size       float — base font size in pt
    grid_max_width  str — CSS max-width for the grid container
"""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .hexword_service import puzzle_to_svg
from .models import Puzzle

logger = logging.getLogger(__name__)

# Template directory lives alongside this module
_TEMPLATE_DIR = Path(__file__).parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=False,  # SVG content must not be escaped
)

# Defaults
DEFAULT_FONT_SIZE = 9.0  # pt — readable for clues, fits most puzzles
DEFAULT_COLUMNS = 2
DEFAULT_GRID_MAX_WIDTH = "55%"


def generate_pdf(
    puzzle: Puzzle,
    *,
    show_solution: bool = False,
    columns: int | None = None,
    font_size: float | None = None,
    grid_max_width: str | None = None,
    auto_fit: bool = True,
) -> bytes:
    """Render a puzzle as a single-page US Letter PDF.

    Parameters
    ----------
    puzzle : Puzzle
        The puzzle to render.
    show_solution : bool
        If True, render the filled grid with answers and annotations.
    columns : int
        Number of clue columns (2 or 3). Defaults to 2.
    font_size : float
        Base clue font size in pt. Defaults to 9.0.
    grid_max_width : str
        CSS max-width for the grid SVG. Defaults to "55%".
    auto_fit : bool
        If True, progressively shrink font size until content fits
        on a single page. Starts from ``font_size`` and decreases by
        0.5 pt per attempt, down to a minimum of 6.5 pt.

    Returns
    -------
    bytes
        The generated PDF file contents.
    """
    import weasyprint

    cols = columns or DEFAULT_COLUMNS
    fs = font_size or DEFAULT_FONT_SIZE
    gw = grid_max_width or DEFAULT_GRID_MAX_WIDTH

    # Render the SVG grid
    svg_data = puzzle_to_svg(puzzle, show_solution=show_solution)

    # WeasyPrint ignores CSS max-height on inline SVGs. We must set explicit
    # width/height attributes based on the desired print size.
    # Target: grid height ≈ 3.2 inches (230pt) to leave room for clues.
    if svg_data:
        import re

        vb_match = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg_data)
        if vb_match:
            vb_w, vb_h = int(vb_match.group(1)), int(vb_match.group(2))
            target_height_pt = 230  # ~3.2 inches
            scale = target_height_pt / vb_h
            new_w = round(vb_w * scale)
            new_h = target_height_pt
            # Replace width/height attributes with explicit pt values
            svg_data = re.sub(r'width="[^"]*"', f'width="{new_w}pt"', svg_data, count=1)
            svg_data = re.sub(r'height="[^"]*"', f'height="{new_h}pt"', svg_data, count=1)

    template = _jinja_env.get_template("puzzle_pdf.html")

    if not auto_fit:
        html_str = template.render(
            puzzle=puzzle,
            svg_data=svg_data,
            show_solution=show_solution,
            columns=cols,
            font_size=fs,
            grid_max_width=gw,
        )
        return weasyprint.HTML(string=html_str).write_pdf()

    # Auto-fit: shrink font until the PDF is a single page
    min_font = 6.5
    step = 0.5
    current_fs = fs

    while current_fs >= min_font:
        html_str = template.render(
            puzzle=puzzle,
            svg_data=svg_data,
            show_solution=show_solution,
            columns=cols,
            font_size=current_fs,
            grid_max_width=gw,
        )
        doc = weasyprint.HTML(string=html_str).render()
        if len(doc.pages) <= 1:
            logger.info(
                "PDF for '%s' (%s) fits at %.1f pt with %d columns",
                puzzle.title,
                "solution" if show_solution else "puzzle",
                current_fs,
                cols,
            )
            return doc.write_pdf()

        logger.debug(
            "PDF for '%s' overflows at %.1f pt (%d pages), shrinking…",
            puzzle.title,
            current_fs,
            len(doc.pages),
        )
        current_fs -= step

    # If we can't fit even at minimum font, return the smallest version
    logger.warning(
        "PDF for '%s' still overflows at minimum font (%.1f pt). "
        "Consider using 3 columns.",
        puzzle.title,
        min_font,
    )
    html_str = template.render(
        puzzle=puzzle,
        svg_data=svg_data,
        show_solution=show_solution,
        columns=cols,
        font_size=min_font,
        grid_max_width=gw,
    )
    return weasyprint.HTML(string=html_str).write_pdf()
