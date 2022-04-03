# -*- coding: utf-8 -*-
import datetime
import json
import logging
import os

import requests
from flask import Flask
from flask import redirect
from flask import render_template
from flask import request
from flask import send_file
from google.cloud import firestore
from google.cloud import secretmanager_v1
from google.cloud import storage
# import imgkit

app = Flask(__name__)

GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")


def render_theme(body, **kwargs):
    """Return the rendered theme."""
    return render_template(
        "theme.html",
        body=body,
        **kwargs,
    )


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


def get_pagination(current):
    """Return the next page and previous page for pagination."""
    client = firestore.Client()
    desc = firestore.Query.DESCENDING
    ref = client.collection("puzzles")

    next_puzzle = ref.order_by("date").start_after(current).limit(1)
    next_id = None
    for doc in next_puzzle.get():
        next_id = doc.id

    previous_puzzle = ref.order_by(
        "date", direction=desc,
    ).start_after(current).limit(1)
    previous_id = None
    for doc in previous_puzzle.get():
        previous_id = doc.id

    pagination = {
        "next": next_id,
        "previous": previous_id,
    }
    return pagination


def get_secret(name):
    client = secretmanager_v1.SecretManagerServiceClient()
    name = f"projects/{GOOGLE_CLOUD_PROJECT}/secrets/{name}/versions/latest"
    request = secretmanager_v1.AccessSecretVersionRequest(name=name)
    response = client.access_secret_version(request=request)
    return response.payload.data.decode("utf-8")


@app.route("/")
def hello():
    """Return a friendly HTTP greeting."""
    body = render_template(
        "index.html",
    )
    return render_theme(body)


@app.route("/admin/publications")
def admin_publications():
    """Display the admin page for publications."""
    body = render_template(
        "admin_publications.html",
    )
    return render_theme(body)


@app.route("/cryptics")
def cryptics():
    """Display the cryptics page."""
    client = firestore.Client()
    cryptics = []
    for doc in client.collection("puzzles").stream():
        cryptic = doc.to_dict()
        cryptic["id"] = doc.id
        cryptics.append(cryptic)

    body = render_template(
        "cryptics.html",
        cryptics=cryptics,
    )
    return render_theme(body)


@app.route("/puzzle/<id>")
def puzzle(id):
    """Display the cryptics page."""
    client = firestore.Client()
    # get puzzle
    doc = client.collection("puzzles").document(id).get()
    puzzle = doc.to_dict()
    if puzzle:
        puzzle["id"] = doc.id

    storage_client = storage.Client()
    image_bucket_name = "lukwam-hex-images"

    # get puzzle url
    puzzle_url = puzzle["puzzle_link"]
    # if puzzle_url:
    #     cache_image(id, "puzzle", puzzle_url)
    if puzzle_url and puzzle_url.lower().endswith(".pdf"):
        puzzle_file_name = f"{doc.id}_puzzle.png"
        bucket = storage_client.get_bucket(image_bucket_name)
        blob = storage.Blob(puzzle_file_name, bucket)
        if blob.exists():
            print("Puzzle image exists! Let's display it.")
            puzzle_url = generate_download_signed_url_v4(
                image_bucket_name,
                puzzle_file_name,
            )

    # get answer url
    answer_url = puzzle["answer_link"]
    # get answer image
    # if answer_url:
    #     cache_image(id, "answer", answer_url)
    if answer_url and answer_url.lower().endswith(".pdf"):
        answer_file_name = f"{doc.id}_answer.png"
        bucket = storage_client.get_bucket(image_bucket_name)
        blob = storage.Blob(answer_file_name, bucket)
        if blob.exists():
            print("Answer image exists! Let's display it.")
            answer_url = generate_download_signed_url_v4(
                image_bucket_name,
                answer_file_name,
            )

    # get pagination information
    pagination = get_pagination(doc)

    body = render_template(
        "puzzle.html",
        puzzle=puzzle,
        puzzle_url=puzzle_url,
        answer_url=answer_url,
        pagination=pagination,
    )
    return render_theme(body)


@app.route("/admin/puzzle/<id>/delete", methods=["GET"])
def delete_puzzle(id):
    client = firestore.Client()
    doc_ref = client.collection("puzzles").document(id)
    doc_ref.delete()
    return redirect("/cryptics")


@app.route("/admin/puzzle/<id>/edit", methods=["GET", "POST"])
def edit_puzzle(id):
    """Display the edit puzzle page."""
    client = firestore.Client()

    if request.method == "POST":
        answer_link = request.form.get("answer_link")
        books = []
        for book in request.form.get("books").split(","):
            if book.strip():
                books.append(book.strip())
        date = request.form.get("date")
        issue = request.form.get("issue")
        num = request.form.get("num")
        pub = request.form.get("publication")
        puzzle_link = request.form.get("puzzle_link")
        title = request.form.get("title")
        web_link = request.form.get("web_link")

        # get puzzle image
        if puzzle_link:
            cache_image(id, "puzzle", puzzle_link)

        # get answer image
        if answer_link:
            cache_image(id, "answer", answer_link)

        puzzle = {
            "answer_link": answer_link,
            "books": books,
            "date": date,
            "issue": issue,
            "num": num,
            "pub": pub,
            "puzzle_link": puzzle_link,
            "title": title,
            "web_link": web_link,
        }
        client.collection("puzzles").document(id).set(puzzle)
        return redirect(f"/puzzle/{id}")
    else:
        # get puzzle
        doc = client.collection("puzzles").document(id).get()
        puzzle = doc.to_dict()
        puzzle["id"] = doc.id

        # get publications
        publications = [
            pub.to_dict() for pub in sorted(
                client.collection("publications").stream(),
                key=lambda x: x.get("name"),
            )
        ]
        body = render_template(
            "puzzle_edit.html",
            publications=publications,
            puzzle=puzzle,
        )
        return render_theme(body)


if __name__ == "__main__":
    @app.route("/favicon.ico")
    def favicon():
        """Return favicon.ico."""
        return send_file("favicon.ico", mimetype="image/x-icon")

    @app.route("/images/<name>")
    def images(name):
        """Return static images as PNG."""
        return send_file(f"images/{name}", mimetype="image/png")

    @app.route("/styles.css")
    def styles():
        """Return data in Firestore."""
        return send_file("styles.css", mimetype="text/css")

    app.run(host="0.0.0.0", port=8080, debug=True)
