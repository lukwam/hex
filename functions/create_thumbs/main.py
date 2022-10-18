# -*- coding: utf-8 -*-
"""Cloud Function to create thumbnails from archive images."""
import os

from google.cloud import storage
from PIL import Image

MAX_SIZE = (340, 440)


def list_files(bucket_name):
    """Return a list of files in storage."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    files = {}
    for blob in bucket.list_blobs():
        files[blob.name] = blob
    return files


def create_thumbs(request):
    """Move create thumbnails for archive images."""
    client = storage.Client()

    archive_bucket = "lukwam-hex-archive-images"
    thumbnails_bucket = "lukwam-hex-thumbnails"

    # get a list of images from the archive bucket
    archive_images = list_files(archive_bucket)
    print(f"Archive Images: {len(archive_images)}")

    # get a list of images from the thumbnails bucket
    thumbnail_images = list_files(thumbnails_bucket)
    print(f"Archive Images: {len(thumbnail_images)}")

    thumb_file = "thumbnail.png"
    tmp_file = "image.png"

    for name in archive_images:
        if name in thumbnail_images:
            continue
        print(f" + {name}")
        blob = archive_images[name]

        # download file
        blob.download_to_filename(tmp_file)

        # create thumbnail
        image = Image.open(tmp_file)
        image.thumbnail(MAX_SIZE)
        image.save(thumb_file)

        # upload thumbnail
        thumbnail = client.bucket(thumbnails_bucket).blob(name)
        thumbnail.upload_from_filename(thumb_file)

        # remove files
        os.remove(tmp_file)
        os.remove(thumb_file)

    return "ok"


if __name__ == "__main__":
    create_thumbs(None)
