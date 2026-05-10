"""Hex Admin — Flask management UI."""

from __future__ import annotations

import logging
import os

from firedantic.configurations import configuration
from flask import Flask, redirect, request, session
from flask_wtf.csrf import CSRFProtect
from google.cloud.firestore_v1 import Client

from .auth import FlaskAuth

logger = logging.getLogger(__name__)
csrf = CSRFProtect()

OAUTH2_CLIENT_CONFIG = os.environ.get("OAUTH2_CLIENT_CONFIG", "")


def create_app() -> Flask:
    """Application factory for the Hex admin service."""
    app = Flask(__name__)

    # Configuration
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    app.config["WTF_CSRF_ENABLED"] = os.environ.get("HEX_ENV", "dev") != "test"

    # Extensions
    csrf.init_app(app)

    # Firestore
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "lukwam-hex")
    db_name = os.environ.get("HEX_DB_NAME", "(default)")
    configuration.add(
        name="(default)",
        project=project,
        database=db_name,
        client=Client(project=project, database=db_name),
    )

    # Register blueprints
    from .views import main_bp

    app.register_blueprint(main_bp)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    auth_enabled = bool(OAUTH2_CLIENT_CONFIG)
    if not auth_enabled:
        logger.warning("OAUTH2_CLIENT_CONFIG not set — auth disabled (dev mode)")

    @app.before_request
    def before_request():
        """Gate every request behind Google OAuth2 (when configured)."""
        # Always allow static files and the OAuth callback
        if request.path.startswith("/static/") or request.path == "/callback":
            return None

        # Always allow logout
        if request.path == "/logout":
            return None

        # If auth is not configured, skip (local dev)
        if not auth_enabled:
            return None

        # Check for a valid session
        if FlaskAuth.validate_user():
            return None

        # Save the original URL for post-login redirect
        session["next_url"] = request.full_path

        # Redirect to Google Sign-In
        authorization_url = FlaskAuth.get_authorization_url()
        return redirect(authorization_url)

    @app.route("/callback")
    def callback():
        """Handle the Google OAuth2 callback."""
        FlaskAuth.handle_callback()
        next_url = session.pop("next_url", "/")
        return redirect(next_url)

    @app.route("/logout")
    def logout():
        """Log out the current user."""
        FlaskAuth.logout()
        return redirect("/")

    logger.info(
        "Hex admin app initialized",
        extra={
            "env": os.environ.get("HEX_ENV", "dev"),
            "project": project,
            "auth": "enabled" if auth_enabled else "disabled",
        },
    )

    return app
