# -*- coding: utf-8 -*-
"""Hex Auth module."""
import requests
from oauthlib.oauth2 import WebApplicationClient


def get_google_provider_config():
    """Return the details of the Google Oauth2 Provider configuration."""
    url = "https://accounts.google.com/.well-known/openid-configuration"
    return requests.get(url).json()


def get_login_url(client_id, base_url):
    """Return the loging URL."""
    client = WebApplicationClient(client_id)
    provider = get_google_provider_config()
    return client.prepare_request_uri(
        provider["authorization_endpoint"],
        redirect_uri=f"{base_url}callback",
        scope=[
            "email",
            "openid",
            "profile",
        ],
    )


def get_token(
        client_id,
        client_secret,
        base_url,
        code,
        request_url,
        redirect_url,
):
    """Return the details of a token request."""
    client = WebApplicationClient(client_id)
    provider = get_google_provider_config()
    token_url, headers, body = client.prepare_token_request(
        provider["token_endpoint"],
        authorization_response=request_url,
        redirect_url=redirect_url,
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(client_id, client_secret),
    )
    return client.parse_request_body_response(token_response.text)


def get_tokeninfo(**kwargs):
    """Return the details of an access_token or id_token."""
    url = "https://www.googleapis.com/oauth2/v3/tokeninfo"
    return requests.get(url, params=kwargs).json()
