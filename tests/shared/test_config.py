"""Tests for services.shared.config — environment-aware configuration."""

from __future__ import annotations

from services.shared.config import HexConfig


class TestHexConfig:
    """Tests for HexConfig.from_env()."""

    def test_defaults(self, monkeypatch):
        """Default config uses test env values from conftest."""
        config = HexConfig.from_env()
        assert config.project_id == "test-project"
        assert config.env == "test"

    def test_prod_env(self, monkeypatch):
        monkeypatch.setenv("HEX_ENV", "prod")
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "lukwam-hex")
        config = HexConfig.from_env()
        assert config.env == "prod"
        assert config.is_prod is True
        assert config.db_name == "(default)"

    def test_dev_env(self, monkeypatch):
        monkeypatch.setenv("HEX_ENV", "dev")
        monkeypatch.delenv("HEX_DB_NAME", raising=False)
        config = HexConfig.from_env()
        assert config.is_prod is False
        assert config.db_name == "v2"

    def test_custom_db_name(self, monkeypatch):
        monkeypatch.setenv("HEX_DB_NAME", "custom-db")
        config = HexConfig.from_env()
        assert config.db_name == "custom-db"

    def test_frozen(self):
        """Config should be immutable."""
        config = HexConfig(project_id="test", db_name="db", env="dev")
        with __import__("pytest").raises(AttributeError):
            config.env = "prod"  # type: ignore[misc]
