"""Root conftest — shared fixtures for Hex v2 tests."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

# Set testing flag to prevent real service initialization.
os.environ["TESTING"] = "1"

# ---------------------------------------------------------------------------
# Environment defaults — prevent tests from touching real GCP resources
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _env_defaults(monkeypatch):
    """Set safe environment defaults for all tests."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("HEX_ENV", "test")
    monkeypatch.setenv("HEX_DB_NAME", "(default)")


# ---------------------------------------------------------------------------
# Mock Firestore — prevent any real Firestore access
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_firestore():
    """Patch firedantic configuration so no real Firestore client is created."""
    mock_config = MagicMock()
    with patch("firedantic.configurations.configuration", mock_config):
        yield mock_config


# ---------------------------------------------------------------------------
# Flask test client
# ---------------------------------------------------------------------------


@pytest.fixture()
def app():
    """Create a Flask app instance for testing."""
    # Provide a dummy OAuth config so auth module doesn't complain
    os.environ["OAUTH2_CLIENT_CONFIG"] = '{"web": {"client_id": "test"}}'

    from services.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    yield app

    os.environ.pop("OAUTH2_CLIENT_CONFIG", None)


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()
