"""Hex Admin — main views blueprint."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from firedantic_extras import cursor_paginate
from firedantic_extras.query import count_model
from flask import Blueprint, abort, flash, redirect, request, url_for
from hexword import ClueGroup, ClueGroupSettings, HexwordService, Grid
from werkzeug.wrappers import Response

from ..shared.hexword_service import puzzle_to_svg
from ..shared.models import APIKey, Book, Publication, Puzzle, Solve, User, StagingPuzzle
from .forms import APIKeyForm, BookForm, PublicationForm, PuzzleForm, UserForm
from .storage import get_cover_url
from .theme import render_theme

main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@main_bp.route("/")
def index() -> Response:
    """Dashboard landing page."""
    stats = {
        "puzzles": count_model(Puzzle),
        "publications": count_model(Publication),
        "books": count_model(Book),
        "users": count_model(User),
        "api_keys": count_model(APIKey),
    }
    return render_theme(
        "index.html",
        page_title="Dashboard",
        active_page="dashboard",
        stats=stats,
    )


@main_bp.route("/publications")
def publications() -> Response:
    """Publications list."""
    items = Publication.find()
    items.sort(key=lambda p: p.name)
    return render_theme(
        "publications.html",
        page_title="Publications",
        active_page="publications",
        publications=items,
    )


@main_bp.route("/books")
def books() -> Response:
    """Books list."""
    items = Book.find()
    items.sort(key=lambda b: b.date or "", reverse=True)
    # Attach cover URLs
    cover_urls = {b.id: get_cover_url(b.id) for b in items}
    return render_theme(
        "books.html",
        page_title="Books",
        active_page="books",
        books=items,
        cover_urls=cover_urls,
    )


@main_bp.route("/users")
def users() -> Response:
    """Users list."""
    items = User.find()
    items.sort(key=lambda u: u.email)
    return render_theme(
        "users.html",
        page_title="Users",
        active_page="users",
        users=items,
    )


@main_bp.route("/puzzles")
def puzzles() -> Response:
    """Puzzles list (all, client-side sort/filter via DataTables)."""
    items = Puzzle.find()
    items.sort(key=lambda p: p.date or "", reverse=True)
    return render_theme(
        "puzzles.html",
        page_title="Puzzles",
        active_page="puzzles",
        puzzles=items,
    )


@main_bp.route("/users/<user_id>")
def user_detail(user_id: str) -> Response:
    """User detail page with solve history."""
    user = User.get_by_id(user_id)
    if not user:
        abort(404)

    # Fetch solves for this user
    user_solves = Solve.find({"user_id": user_id})

    # Build a puzzle lookup for display
    puzzle_ids = {s.puzzle_id for s in user_solves}
    puzzle_map: dict[str, Puzzle] = {}
    for pid in puzzle_ids:
        try:
            p = Puzzle.get_by_id(pid)
            if p:
                puzzle_map[pid] = p
        except Exception:  # noqa: BLE001
            logger.warning("Puzzle %s not found", pid)

    # Pair solves with their puzzles and sort by puzzle date
    solves_with_puzzles = [(s, puzzle_map.get(s.puzzle_id)) for s in user_solves]
    solves_with_puzzles.sort(
        key=lambda sp: (sp[1].date if sp[1] else "") or "",
        reverse=True,
    )

    return render_theme(
        "user_detail.html",
        page_title=user.email,
        active_page="users",
        user=user,
        solves=solves_with_puzzles,
    )


@main_bp.route("/users/new", methods=["GET", "POST"])
def user_create() -> Response:
    """Create a new user."""
    form = UserForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data or "",
            name=form.name.data or "",
            first_name=form.first_name.data or "",
            last_name=form.last_name.data or "",
            admin=form.admin.data,
        )
        user.save()
        flash(f"User {user.email} created.", "success")
        return redirect(url_for("main.user_detail", user_id=user.id))

    return render_theme(
        "user_form.html",
        page_title="New User",
        active_page="users",
        form=form,
        is_new=True,
    )


@main_bp.route("/users/<user_id>/edit", methods=["GET", "POST"])
def user_edit(user_id: str) -> Response:
    """Edit an existing user."""
    user = User.get_by_id(user_id)
    if not user:
        abort(404)

    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.email = form.email.data or ""
        user.name = form.name.data or ""
        user.first_name = form.first_name.data or ""
        user.last_name = form.last_name.data or ""
        user.admin = form.admin.data
        user.save()
        flash(f"User {user.email} updated.", "success")
        return redirect(url_for("main.user_detail", user_id=user.id))

    return render_theme(
        "user_form.html",
        page_title=f"Edit {user.email}",
        active_page="users",
        form=form,
        user=user,
        is_new=False,
    )


@main_bp.route("/users/<user_id>/delete", methods=["GET", "POST"])
def user_delete(user_id: str) -> Response:
    """Delete a user with confirmation."""
    user = User.get_by_id(user_id)
    if not user:
        abort(404)

    if request.method == "POST":
        email = user.email
        user.delete()
        flash(f"User {email} deleted.", "success")
        return redirect(url_for("main.users"))

    return render_theme(
        "user_delete.html",
        page_title=f"Delete {user.email}",
        active_page="users",
        user=user,
    )


def _get_pub_for_puzzle(puzzle: Puzzle) -> Publication | None:
    """Resolve a puzzle's publication code to a Publication model."""
    if not puzzle.publication:
        return None
    results = Publication.find({"code": puzzle.publication})
    return results[0] if results else None


def _publication_choices() -> list[tuple[str, str]]:
    """Build (code, display_name) choices for the publication dropdown."""
    pubs = Publication.find()
    pubs.sort(key=lambda p: p.name)
    choices = [("", "— Select —")]
    choices.extend((p.code, f"{p.name} ({p.code})") for p in pubs if p.code)
    return choices


@main_bp.route("/publications/<pub_id>")
def publication_detail(pub_id: str) -> Response:
    """Publication detail with related puzzles."""
    publication = Publication.get_by_id(pub_id)
    if not publication:
        abort(404)

    # Find puzzles that reference this publication's code
    pub_puzzles: list[Puzzle] = []
    if publication.code:
        pub_puzzles = Puzzle.find({"publication": publication.code})
    pub_puzzles.sort(key=lambda p: p.date or "", reverse=True)

    return render_theme(
        "publication_detail.html",
        page_title=publication.name,
        active_page="publications",
        publication=publication,
        puzzles=pub_puzzles,
    )


@main_bp.route("/publications/new", methods=["GET", "POST"])
def publication_create() -> Response:
    """Create a new publication."""
    form = PublicationForm()
    if form.validate_on_submit():
        publication = Publication(
            name=form.name.data or "",
            code=form.code.data or "",
            url=form.url.data or "",
        )
        publication.save()
        flash(f"Publication '{publication.name}' created.", "success")
        return redirect(url_for("main.publication_detail", pub_id=publication.id))

    return render_theme(
        "publication_form.html",
        page_title="New Publication",
        active_page="publications",
        form=form,
        is_new=True,
    )


@main_bp.route("/publications/<pub_id>/edit", methods=["GET", "POST"])
def publication_edit(pub_id: str) -> Response:
    """Edit an existing publication."""
    publication = Publication.get_by_id(pub_id)
    if not publication:
        abort(404)

    form = PublicationForm(obj=publication)
    if form.validate_on_submit():
        publication.name = form.name.data or ""
        publication.code = form.code.data or ""
        publication.url = form.url.data or ""
        publication.save()
        flash(f"Publication '{publication.name}' updated.", "success")
        return redirect(url_for("main.publication_detail", pub_id=publication.id))

    return render_theme(
        "publication_form.html",
        page_title=f"Edit {publication.name}",
        active_page="publications",
        form=form,
        publication=publication,
        is_new=False,
    )


@main_bp.route("/books/<book_id>")
def book_detail(book_id: str) -> Response:
    """Book detail with related puzzles."""
    book = Book.get_by_id(book_id)
    if not book:
        abort(404)

    # Find puzzles that reference this book's code
    book_puzzles: list[Puzzle] = []
    if book.code:
        book_puzzles = Puzzle.find({"books": {"array_contains": book.code}})
    book_puzzles.sort(key=lambda p: p.date or "", reverse=True)

    cover_url = get_cover_url(book_id)

    return render_theme(
        "book_detail.html",
        page_title=book.title,
        active_page="books",
        book=book,
        puzzles=book_puzzles,
        cover_url=cover_url,
    )


@main_bp.route("/books/new", methods=["GET", "POST"])
def book_create() -> Response:
    """Create a new book."""
    form = BookForm()
    if form.validate_on_submit():
        book = Book(
            title=form.title.data or "",
            code=form.code.data or "",
            date=form.date.data or "",
            publisher=form.publisher.data or "",
            source=form.source.data or "",
            isbn_10=form.isbn_10.data or "",
            isbn_13=form.isbn_13.data or "",
            amazon_link=form.amazon_link.data or "",
            notes=form.notes.data or "",
        )
        book.save()
        flash(f"Book '{book.title}' created.", "success")
        return redirect(url_for("main.book_detail", book_id=book.id))

    return render_theme(
        "book_form.html",
        page_title="New Book",
        active_page="books",
        form=form,
        is_new=True,
    )


@main_bp.route("/books/<book_id>/edit", methods=["GET", "POST"])
def book_edit(book_id: str) -> Response:
    """Edit an existing book."""
    book = Book.get_by_id(book_id)
    if not book:
        abort(404)

    form = BookForm(obj=book)
    if form.validate_on_submit():
        book.title = form.title.data or ""
        book.code = form.code.data or ""
        book.date = form.date.data or ""
        book.publisher = form.publisher.data or ""
        book.source = form.source.data or ""
        book.isbn_10 = form.isbn_10.data or ""
        book.isbn_13 = form.isbn_13.data or ""
        book.amazon_link = form.amazon_link.data or ""
        book.notes = form.notes.data or ""
        book.save()
        flash(f"Book '{book.title}' updated.", "success")
        return redirect(url_for("main.book_detail", book_id=book.id))

    return render_theme(
        "book_form.html",
        page_title=f"Edit {book.title}",
        active_page="books",
        form=form,
        book=book,
        is_new=False,
    )


@main_bp.route("/puzzles/<puzzle_id>")
def puzzle_detail(puzzle_id: str) -> Response:
    """Puzzle detail with publication and book cross-references."""
    puzzle = Puzzle.get_by_id(puzzle_id)
    if not puzzle:
        abort(404)

    publication = _get_pub_for_puzzle(puzzle)

    # Resolve book codes to Book objects
    book_map: dict[str, Book] = {}
    for code in puzzle.books:
        if code:
            results = Book.find({"code": code})
            if results:
                book_map[code] = results[0]

    # Prev/next: one-item pages in each direction from this puzzle
    prev_page = cursor_paginate(
        Puzzle,
        limit=1,
        cursor=puzzle_id,
        direction="prev",
        order_by=[("date", "DESCENDING")],
    )
    next_page = cursor_paginate(
        Puzzle,
        limit=1,
        cursor=puzzle_id,
        direction="next",
        order_by=[("date", "DESCENDING")],
    )
    prev_puzzle = prev_page.items[0] if prev_page.items else None
    next_puzzle = next_page.items[0] if next_page.items else None

    # Render SVG grids
    puzzle_svg = puzzle_to_svg(puzzle, show_solution=False)
    solution_svg = puzzle_to_svg(puzzle, show_solution=True)

    # Generate signed URLs for puzzle files
    from services.admin.storage import get_puzzle_file_urls

    file_urls = get_puzzle_file_urls(puzzle)

    return render_theme(
        "puzzle_detail.html",
        page_title=puzzle.title,
        active_page="puzzles",
        puzzle=puzzle,
        publication=publication,
        book_map=book_map,
        prev_puzzle=prev_puzzle,
        next_puzzle=next_puzzle,
        puzzle_svg=puzzle_svg,
        solution_svg=solution_svg,
        file_urls=file_urls,
    )


@main_bp.route("/puzzles/new", methods=["GET", "POST"])
def puzzle_create() -> Response:
    """Create a new puzzle."""
    form = PuzzleForm()
    form.publication.choices = _publication_choices()
    if form.validate_on_submit():
        puzzle = Puzzle(
            title=form.title.data or "",
            author=form.author.data or "",
            publication=form.publication.data or "",
            number=form.number.data,
            date=form.date.data or "",
            issue=form.issue.data or "",
            editor=form.editor.data or None,
            shape=form.shape.data or "",
            instructions=form.instructions.data or "",
            solution=form.solution.data or "",
        )
        puzzle.save()
        flash(f"Puzzle '{puzzle.title}' created.", "success")
        return redirect(url_for("main.puzzle_detail", puzzle_id=puzzle.id))

    return render_theme(
        "puzzle_form.html",
        page_title="New Puzzle",
        active_page="puzzles",
        form=form,
        is_new=True,
    )


@main_bp.route("/puzzles/<puzzle_id>/edit", methods=["GET", "POST"])
def puzzle_edit(puzzle_id: str) -> Response:
    """Edit an existing puzzle's metadata."""
    puzzle = Puzzle.get_by_id(puzzle_id)
    if not puzzle:
        abort(404)

    form = PuzzleForm(obj=puzzle)
    form.publication.choices = _publication_choices()
    if form.validate_on_submit():
        puzzle.title = form.title.data or ""
        puzzle.author = form.author.data or ""
        puzzle.publication = form.publication.data or ""
        puzzle.number = form.number.data
        puzzle.date = form.date.data or ""
        puzzle.issue = form.issue.data or ""
        puzzle.editor = form.editor.data or None
        puzzle.shape = form.shape.data or ""
        puzzle.instructions = form.instructions.data or ""
        puzzle.solution = form.solution.data or ""
        puzzle.save()
        flash(f"Puzzle '{puzzle.title}' updated.", "success")
        return redirect(url_for("main.puzzle_detail", puzzle_id=puzzle.id))

    return render_theme(
        "puzzle_form.html",
        page_title=f"Edit {puzzle.title}",
        active_page="puzzles",
        form=form,
        puzzle=puzzle,
        is_new=False,
    )


@main_bp.route("/puzzles/<puzzle_id>/delete", methods=["GET", "POST"])
def puzzle_delete(puzzle_id: str) -> Response:
    """Delete a puzzle with confirmation."""
    puzzle = Puzzle.get_by_id(puzzle_id)
    if not puzzle:
        abort(404)

    if request.method == "POST":
        title = puzzle.title
        puzzle.delete()
        flash(f"Puzzle '{title}' deleted.", "success")
        return redirect(url_for("main.puzzles"))

    return render_theme(
        "puzzle_delete.html",
        page_title=f"Delete {puzzle.title}",
        active_page="puzzles",
        puzzle=puzzle,
    )


@dataclass
class _ClueGroupText:
    """Lightweight container for template rendering."""

    name: str = ""
    text: str = ""
    show_grid_labels: bool = True
    show_enumerations: str = ""
    show_grid_entries: bool = True
    reverse_grid_entries: bool = False


def _groups_to_text(puzzle: Puzzle) -> list[_ClueGroupText]:
    """Serialize puzzle's clue groups to editable text blocks."""
    svc = HexwordService()
    result: list[_ClueGroupText] = []
    for group in puzzle.clue_groups:
        lines = [svc.clue_to_string(c) for c in group.clues]
        settings = group.settings
        result.append(
            _ClueGroupText(
                name=group.name,
                text="\n".join(lines),
                show_grid_labels=settings.show_grid_labels if settings else True,
                show_enumerations=settings.show_enumerations if settings else "",
                show_grid_entries=settings.show_grid_entries if settings else True,
                reverse_grid_entries=settings.reverse_grid_entries if settings else False,
            )
        )
    return result or [_ClueGroupText(name="Across"), _ClueGroupText(name="Down")]


@main_bp.route("/puzzles/<puzzle_id>/clues", methods=["GET", "POST"])
def puzzle_clues(puzzle_id: str) -> Response:
    """Edit a puzzle's clue groups using tilde-delimited text."""
    puzzle = Puzzle.get_by_id(puzzle_id)
    if not puzzle:
        abort(404)

    if request.method == "POST":
        svc = HexwordService()
        group_count = int(request.form.get("group_count", 0))
        new_groups: list[ClueGroup] = []
        errors: list[str] = []

        for i in range(group_count):
            name = request.form.get(f"group_{i}_name", "").strip()
            raw_text = request.form.get(f"group_{i}_clues", "").strip()
            if not name:
                continue

            show_grid_labels = request.form.get(f"group_{i}_show_grid_labels") == "on"
            show_enumerations = request.form.get(f"group_{i}_show_enumerations", "").strip()
            show_grid_entries = request.form.get(f"group_{i}_show_grid_entries") == "on"
            reverse_grid_entries = request.form.get(f"group_{i}_reverse_grid_entries") == "on"

            settings = ClueGroupSettings(
                show_grid_labels=show_grid_labels,
                show_enumerations=show_enumerations,
                show_grid_entries=show_grid_entries,
                reverse_grid_entries=reverse_grid_entries,
            )

            clues = []
            for line_num, line in enumerate(raw_text.splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    clues.append(svc.parse_clue(line))
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{name} line {line_num}: {exc}")

            new_groups.append(ClueGroup(name=name, clues=clues, settings=settings))

        if errors:
            for err in errors:
                flash(err, "danger")
            # Re-render with submitted data so the user doesn't lose work
            groups = []
            for i in range(group_count):
                groups.append(
                    _ClueGroupText(
                        name=request.form.get(f"group_{i}_name", ""),
                        text=request.form.get(f"group_{i}_clues", ""),
                        show_grid_labels=request.form.get(f"group_{i}_show_grid_labels") == "on",
                        show_enumerations=request.form.get(f"group_{i}_show_enumerations", "").strip(),
                        show_grid_entries=request.form.get(f"group_{i}_show_grid_entries") == "on",
                        reverse_grid_entries=request.form.get(f"group_{i}_reverse_grid_entries") == "on",
                    )
                )
            return render_theme(
                "puzzle_clues.html",
                page_title=f"Edit Clues — {puzzle.title}",
                active_page="puzzles",
                puzzle=puzzle,
                groups=groups,
            )

        puzzle.clue_groups = new_groups
        puzzle.save()
        total = sum(len(g.clues) for g in new_groups)
        flash(
            f"Saved {len(new_groups)} group(s), {total} clue(s).",
            "success",
        )
        return redirect(url_for("main.puzzle_detail", puzzle_id=puzzle.id))

    # GET — serialize existing clue groups to text
    groups = _groups_to_text(puzzle)
    return render_theme(
        "puzzle_clues.html",
        page_title=f"Edit Clues — {puzzle.title}",
        active_page="puzzles",
        puzzle=puzzle,
        groups=groups,
    )


# ── API Keys ──────────────────────────────────────────────────────────


@main_bp.route("/api-keys")
def api_keys() -> Response:
    """List all API keys."""
    keys = APIKey.find({})
    return render_theme(
        "api_keys.html",
        page_title="API Keys",
        active_page="api_keys",
        api_keys=keys,
    )


@main_bp.route("/api-keys/create", methods=["GET", "POST"])
def api_key_create() -> Response:
    """Create a new API key."""
    form = APIKeyForm()
    if form.validate_on_submit():
        key_id = str(uuid.uuid4())
        api_key = APIKey(description=form.description.data or "")
        api_key.id = key_id  # type: ignore[assignment]
        api_key.save()
        flash(f"API key created: {key_id[:8]}…{key_id[-4:]}", "success")
        return redirect(url_for("main.api_key_detail", api_key_id=key_id))
    return render_theme(
        "api_key_form.html",
        page_title="Create API Key",
        active_page="api_keys",
        form=form,
    )


@main_bp.route("/api-keys/<api_key_id>")
def api_key_detail(api_key_id: str) -> Response:
    """View an API key."""
    from firedantic import ModelNotFoundError

    try:
        api_key = APIKey.get_by_id(api_key_id)
    except ModelNotFoundError:
        abort(404)
    return render_theme(
        "api_key_detail.html",
        page_title="API Key",
        active_page="api_keys",
        api_key=api_key,
    )


@main_bp.route("/api-keys/<api_key_id>/delete", methods=["POST"])
def api_key_delete(api_key_id: str) -> Response:
    """Delete an API key."""
    from firedantic import ModelNotFoundError

    try:
        api_key = APIKey.get_by_id(api_key_id)
    except ModelNotFoundError:
        abort(404)
    api_key.delete()
    flash(f"API key deleted: {api_key_id[:8]}…{api_key_id[-4:]}", "success")
    return redirect(url_for("main.api_keys"))


@main_bp.route("/puzzles/staging")
def puzzles_staging() -> Response:
    """List of all puzzles currently in the staging area awaiting review."""
    items = StagingPuzzle.find()
    # Sort by extraction time, newest first
    items.sort(key=lambda p: p.extracted_at or datetime.min, reverse=True)
    return render_theme(
        "puzzles_staging.html",
        page_title="Staging Area",
        active_page="staging",
        puzzles=items,
    )


@main_bp.route("/puzzles/staging/<puzzle_id>/review", methods=["GET", "POST"])
def puzzle_review(puzzle_id: str) -> Response:
    """Side-by-side review of a staged puzzle, allowing editing and approval."""
    from firedantic import ModelNotFoundError

    try:
        staging_puzzle = StagingPuzzle.get_by_id(puzzle_id)
    except ModelNotFoundError:
        abort(404)

    # Fetch live puzzle metadata for comparison/reference
    live_puzzle = None
    try:
        live_puzzle = Puzzle.get_by_id(puzzle_id)
    except ModelNotFoundError:
        pass

    if request.method == "POST":
        action = request.form.get("action", "save_draft")
        
        # 1. Parse and update metadata
        staging_puzzle.title = request.form.get("title", "").strip() or staging_puzzle.title
        staging_puzzle.author = request.form.get("author", "").strip()
        staging_puzzle.publication = request.form.get("publication", "").strip()
        
        num_raw = request.form.get("number", "").strip()
        staging_puzzle.number = int(num_raw) if num_raw.isdigit() else None
        
        staging_puzzle.date = request.form.get("date", "").strip()
        staging_puzzle.issue = request.form.get("issue", "").strip()
        staging_puzzle.editor = request.form.get("editor", "").strip() or None
        staging_puzzle.shape = request.form.get("shape", "").strip()
        staging_puzzle.instructions = request.form.get("instructions", "").strip() or None
        staging_puzzle.solution = request.form.get("solution", "").strip() or None

        # 1.5 Parse and update grid rows, columns, and style
        grid_rows_raw = request.form.get("grid_rows", "").strip()
        grid_cols_raw = request.form.get("grid_columns", "").strip()
        grid_style_raw = request.form.get("grid_style", "").strip()

        new_rows = [line.strip() for line in grid_rows_raw.splitlines() if line.strip()]
        new_cols = [line.strip() for line in grid_cols_raw.splitlines() if line.strip()]
        new_style = [line.strip() for line in grid_style_raw.splitlines() if line.strip()]
        
        staging_puzzle.grid = Grid(
            rows=new_rows,
            columns=new_cols,
            style=new_style,
            solution_style=new_style,
            styles=staging_puzzle.grid.styles,
            solution_rows=new_rows,
            solution_columns=new_cols,
            entry_rows=staging_puzzle.grid.entry_rows,
            entry_columns=staging_puzzle.grid.entry_columns
        )

        # 1.6 Parse grid styles JSON (maps mask characters to visual properties)
        grid_styles_raw = request.form.get("grid_styles", "").strip()
        if grid_styles_raw:
            try:
                import json
                from hexword.models import GridStyle

                styles_dict = json.loads(grid_styles_raw)
                staging_puzzle.grid.styles = {
                    k: GridStyle(**v) if isinstance(v, dict) else v
                    for k, v in styles_dict.items()
                }
            except (json.JSONDecodeError, Exception) as exc:
                flash(f"Invalid grid styles JSON: {exc}", "danger")

        # 2. Parse tilde-delimited clue groups
        svc = HexwordService()
        group_count = int(request.form.get("group_count", 0))
        new_groups: list[ClueGroup] = []
        errors: list[str] = []

        for i in range(group_count):
            name = request.form.get(f"group_{i}_name", "").strip()
            raw_text = request.form.get(f"group_{i}_clues", "").strip()
            if not name:
                continue

            show_grid_labels = request.form.get(f"group_{i}_show_grid_labels") == "on"
            show_enumerations = request.form.get(f"group_{i}_show_enumerations", "").strip()
            show_grid_entries = request.form.get(f"group_{i}_show_grid_entries") == "on"
            reverse_grid_entries = request.form.get(f"group_{i}_reverse_grid_entries") == "on"

            settings = ClueGroupSettings(
                show_grid_labels=show_grid_labels,
                show_enumerations=show_enumerations,
                show_grid_entries=show_grid_entries,
                reverse_grid_entries=reverse_grid_entries,
            )

            clues = []
            for line_num, line in enumerate(raw_text.splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    clues.append(svc.parse_clue(line))
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{name} line {line_num}: {exc}")

            new_groups.append(ClueGroup(name=name, clues=clues, settings=settings))

        if errors:
            for err in errors:
                flash(err, "danger")
            # Re-render with submitted draft data on error
            groups = []
            for i in range(group_count):
                groups.append(
                    _ClueGroupText(
                        name=request.form.get(f"group_{i}_name", ""),
                        text=request.form.get(f"group_{i}_clues", ""),
                        show_grid_labels=request.form.get(f"group_{i}_show_grid_labels") == "on",
                        show_enumerations=request.form.get(f"group_{i}_show_enumerations", "").strip(),
                        show_grid_entries=request.form.get(f"group_{i}_show_grid_entries") == "on",
                        reverse_grid_entries=request.form.get(f"group_{i}_reverse_grid_entries") == "on",
                    )
                )
            
            # Generate file URLs
            from services.admin.storage import get_puzzle_file_urls
            file_urls = get_puzzle_file_urls(staging_puzzle)

            return render_theme(
                "puzzle_review.html",
                page_title=f"Review — {staging_puzzle.title}",
                active_page="staging",
                puzzle=staging_puzzle,
                groups=groups,
                file_urls=file_urls,
            )

        if action in ("preview", "preview_solution"):
            temp_puzzle = StagingPuzzle(
                id=puzzle_id,
                title=staging_puzzle.title,
                author=staging_puzzle.author,
                publication=staging_puzzle.publication,
                number=staging_puzzle.number,
                date=staging_puzzle.date,
                issue=staging_puzzle.issue,
                editor=staging_puzzle.editor,
                shape=staging_puzzle.shape,
                instructions=staging_puzzle.instructions,
                solution=staging_puzzle.solution,
                clue_groups=new_groups,
                grid=staging_puzzle.grid,
                settings=staging_puzzle.settings,
                unclued=staging_puzzle.unclued,
                files=staging_puzzle.files,
                links=staging_puzzle.links,
            )
            show_solution = (action == "preview_solution")
            svg_data = puzzle_to_svg(temp_puzzle, show_solution=show_solution)
            
            preview_title = f"Solution Preview — {temp_puzzle.title}" if show_solution else f"Solver Preview — {temp_puzzle.title}"
            return render_theme(
                "puzzle_preview.html",
                page_title=preview_title,
                active_page="staging",
                puzzle=temp_puzzle,
                svg_data=svg_data,
                show_solution=show_solution,
            )

        # Update clue groups
        staging_puzzle.clue_groups = new_groups
        staging_puzzle.save()

        # Handle Action: Promote to Live
        if action == "approve" and live_puzzle:
            live_puzzle.title = staging_puzzle.title
            live_puzzle.author = staging_puzzle.author
            live_puzzle.publication = staging_puzzle.publication
            live_puzzle.number = staging_puzzle.number
            live_puzzle.date = staging_puzzle.date
            live_puzzle.issue = staging_puzzle.issue
            live_puzzle.editor = staging_puzzle.editor
            live_puzzle.shape = staging_puzzle.shape
            live_puzzle.instructions = staging_puzzle.instructions
            live_puzzle.solution = staging_puzzle.solution
            live_puzzle.clue_groups = staging_puzzle.clue_groups
            live_puzzle.grid = staging_puzzle.grid
            live_puzzle.settings = staging_puzzle.settings
            live_puzzle.unclued = staging_puzzle.unclued
            live_puzzle.save()
            
            # Remove from staging area
            staging_puzzle.delete()
            
            flash(
                f"Puzzle '{live_puzzle.title}' successfully validated, approved, and imported to live!",
                "success",
            )
            return redirect(url_for("main.puzzles_staging"))

        flash("Staging draft successfully saved.", "success")
        return redirect(url_for("main.puzzle_review", puzzle_id=puzzle_id))

    # GET request: load and format
    groups = _groups_to_text(staging_puzzle)
    
    # Generate file URLs for the puzzle (PDF/PNG review)
    from services.admin.storage import get_puzzle_file_urls
    file_urls = get_puzzle_file_urls(staging_puzzle)

    # Serialize grid styles for the JSON textarea (must use aliases like "background-color")
    import json
    grid_styles_json = "{}"
    if staging_puzzle.grid.styles:
        grid_styles_json = json.dumps(
            {k: v.model_dump(by_alias=True, exclude_none=True) for k, v in staging_puzzle.grid.styles.items()},
            indent=2,
        )

    return render_theme(
        "puzzle_review.html",
        page_title=f"Review — {staging_puzzle.title}",
        active_page="staging",
        puzzle=staging_puzzle,
        groups=groups,
        file_urls=file_urls,
        grid_styles_json=grid_styles_json,
    )


@main_bp.route("/puzzles/staging/<puzzle_id>/discard", methods=["POST"])
def puzzle_discard(puzzle_id: str) -> Response:
    """Discard a puzzle from the staging area without publishing it."""
    from firedantic import ModelNotFoundError

    try:
        staging_puzzle = StagingPuzzle.get_by_id(puzzle_id)
    except ModelNotFoundError:
        abort(404)

    title = staging_puzzle.title
    staging_puzzle.delete()
    flash(f"Staged puzzle '{title}' discarded successfully.", "info")
    return redirect(url_for("main.puzzles_staging"))


@main_bp.route("/puzzles/<puzzle_id>/pdf")
def puzzle_pdf(puzzle_id: str) -> Response:
    """Generate a single-page PDF for a live puzzle."""
    puzzle = Puzzle.get_by_id(puzzle_id)
    if not puzzle:
        abort(404)

    show_solution = request.args.get("solution", "").lower() in ("1", "true", "yes")
    columns = int(request.args.get("columns", 2))
    reveal = request.args.get("reveal", "minimal")

    from services.shared.pdf_service import generate_pdf

    pdf_bytes = generate_pdf(puzzle, show_solution=show_solution, reveal=reveal, columns=columns)

    filename = f"{puzzle.title or puzzle_id}"
    if show_solution:
        filename += " - Solution"
    filename += ".pdf"

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@main_bp.route("/puzzles/staging/<puzzle_id>/pdf")
def staging_puzzle_pdf(puzzle_id: str) -> Response:
    """Generate a single-page PDF for a staged puzzle."""
    from firedantic import ModelNotFoundError

    try:
        puzzle = StagingPuzzle.get_by_id(puzzle_id)
    except ModelNotFoundError:
        abort(404)

    show_solution = request.args.get("solution", "").lower() in ("1", "true", "yes")
    columns = int(request.args.get("columns", 2))
    reveal = request.args.get("reveal", "minimal")

    from services.shared.pdf_service import generate_pdf

    pdf_bytes = generate_pdf(puzzle, show_solution=show_solution, reveal=reveal, columns=columns)

    filename = f"{puzzle.title or puzzle_id}"
    if show_solution:
        filename += " - Solution"
    filename += ".pdf"

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@main_bp.route("/health")
def health() -> tuple[dict, int]:
    """Health check endpoint.

    Named "/health" rather than "/healthz" — Cloud Run's shared front-end
    infrastructure intercepts the exact literal path "/healthz" before it
    reaches any container, always returning a generic Google 404 regardless
    of what the app defines there.
    """
    return {"status": "ok"}, 200
