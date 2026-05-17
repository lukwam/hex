"""Hex API — FastAPI read-only puzzle API."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from firedantic.configurations import configuration
from google.cloud.firestore_v1 import Client

from .routers import books, health, publications, puzzles

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Application factory for the Hex API service."""
    # Firestore
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "lukwam-hex")
    db_name = os.environ.get("HEX_DB_NAME", "(default)")
    configuration.add(
        name="(default)",
        project=project,
        database=db_name,
        client=Client(project=project, database=db_name),
    )

    app = FastAPI(
        title="Hex API",
        description="Read-only API for the Cox & Rathvon puzzle archive.",
        version="2.0.0",
    )

    # Health check — no auth required
    app.include_router(health.router)

    # Data routers — API key required (enforced per-router)
    app.include_router(books.router)
    app.include_router(publications.router)
    app.include_router(puzzles.router)

    logger.info(
        "Hex API initialized",
        extra={"project": project, "database": db_name},
    )

    return app
