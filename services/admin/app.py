"""Hex Admin — Flask management UI."""

from __future__ import annotations

import logging
import os

from flask import Flask
from flask_wtf.csrf import CSRFProtect

logger = logging.getLogger(__name__)
csrf = CSRFProtect()


def create_app() -> Flask:
    """Application factory for the Hex admin service."""
    app = Flask(__name__)

    # Configuration
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    app.config["WTF_CSRF_ENABLED"] = os.environ.get("HEX_ENV", "dev") != "test"

    # Extensions
    csrf.init_app(app)

    # Register blueprints
    from .views import main_bp

    app.register_blueprint(main_bp)

    logger.info("Hex admin app initialized", extra={"env": os.environ.get("HEX_ENV", "dev")})

    return app
