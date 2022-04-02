# -*- coding: utf-8 -*-
"""PDF to PNG."""
import os

from flask import Flask
from flask import request
from google.cloud import storage

app = Flask(__name__)


@app.route("/", methods=["POST"])
def index():
    event = request.get_json()

    bucket_name = event["bucket"]
    file_name = event["name"]

    # content_type = event["contentType"]
    path = f"gs://{bucket_name}/{file_name}"
    # print(f"Path: {path} [{content_type}]")

    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = storage.Blob(file_name, bucket)

    tmp_file = f"/tmp/{file_name}"

    # download file
    print(f"Downloading file {path}...")
    blob.download_to_filename(tmp_file)

    # remove downloaded file
    os.remove(tmp_file)
    print(f"Removed file {tmp_file}.")

    return "ok"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
