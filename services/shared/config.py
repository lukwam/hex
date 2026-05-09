"""Hex environment-aware configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class HexConfig:
    """Application configuration loaded from environment."""

    project_id: str
    db_name: str
    env: str

    @classmethod
    def from_env(cls) -> HexConfig:
        """Create config from environment variables."""
        env = os.environ.get("HEX_ENV", "dev")
        return cls(
            project_id=os.environ.get("GOOGLE_CLOUD_PROJECT", "lukwam-hex"),
            db_name=os.environ.get("HEX_DB_NAME", "(default)" if env == "prod" else "v2"),
            env=env,
        )

    @property
    def is_prod(self) -> bool:
        """Check if running in production."""
        return self.env == "prod"
