# -*- coding: utf-8 -*-
"""PDF to PNG."""
import logging
import os

from flask import Flask
from flask import request
from google.cloud import storage
from pdf2image import convert_from_path
from PIL import Image

app = Flask(__name__)

EXTENSIONS = ["gif", "jpeg", "jpg", "pdf", "png"]
IMAGES_BUCKET = "lukwam-hex-images"
MAX_SIZE = (340, 440)


def convert_image_to_png(input_file_path, extension):
    """Convert an image file to a PNG."""
    file_path = input_file_path.replace(f".{extension}", ".png")
    file_name = file_path.split("/")[-1]
    uri = f"gs://{IMAGES_BUCKET}/{file_name}"

    # convert pdf
    image = Image.open(input_file_path)
    image.save(file_path)

    # create blob
    client = storage.Client()
    bucket = client.get_bucket(IMAGES_BUCKET)
    blob = storage.Blob(file_name, bucket)
    print(f"Uploading file to {uri}...")
    blob.upload_from_filename(file_path)

    if os.path.exists(file_name):
        os.remove(file_name)

    return blob


def convert_pdf_to_png(input_file_path, archive):
    """Convert a PDF file to a PNG."""
    bucket_name = IMAGES_BUCKET
    file_path = input_file_path.replace(".pdf", ".png")
    file_name = file_path.split("/")[-1]

    if archive:
        bucket_name = "lukwam-hex-archive-images"
        file_name = f"{archive}/{file_name}"

    uri = f"gs://{bucket_name}/{file_name}"

    # convert pdf
    images = convert_from_path(input_file_path, fmt="png", single_file=True)
    for image in images:
        image.save(file_path)
        break

    # create blob
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = storage.Blob(file_name, bucket)
    print(f"Uploading file to {uri}...")
    blob.upload_from_filename(file_path)

    # create thumbnails for archive files
    if archive:
        # set bucket and filename for thumbnail
        thumb_bucket_name = "lukwam-hex-thumbnails"
        thumb_path = file_path.replace(".png", "_thumb.png")
        thumb_uri = f"gs://{thumb_bucket_name}/{file_name}"

        # create thumbnail image
        thumb = Image.open(file_path)
        thumb.thumbnail(MAX_SIZE)
        thumb.save(thumb_path)

        # upload thumbnail
        thumb_bucket = client.get_bucket(thumb_bucket_name)
        thumb_blob = storage.Blob(file_name, thumb_bucket)
        print(f"Uploading thumbnail file to {thumb_uri}...")
        thumb_blob.upload_from_filename(thumb_path)

        if os.path.exists(thumb_path):
            os.remove(thumb_path)

    if os.path.exists(file_path):
        os.remove(file_path)

    return blob


def copy_image(input_file_path):
    """Copy a PNG file."""
    # create blob
    file_name = input_file_path.split("/")[-1]
    uri = f"gs://{IMAGES_BUCKET}/{file_name}"

    client = storage.Client()
    bucket = client.get_bucket(IMAGES_BUCKET)
    blob = storage.Blob(file_name, bucket)
    print(f"Uploading file to {uri}...")
    blob.upload_from_filename(input_file_path)

    return blob


@app.route("/", methods=["POST"])
def index():
    event = request.get_json()

    # get the object info from the event message
    bucket_name = event["bucket"]
    file_name = event["name"]
    uri = f"gs://{bucket_name}/{file_name}"
    print(f"New image uploaded: {uri}")

    # check if this is for the archive
    archive = False
    if bucket_name == "lukwam-hex-archive":
        archive = file_name.split("/")[0]

    extension = file_name.lower().split(".")[-1]

    # fail if unsupported extension
    if extension not in EXTENSIONS:
        if extension in ["svg"]:
            print(f"Skipping SVG file: {file_name}")
            return "ok"
        error = f"Unknown extension: {extension}"
        logging.error(error)
        return (error, 500)

    # define temp file, delete if exists
    file_path = f"/tmp/{file_name.split('/')[-1]}"
    if os.path.exists(file_path):
        os.remove(file_path)

    # get the input file from gcs
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = storage.Blob(file_name, bucket)
    print(f"Downloading file {uri} to {file_path}...")
    blob.download_to_filename(file_path)

    # check file extension
    if extension == "png":
        print(f"Copying PNG file to image bucket: {file_name}")
        if not archive:
            copy_image(file_path)

    elif extension == "pdf":
        print(f"Converting PDF file to PNG: {file_name}")
        convert_pdf_to_png(file_path, archive)

    elif extension in ["gif", "jpeg", "jpg"]:
        print(f"Converting image file to PNG: {file_name}")
        if not archive:
            convert_image_to_png(file_path, extension)

    else:
        error = f"Unknown file type: {extension}"
        logging.error(error)
        return (error, 500)

    if os.path.exists(file_path):
        os.remove(file_path)

    return "ok"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
