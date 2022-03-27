# -*- coding: utf-8 -*-
import logging

import requests
from flask import Flask
from flask import redirect
from flask import render_template
from flask import request
from flask import send_file
from google.cloud import firestore
from google.cloud import storage

app = Flask(__name__)


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
    if url.endswith(".pdf"):
        content_type = "application/pdf"
        extension = "pdf"
    else:
        extension = url.split(".")[-1]
        logging.error(f"Unknown extension: {extension}")
        return

    # download raw image to file handle
    print(f"Getting {extension} from {url}...")
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        response.raw.decode_content = True
        filename = f"{puzzle_id}_{type}.{extension}"
        print(f"Image sucessfully downloaded: {filename}")
    else:
        print(f"Failed to download image: {filename}")
        return

    # save file to cloud storage
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(filename)
    if blob.exists():
        blob.delete()
    blob.upload_from_file(response.raw, content_type=content_type)


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
    puzzle["id"] = doc.id
    body = render_template(
        "puzzle.html",
        puzzle=puzzle,
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
        date = request.form.get("date")
        issue = request.form.get("issue")
        num = request.form.get("num")
        publication = request.form.get("publication")
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
            "title": title,
            "pub": publication,
            "issue": issue,
            "date": date,
            "num": num,
            "web_link": web_link,
            "puzzle_link": puzzle_link,
            "answer_link": answer_link,
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
