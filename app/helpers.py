# -*- coding: utf-8 -*-
"""Helpers module for Hex."""
import datetime
import json
import logging
import os

import requests
from flask import render_template
from flask import request
from google.cloud import secretmanager_v1
from google.cloud import storage

GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
DEBUG_USER = (
    "admin@lukwam.dev",
    "106026141512242120941",
)


class User:
    """User class."""

    def __init__(self, email, id):
        """Initialize a User instance."""
        self.email = email
        self.id = id


def cache_image(puzzle_id, type, url):
    """Download and cache an image."""
    # set buckets
    answer_bucket = "lukwam-hex-answers"
    puzzle_bucket = "lukwam-hex-puzzles"
    # thumbnail_bucket = "lukwam-hex-thumbnails"

    # define bucket based on type of file
    if type == "answer":
        bucket_name = answer_bucket
    elif type == "puzzle":
        bucket_name = puzzle_bucket
    else:
        return

    # check file extension
    if url.lower().endswith(".pdf"):
        content_type = "application/pdf"
        extension = "pdf"
    elif url.lower().endswith(".gif"):
        content_type = "image/gif"
        extension = "gif"
    elif url.lower().endswith(".jpeg") or url.lower().endswith(".jpg"):
        content_type = "image/jpeg"
        extension = "jpg"
    else:
        extension = url.split(".")[-1]
        logging.error(f"Unknown extension: {extension}")
        return

    filename = f"{puzzle_id}_{type}.{extension}"

    # download raw image to file handle
    print(f"\nGetting {extension} from url: {url}")
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/88.0.4324.182 Safari/537.36"
    )
    headers = {
        "user-agent": user_agent,
    }
    response = requests.get(url, headers=headers, stream=True)
    if response.status_code == 200:
        response.raw.decode_content = True
        print(f"Image sucessfully downloaded: {filename}")
    else:
        print(
            f"ERROR: Failed to download image: {filename} "
            f"[{response.status_code}]",
        )
        return

    # save file to cloud storage
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(filename)
    if blob.exists():
        blob.delete()
    blob.upload_from_file(response.raw, content_type=content_type)


def generate_download_signed_url_v4(bucket_name, blob_name):
    """Generates a v4 signed URL for downloading a blob."""
    service_account_json = json.loads(get_secret("image-reader-key"))

    storage_client = storage.Client.from_service_account_info(
        service_account_json,
    )
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    url = blob.generate_signed_url(
        version="v4",
        # This URL is valid for 15 minutes
        expiration=datetime.timedelta(minutes=15),
        # Allow GET requests using this URL.
        method="GET",
    )

    return url


def get_current_user(debug=False):
    """Return the current user."""
    if debug:
        return User(*DEBUG_USER)
    user_email = request.headers.get("x-goog-authenticated-user-email", "")
    user_id = request.headers.get("x-goog-authenticated-user-id", "")
    if user_email and user_id:
        return User(
            user_email.replace("accounts.google.com:", ""),
            user_id.replace("accounts.google.com:", ""),
        )
    return None


def get_image_url(file_name):
    """Return the URL for an image."""
    client = storage.Client()
    image_bucket_name = "lukwam-hex-images"
    bucket = client.get_bucket(image_bucket_name)
    blob = storage.Blob(file_name, bucket)
    if blob.exists():
        return generate_download_signed_url_v4(
            image_bucket_name,
            file_name,
        )
    return None


def get_secret(name):
    """Return a secret."""
    client = secretmanager_v1.SecretManagerServiceClient()
    name = f"projects/{GOOGLE_CLOUD_PROJECT}/secrets/{name}/versions/latest"
    request = secretmanager_v1.AccessSecretVersionRequest(name=name)
    response = client.access_secret_version(request=request)
    return response.payload.data.decode("utf-8")


def render_theme(body, **kwargs):
    """Return the rendered theme."""
    return render_template(
        "theme.html",
        body=body,
        **kwargs,
    )


def save_image(file_name, file_object):
    """Save an image to GCS."""
    bucket_name = "lukwam-hex-images"
    uri = f"gs://{bucket_name}/{file_name}"
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    if blob.exists():
        print(f"Deleted {uri}...")
        blob.delete()
    blob.upload_from_file(file_object, content_type="image/png")
    print(f"Uploaded {uri}...")
