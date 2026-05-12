"""Hex Admin — main views blueprint."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from firedantic_extras import cursor_paginate
from firedantic_extras.query import count_model
from flask import Blueprint, Response, abort, flash, redirect, request, url_for
from hexword import ClueGroup, HexwordService

from ..shared.hexword_service import puzzle_to_svg
from ..shared.models import APIKey, Book, Publication, Puzzle, Solve, User
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
            email=form.email.data,
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
        user.email = form.email.data
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
            name=form.name.data,
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
        publication.name = form.name.data
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
            title=form.title.data,
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
        book.title = form.title.data
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
            title=form.title.data,
            author=form.author.data or "",
            publication=form.publication.data or "",
            number=form.number.data,
            date=form.date.data or "",
            issue=form.issue.data or "",
            editor=form.editor.data or None,
            shape=form.shape.data or "",
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
        puzzle.title = form.title.data
        puzzle.author = form.author.data or ""
        puzzle.publication = form.publication.data or ""
        puzzle.number = form.number.data
        puzzle.date = form.date.data or ""
        puzzle.issue = form.issue.data or ""
        puzzle.editor = form.editor.data or None
        puzzle.shape = form.shape.data or ""
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


def _groups_to_text(puzzle: Puzzle) -> list[_ClueGroupText]:
    """Serialize puzzle's clue groups to editable text blocks."""
    svc = HexwordService()
    result: list[_ClueGroupText] = []
    for group in puzzle.clue_groups:
        lines = [svc.clue_to_string(c) for c in group.clues]
        result.append(_ClueGroupText(name=group.name, text="\n".join(lines)))
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

            clues = []
            for line_num, line in enumerate(raw_text.splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    clues.append(svc.parse_clue(line))
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{name} line {line_num}: {exc}")

            new_groups.append(ClueGroup(name=name, clues=clues))

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


@main_bp.route("/healthz")
def healthz() -> tuple[dict, int]:
    """Health check endpoint."""
    return {"status": "ok"}, 200
