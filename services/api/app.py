"""Hex API — FastAPI read-only puzzle API."""

from __future__ import annotations

from fastapi import FastAPI

from .routers import books, health, publications, puzzles


def create_app() -> FastAPI:
    """Application factory for the Hex API service."""
    app = FastAPI(
        title="Hex API",
        description="Read-only API for the Cox & Rathvon puzzle archive.",
        version="2.0.0",
    )

    app.include_router(health.router)
    app.include_router(books.router)
    app.include_router(publications.router)
    app.include_router(puzzles.router)

    return app
