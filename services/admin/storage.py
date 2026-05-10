"""Hex Admin — GCS storage helpers."""

from __future__ import annotations

import logging
import os
from datetime import timedelta

import google.auth
from google.auth import impersonated_credentials
from google.auth.transport import requests as auth_requests
from google.cloud import storage

logger = logging.getLogger(__name__)

# Cache at module level.
_storage_client: storage.Client | None = None
_signing_credentials: google.auth.credentials.Credentials | None = None


def _get_client() -> storage.Client:
    """Return a cached storage client."""
    global _storage_client  # noqa: PLW0603
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def _get_signing_credentials() -> google.auth.credentials.Credentials:
    """Return cached credentials capable of IAM-based signing.

    In production (Cloud Run), the service account credentials support
    signing directly.  In local dev, we impersonate the SA specified by
    HEX_IMPERSONATE_SA (set by develop.sh) using the user's own ADC.
    """
    global _signing_credentials  # noqa: PLW0603
    if _signing_credentials is not None:
        return _signing_credentials

    source_credentials, _ = google.auth.default()

    # If running as a service account already (Cloud Run), use it directly.
    if hasattr(source_credentials, "service_account_email") and hasattr(source_credentials, "sign_bytes"):
        if hasattr(source_credentials, "refresh"):
            source_credentials.refresh(auth_requests.Request())
        _signing_credentials = source_credentials
        return _signing_credentials

    # Local dev: impersonate the SA from HEX_IMPERSONATE_SA.
    sa_email = os.environ.get("HEX_IMPERSONATE_SA")
    if not sa_email:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "lukwam-hex-dev")
        sa_email = f"admin-service@{project}.iam.gserviceaccount.com"

    logger.info("Impersonating %s for GCS signing", sa_email)
    target = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=sa_email,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    target.refresh(auth_requests.Request())
    _signing_credentials = target
    return _signing_credentials


def _images_bucket_name() -> str:
    """Return the images bucket name for the current environment.

    Prod:  lukwam-hex-images
    Other: lukwam-hex-images-{env}
    """
    env = os.environ.get("HEX_ENV", "dev")
    if env == "prod":
        return "lukwam-hex-images"
    return f"lukwam-hex-images-{env}"


def get_cover_url(book_id: str) -> str | None:
    """Return a signed URL for a book cover image, or None if not found."""
    bucket_name = _images_bucket_name()
    blob_name = f"{book_id}_cover.png"
    try:
        client = _get_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
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
        logger.warning("Failed to generate cover URL for %s", book_id, exc_info=True)
        return None
