"""Tests for services.admin.auth — OAuth2 and URL helpers."""

from __future__ import annotations

import pytest

from services.admin.auth import FlaskAuth, GoogleAuth


class TestGoogleAuthCreateFlow:
    """Tests for GoogleAuth.create_flow() — lazy config loading."""

    def test_raises_without_config(self, monkeypatch):
        monkeypatch.delenv("OAUTH2_CLIENT_CONFIG", raising=False)
        with pytest.raises(ValueError, match="OAUTH2_CLIENT_CONFIG is not set"):
            GoogleAuth.create_flow(redirect_uri="http://localhost:8080/callback")

    def test_raises_with_empty_config(self, monkeypatch):
        monkeypatch.setenv("OAUTH2_CLIENT_CONFIG", "")
        with pytest.raises(ValueError, match="OAUTH2_CLIENT_CONFIG is not set"):
            GoogleAuth.create_flow(redirect_uri="http://localhost:8080/callback")


class TestRepairUrl:
    """Tests for FlaskAuth._repair_url() — HTTPS enforcement."""

    def test_localhost_unchanged(self):
        url = "http://localhost:8080/callback"
        assert FlaskAuth._repair_url(url) == url

    def test_127_unchanged(self):
        url = "http://127.0.0.1:5000/callback"
        assert FlaskAuth._repair_url(url) == url

    def test_0000_unchanged(self):
        url = "http://0.0.0.0:8080/callback"
        assert FlaskAuth._repair_url(url) == url

    def test_production_url_upgraded(self):
        url = "http://hex-admin.run.app/callback"
        assert FlaskAuth._repair_url(url) == "https://hex-admin.run.app/callback"

    def test_already_https_unchanged(self):
        url = "https://hex-admin.run.app/callback"
        assert FlaskAuth._repair_url(url) == url
