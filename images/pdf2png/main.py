# -*- coding: utf-8 -*-
"""PDF to PNG."""
import os

from flask import Flask
from flask import request
from google.cloud import storage
from pdf2image import convert_from_path

app = Flask(__name__)


@app.route("/", methods=["POST"])
def index():
    event = request.get_json()

    bucket_name = event["bucket"]
    file_name = event["name"]
    path = f"gs://{bucket_name}/{file_name}"

    # content_type = event["contentType"]
    # print(f"Path: {path} [{content_type}]")

    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = storage.Blob(file_name, bucket)

    tmp_file = f"/tmp/{file_name}"

    # download file
    print(f"Downloading file {path}...")
    blob.download_to_filename(tmp_file)

    # convert image(s)
    print(f"Converting {tmp_file} to image...")
    images = convert_from_path(
        tmp_file,
        fmt="png",
        single_file=True,
    )

    image_bucket = client.get_bucket("lukwam-hex-images")
    new_name = file_name.replace("pdf", "png")
    new_blob = storage.Blob(new_name, image_bucket)

    print("Saving converted images...")
    for image in images:
        image.save(new_name)

    # upload image
    new_path = f"gs://lukwam-hex-images/{new_name}"
    print(f"Uploading file to {new_path}...")
    new_blob.upload_from_filename(new_name)

    # remove downloaded file
    os.remove(tmp_file)
    print(f"Removed file {tmp_file}.")

    return "ok"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
