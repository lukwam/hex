"""Hex Admin — Google OAuth2 authentication.

Adapted from the Darwin's Ark FlaskAuth pattern. Provides:
- GoogleAuth: wraps google-auth-oauthlib Flow
- FlaskAuth: session management, user lookup, request gating
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests
from flask import abort, g, request, session
from google_auth_oauthlib.flow import Flow

from ..shared.models import User

logger = logging.getLogger(__name__)

OAUTH2_CLIENT_CONFIG = os.environ.get("OAUTH2_CLIENT_CONFIG", "")


# ---------------------------------------------------------------------------
# Google OAuth2 low-level helpers
# ---------------------------------------------------------------------------


class GoogleAuth:
    """Thin wrapper around google-auth-oauthlib for the OAuth2 dance."""

    SCOPES = [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
    ]

    @staticmethod
    def decode_access_token(token: str) -> dict[str, Any]:
        """Exchange an access token for user info via Google's tokeninfo."""
        resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/tokeninfo",
            params={"access_token": token},
            timeout=5,
        )
        return resp.json()

    @classmethod
    def create_flow(cls, redirect_uri: str, state: str | None = None) -> Flow:
        """Create an OAuth2 Flow from the client config."""
        if not OAUTH2_CLIENT_CONFIG:
            raise ValueError(
                "OAUTH2_CLIENT_CONFIG is not set. Set it to the JSON contents of your Google OAuth2 client secret."
            )
        client_config = json.loads(OAUTH2_CLIENT_CONFIG)
        flow = Flow.from_client_config(
            client_config,
            scopes=cls.SCOPES,
            state=state,
        )
        flow.redirect_uri = redirect_uri
        return flow

    @classmethod
    def create_authorization_url(cls, redirect_uri: str) -> tuple[str, str, str]:
        """Return (authorization_url, state, code_verifier)."""
        flow = cls.create_flow(redirect_uri=redirect_uri)
        authorization_url, state = flow.authorization_url(
            access_type="online",
            include_granted_scopes="false",
        )
        # The Flow auto-generates a PKCE code_verifier; we must persist it
        # so handle_callback can pass it back during token exchange.
        return authorization_url, state, flow.code_verifier

    @classmethod
    def handle_callback(
        cls,
        redirect_uri: str,
        state: str,
        request_url: str,
        code_verifier: str | None = None,
    ) -> str:
        """Exchange the authorization code for an access token. Returns the token."""
        flow = cls.create_flow(redirect_uri=redirect_uri, state=state)
        if code_verifier:
            flow.code_verifier = code_verifier
        flow.fetch_token(authorization_response=request_url)
        token = flow.credentials.token
        if not token:
            abort(403)
        return token


# ---------------------------------------------------------------------------
# Flask-level auth: session + user management
# ---------------------------------------------------------------------------


class FlaskAuth:
    """Session-based Google OAuth2 authentication for Flask."""

    # ------ URL helpers ------

    @staticmethod
    def _repair_url(url: str) -> str:
        """Ensure https in non-local URLs (behind GCP load balancers)."""
        for prefix in ("http://localhost:", "http://127.0.0.1:", "http://0.0.0.0:"):
            if url.startswith(prefix):
                return url
        return url.replace("http://", "https://", 1)

    @classmethod
    def _callback_uri(cls) -> str:
        base = cls._repair_url(request.url_root.rstrip("/"))
        return f"{base}/callback"

    # ------ Public API ------

    @classmethod
    def get_authorization_url(cls) -> str:
        """Build the Google Sign-In URL and stash state in the session."""
        redirect_uri = cls._callback_uri()
        authorization_url, state, code_verifier = GoogleAuth.create_authorization_url(redirect_uri)
        session["state"] = state
        session["code_verifier"] = code_verifier
        return authorization_url

    @classmethod
    def handle_callback(cls) -> None:
        """Process the OAuth2 callback: exchange code → save token + email."""
        state = session.get("state", "")
        code_verifier = session.get("code_verifier")
        redirect_uri = cls._callback_uri()
        request_url = cls._repair_url(request.url)
        token = GoogleAuth.handle_callback(redirect_uri, state, request_url, code_verifier)

        # Decode and save to session
        token_info = GoogleAuth.decode_access_token(token)
        session["email"] = token_info.get("email")
        session["sub"] = token_info.get("sub")
        session["token"] = token

    @classmethod
    def validate_user(cls) -> User | None:
        """Check the session for a valid, known user.

        On success, sets g.user / g.email and returns the User.
        Returns None if the session is missing or invalid.
        """
        email = session.get("email")
        token = session.get("token")
        if not email or not token:
            return None

        # Verify the token is still valid
        token_info = GoogleAuth.decode_access_token(token)
        if token_info.get("email") != email:
            logger.warning("Token email mismatch: session=%s token=%s", email, token_info.get("email"))
            return None

        # Look up user in Firestore
        results = User.find({"email": email})
        if not results:
            logger.warning("Unknown user attempted access: %s", email)
            return None

        user = results[0]
        g.user = user
        g.email = user.email
        return user

    @classmethod
    def logout(cls) -> None:
        """Clear the session."""
        session.clear()
