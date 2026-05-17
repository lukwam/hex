"""Tests for services.api.auth — API key dependency."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from services.api.auth import require_api_key
from services.shared.models import APIKey

# Build a minimal FastAPI app with a protected and unprotected endpoint.
_app = FastAPI()


@_app.get("/protected")
async def _protected(key: APIKey = Depends(require_api_key)) -> dict:  # noqa: B008
    return {"key_id": key.id}


@_app.get("/health")
async def _health() -> dict:
    return {"status": "ok"}


@pytest.fixture()
def api_client():
    return TestClient(_app)


class TestRequireApiKey:
    """Tests for the require_api_key FastAPI dependency."""

    def test_missing_key_returns_401(self, api_client):
        resp = api_client.get("/protected")
        assert resp.status_code == 401
        assert "Missing API key" in resp.json()["detail"]

    def test_empty_header_returns_401(self, api_client):
        resp = api_client.get("/protected", headers={"X-API-Key": ""})
        assert resp.status_code == 401

    def test_invalid_key_returns_401(self, api_client):
        with patch("services.api.auth.APIKey") as mock_cls:
            from firedantic import ModelNotFoundError

            mock_cls.get_by_id.side_effect = ModelNotFoundError()
            resp = api_client.get("/protected", headers={"X-API-Key": "bad-key"})
            assert resp.status_code == 401
            assert "Invalid API key" in resp.json()["detail"]

    def test_valid_header_key(self, api_client):
        fake_key = MagicMock(spec=APIKey)
        fake_key.id = "abc123"
        with patch("services.api.auth.APIKey") as mock_cls:
            mock_cls.get_by_id.return_value = fake_key
            resp = api_client.get("/protected", headers={"X-API-Key": "abc123"})
            assert resp.status_code == 200
            assert resp.json() == {"key_id": "abc123"}

    def test_valid_query_key(self, api_client):
        fake_key = MagicMock(spec=APIKey)
        fake_key.id = "qp-key"
        with patch("services.api.auth.APIKey") as mock_cls:
            mock_cls.get_by_id.return_value = fake_key
            resp = api_client.get("/protected?api_key=qp-key")
            assert resp.status_code == 200

    def test_header_takes_precedence(self, api_client):
        fake_key = MagicMock(spec=APIKey)
        fake_key.id = "header-key"
        with patch("services.api.auth.APIKey") as mock_cls:
            mock_cls.get_by_id.return_value = fake_key
            resp = api_client.get(
                "/protected?api_key=query-key",
                headers={"X-API-Key": "header-key"},
            )
            assert resp.status_code == 200
            mock_cls.get_by_id.assert_called_once_with("header-key")

    def test_health_no_auth_required(self, api_client):
        """Health endpoint doesn't need an API key."""
        resp = api_client.get("/health")
        assert resp.status_code == 200
