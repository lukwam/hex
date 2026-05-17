"""Hex Admin — template rendering helpers."""

from __future__ import annotations

import os

from flask import make_response, render_template
from werkzeug.wrappers import Response


def render_theme(template: str, *, page_title: str = "", active_page: str = "", **kwargs) -> Response:
    """Render a template within the Hex Admin theme.

    Injects common context variables (env, project, page_title)
    so individual routes don't need to repeat them.

    Args:
        template:    Template filename (e.g. "index.html").
        page_title:  Shown in <title> and as an <h1> heading.
        active_page: Sidebar nav item to highlight (e.g. "puzzles").
        **kwargs:    Additional template variables.
    """
    return make_response(
        render_template(
            template,
            page_title=page_title,
            active_page=active_page,
            env=os.environ.get("HEX_ENV", "dev"),
            project=os.environ.get("GOOGLE_CLOUD_PROJECT", "lukwam-hex"),
            **kwargs,
        )
    )
