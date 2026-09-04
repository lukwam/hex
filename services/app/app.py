"""CoxRathvon — Public front-end for the Hex puzzle archive.

A read-only Flask app that displays cryptic crossword puzzles by
Emily Cox and Henry Rathvon. All data comes from the Hex API via
an API key; images are served from the consolidated GCS assets bucket.
"""

from __future__ import annotations

import datetime
import logging
import os

from api_client import HexAPIClient
from flask import Flask, abort, make_response, redirect, render_template, request
from hexword import Hexword, render_svg
from storage import download_blob, get_puzzle_image_urls, get_signed_url

# ── App init ──────────────────────────────────────────────────────

app = Flask(__name__, static_folder="static", static_url_path="/static")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API client — configured via environment variables.
_api = HexAPIClient(
    base_url=os.environ.get("HEX_API_URL", "http://localhost:8081"),
    api_key=os.environ.get("HEX_API_KEY", ""),
)


# ── Template helpers ──────────────────────────────────────────────


@app.context_processor
def inject_globals():
    """Inject the current year into all templates."""
    return {"current_year": datetime.datetime.now().year}


def render_theme(body: str, **kwargs) -> str:
    """Render body content inside the site theme."""
    return render_template("theme.html", body=body, **kwargs)


def _parse_date(date_str: str) -> datetime.datetime | None:
    """Parse a YYYY-MM-DD date string."""
    try:
        return datetime.datetime.strptime(date_str[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _build_hexword(puzzle: dict) -> Hexword | None:
    """Build a Hexword model from API puzzle data for SVG rendering."""
    grid = puzzle.get("grid", {})
    if not grid or not grid.get("rows"):
        return None
    try:
        return Hexword(
            title=puzzle.get("title", ""),
            author=puzzle.get("author", ""),
            editor=puzzle.get("editor", ""),
            instructions=puzzle.get("instructions", ""),
            solution=puzzle.get("solution", ""),
            clue_groups=puzzle.get("clue_groups", []),
            grid=grid,
            settings=puzzle.get("settings", {}),
            unclued=puzzle.get("unclued", []),
        )
    except Exception:
        logger.exception("Failed to build Hexword for %s", puzzle.get("id"))
        return None


# ── Routes ────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Puzzle list with search and filter."""
    puzzles = _api.list_puzzles()

    # Filter to atlantic + wsj only (match current site)
    puzzles = [p for p in puzzles if p.get("publication") in ("atlantic", "wsj")]
    puzzles = sorted(puzzles, key=lambda x: x.get("date", ""), reverse=True)

    # Year ranges per publication
    pub_years: dict[str, list[str]] = {}
    for p in puzzles:
        pub = p.get("publication", "unknown")
        year = str(p.get("date", ""))[:4]
        if pub not in pub_years:
            pub_years[pub] = []
        pub_years[pub].append(year)
    pub_ranges = {}
    for pub, years in pub_years.items():
        pub_ranges[pub] = {"first": min(years), "last": max(years)}

    # Unique years for filter dropdown
    all_years = sorted({str(p.get("date", ""))[:4] for p in puzzles}, reverse=True)

    body = render_template(
        "index.html",
        puzzles=puzzles,
        pub_ranges=pub_ranges,
        years=all_years,
    )
    return render_theme(body)


@app.route("/about")
def about():
    """About page with stats."""
    puzzles = _api.list_puzzles()
    puzzles = [p for p in puzzles if p.get("publication") in ("atlantic", "wsj")]

    stats: dict[str, dict] = {}
    for p in puzzles:
        pub = p.get("publication", "unknown")
        if pub not in stats:
            stats[pub] = {"count": 0, "dates": []}
        stats[pub]["count"] += 1
        stats[pub]["dates"].append(str(p.get("date", ""))[:10])

    for pub in stats:
        dates = sorted(stats[pub]["dates"])
        first = _parse_date(dates[0]) if dates else None
        last = _parse_date(dates[-1]) if dates else None
        if pub == "atlantic":
            stats[pub]["first"] = first.strftime("%B %Y") if first else None
            stats[pub]["last"] = last.strftime("%B %Y") if last else None
        else:
            stats[pub]["first"] = first.strftime("%B %-d, %Y") if first else None
            stats[pub]["last"] = last.strftime("%B %-d, %Y") if last else None
        del stats[pub]["dates"]

    total = len(puzzles)
    all_dates = sorted(str(p.get("date", ""))[:10] for p in puzzles)
    first_year = all_dates[0][:4] if all_dates else ""
    last_year = all_dates[-1][:4] if all_dates else ""

    body = render_template(
        "about.html",
        stats=stats,
        total=total,
        first_year=first_year,
        last_year=last_year,
    )
    return render_theme(body, title="About")


@app.route("/years")
def years_view():
    """Browse puzzles by decade and year."""
    puzzles = _api.list_puzzles()
    puzzles = [p for p in puzzles if p.get("publication") in ("atlantic", "wsj")]

    years: dict[str, list[dict]] = {}
    for p in sorted(puzzles, key=lambda x: x.get("date", "")):
        date = str(p.get("date", ""))[:10]
        year = date.split("-")[0]
        if year not in years:
            years[year] = []
        years[year].append(p)

    decades: dict[str, list[str]] = {}
    for year in years:
        decade = year[:3] + "0s"
        if decade not in decades:
            decades[decade] = []
        decades[decade].append(year)

    body = render_template("years.html", decades=decades, years=years)
    return render_theme(body)


@app.route("/puzzles/<puzzle_id>")
def puzzle_page(puzzle_id: str):
    """Individual puzzle page with image."""
    puzzle = _api.get_puzzle(puzzle_id)
    if not puzzle:
        abort(404)

    pub = puzzle.get("publication", "")
    image_urls = get_puzzle_image_urls(puzzle_id, pub)

    puzzle["date"] = _parse_date(str(puzzle.get("date", "")))

    body = render_template(
        "puzzle.html",
        puzzle=puzzle,
        image_url=image_urls.get("puzzle_png"),
        solution_url=image_urls.get("solution_png"),
    )
    return render_theme(body, title=puzzle.get("title"))


@app.route("/puzzles/<puzzle_id>/pdf")
def puzzle_pdf(puzzle_id: str):
    """Redirect to a signed URL for the puzzle PDF."""
    puzzle = _api.get_puzzle(puzzle_id)
    if not puzzle:
        abort(404)

    pub = puzzle.get("publication", "")
    prefix = f"puzzles/{pub}/{puzzle_id}/{puzzle_id}"
    pdf_url = get_signed_url(f"{prefix}_puzzle.pdf")

    if not pdf_url:
        abort(404)

    if request.args.get("download"):
        # Proxy the download with a friendly filename
        data = download_blob(f"{prefix}_puzzle.pdf")
        if not data:
            abort(404)
        title = puzzle.get("title", puzzle_id)
        date = str(puzzle.get("date", ""))[:10]
        response = make_response(data)
        response.headers["Content-Type"] = "application/pdf"
        response.headers.set(
            "Content-Disposition",
            "attachment",
            filename=f"{date} {title}.pdf",
        )
        return response

    return redirect(pdf_url)


@app.route("/puzzles/<puzzle_id>/svg")
@app.route("/solutions/<puzzle_id>/svg")
def puzzle_svg(puzzle_id: str):
    """Return an SVG rendering of the puzzle or solution grid."""
    puzzle = _api.get_puzzle(puzzle_id)
    if not puzzle:
        abort(404)

    hexword = _build_hexword(puzzle)
    if not hexword:
        abort(404)

    show_solution = "/solutions/" in request.path
    svg = render_svg(hexword, show_solution=show_solution)
    response = make_response(svg)
    response.headers["Content-Type"] = "image/svg+xml"
    return response


@app.route("/puzzles/<puzzle_id>/view")
def puzzle_web_view(puzzle_id: str):
    """Interactive web-rendered puzzle with SVG grid and clues."""
    puzzle = _api.get_puzzle(puzzle_id)
    if not puzzle:
        abort(404)

    hexword = _build_hexword(puzzle)
    if not hexword:
        abort(404)

    body = render_template("web.html", id=puzzle_id, puzzle=hexword)
    title = f"{hexword.title} - Emily Cox & Henry Rathvon"
    return render_theme(body, title=title)


@app.route("/solutions/<puzzle_id>")
def solution_page(puzzle_id: str):
    """Solution image page."""
    puzzle = _api.get_puzzle(puzzle_id)
    if not puzzle:
        abort(404)

    pub = puzzle.get("publication", "")
    image_urls = get_puzzle_image_urls(puzzle_id, pub)

    puzzle["date"] = _parse_date(str(puzzle.get("date", "")))

    body = render_template(
        "solution.html",
        puzzle=puzzle,
        image_url=image_urls.get("solution_png"),
    )
    return render_theme(body, title=f"{puzzle.get('title')} (solution)")


@app.route("/solutions/<puzzle_id>/view")
def solution_web_view(puzzle_id: str):
    """Interactive web-rendered solution with SVG grid and answers.

    ``reveal`` controls how much of each clue's solution is shown:
      - "minimal" (default): just the wordplay explanation (annotation).
      - "answers": explanation plus the plain answer word(s).
      - "full": explanation, answer word(s), and the grid-entry
        manipulation (when it differs from the answer).
    """
    puzzle = _api.get_puzzle(puzzle_id)
    if not puzzle:
        abort(404)

    hexword = _build_hexword(puzzle)
    if not hexword:
        abort(404)

    reveal = request.args.get("reveal", "minimal")
    if reveal not in ("minimal", "answers", "full"):
        reveal = "minimal"

    body = render_template(
        "web_solution.html",
        id=puzzle_id,
        puzzle=hexword,
        reveal=reveal,
        show_answers=reveal in ("answers", "full"),
        show_entries=reveal == "full",
    )
    title = f"{hexword.title} - Emily Cox & Henry Rathvon"
    return render_theme(body, title=title)


@app.route("/healthz")
def healthz():
    """Health check."""
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))  # noqa: S104, S201
