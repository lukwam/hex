"""CoxRathvon App — GCS signed URL helpers.

Generates signed URLs for puzzle assets in the consolidated assets bucket.
This module is temporary — when the app moves to the coxrathvon project,
image serving should be handled via API endpoints instead.
"""

from __future__ import annotations

import logging
import os
from datetime import timedelta

import google.auth
from google.auth import impersonated_credentials
from google.auth.transport import requests as auth_requests
from google.cloud import storage

logger = logging.getLogger(__name__)

_storage_client: storage.Client | None = None
_signing_credentials: google.auth.credentials.Credentials | None = None


def _get_client() -> storage.Client:
    """Return a cached storage client."""
    global _storage_client  # noqa: PLW0603
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def _get_signing_credentials() -> google.auth.credentials.Credentials:
    """Return cached credentials capable of IAM-based signing."""
    global _signing_credentials  # noqa: PLW0603
    if _signing_credentials is not None:
        return _signing_credentials

    source_credentials, _ = google.auth.default()

    # Cloud Run: service account credentials support signing directly.
    if hasattr(source_credentials, "service_account_email") and hasattr(source_credentials, "sign_bytes"):
        if hasattr(source_credentials, "refresh"):
            source_credentials.refresh(auth_requests.Request())
        _signing_credentials = source_credentials
        return _signing_credentials

    # Local dev: impersonate the SA.
    sa_email = os.environ.get("HEX_IMPERSONATE_SA")
    if not sa_email:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "lukwam-hex-dev")
        sa_email = f"app-service@{project}.iam.gserviceaccount.com"

    logger.info("Impersonating %s for GCS signing", sa_email)
    target = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=sa_email,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    target.refresh(auth_requests.Request())
    _signing_credentials = target
    return _signing_credentials


def _assets_bucket_name() -> str:
    """Return the consolidated assets bucket name."""
    env = os.environ.get("HEX_ENV", "dev")
    if env == "prod":
        return "lukwam-hex-assets"
    return f"lukwam-hex-assets-{env}"


def get_signed_url(blob_path: str) -> str | None:
    """Return a signed URL for a blob in the assets bucket, or None."""
    if not blob_path:
        return None
    bucket_name = _assets_bucket_name()
    try:
        client = _get_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        if not blob.exists():
            return None

        creds = _get_signing_credentials()
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET",
            service_account_email=creds.service_account_email,
            access_token=creds.token,
        )
        return url
    except Exception:
        logger.warning("Failed to generate signed URL for %s", blob_path, exc_info=True)
        return None


def get_puzzle_image_urls(puzzle_id: str, publication: str) -> dict[str, str | None]:
    """Generate signed URLs for a puzzle's images.

    Uses the new consolidated assets bucket path layout:
      puzzles/{publication}/{puzzle_id}/{puzzle_id}_{type}.{ext}
    """
    prefix = f"puzzles/{publication}/{puzzle_id}/{puzzle_id}"
    return {
        "puzzle_png": get_signed_url(f"{prefix}_puzzle.png"),
        "puzzle_pdf": get_signed_url(f"{prefix}_puzzle.pdf"),
        "solution_png": get_signed_url(f"{prefix}_solution.png"),
        "solution_pdf": get_signed_url(f"{prefix}_solution.pdf"),
        "puzzle_thumb": get_signed_url(f"{prefix}_puzzle_thumb.png"),
        "solution_thumb": get_signed_url(f"{prefix}_solution_thumb.png"),
    }
