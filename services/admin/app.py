"""Hex Admin — Flask management UI."""

from __future__ import annotations

import logging
import os

from firedantic.configurations import configuration
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from google.cloud.firestore_v1 import Client

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

    logger.info(
        "Hex admin app initialized",
        extra={"env": os.environ.get("HEX_ENV", "dev"), "project": project},
    )

    return app
