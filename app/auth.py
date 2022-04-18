# -*- coding: utf-8 -*-
"""Hex Auth module."""
import logging
import os

import db
from flask import request
from google.auth.transport import requests
from google.oauth2 import id_token

CLIENT_ID = os.environ.get("CLIENT_ID")


class User:
    """User class."""

    def __init__(self, user_id=None):
        """Initialize a User instance."""
        self.id = user_id
        self.admin = False
        self.email = None
        self.first_name = None
        self.last_name = None
        self.name = None
        self.photo = None

    def get(self):
        """Get a user from firestore."""
        data = db.get_doc_dict("users", self.id)
        self.admin = data.get("admin", False)
        self.email = data.get("email")
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")
        self.name = data.get("name")
        self.photo = data.get("photo")
        return self

    def from_token_info(self, token_info):
        """Initialize a user from an ID token."""
        print(f"Token Info: {token_info}")
        self.id = token_info.get("sub")
        # get user from firestore
        self.get()
        # update user from id token
        self.email = token_info.get("email")
        self.first_name = token_info.get("given_name")
        self.last_name = token_info.get("family_name")
        self.name = token_info.get("name")
        self.photo = token_info.get("picture")
        return self

    def to_dict(self):
        """Return a user as a dict."""
        data = {
            "id": self.id,
            "admin": self.admin,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "name": self.name,
            "photo": self.photo,
        }
        return data

    def save(self):
        """Save a user to firestore."""
        data = self.to_dict()
        db.save_doc("users", self.id, data)


def validate_credential():
    """Validate the ID token."""
    credential = request.values.get("credential")
    try:
        token_info = id_token.verify_oauth2_token(credential, requests.Request(), CLIENT_ID)
        user_id = token_info["sub"]
        print(f"Successfully validated credential: {user_id}")
        return token_info
    except ValueError:
        logging.error("Failed to validate credentia.")
        return False


def validate_csrf_token():
    """Validate the CSRF token."""
    csrf_token = request.values.get("g_csrf_token")
    csrf_token_cookie = request.cookies.get('g_csrf_token')
    if not csrf_token:
        logging.error("No CSRF token in request.")
        return False
    elif not csrf_token_cookie:
        logging.error("No CSRF token in cookie.")
        return False
    elif csrf_token != csrf_token_cookie:
        logging.error("Failed to verify double submit cookie.")
        return False
    return True
