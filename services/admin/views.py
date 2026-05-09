"""Hex Admin — main views blueprint."""

from __future__ import annotations

from flask import Blueprint, render_template

from ..shared.repo import PuzzleRepo

main_bp = Blueprint("main", __name__)

_repo = PuzzleRepo()


@main_bp.route("/")
def index() -> str:
    """Landing page."""
    return render_template("index.html")


@main_bp.route("/healthz")
def healthz() -> tuple[dict, int]:
    """Health check endpoint."""
    return {"status": "ok"}, 200
