"""Image Processor — reactive asset pipeline for Hex.

Triggered by Eventarc GCS finalize events on the assets bucket.
Converts uploaded PDFs and images to standardized PNGs and thumbnails,
then updates the Firestore puzzle manifest.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile

from flask import Flask, request
from google.cloud import firestore, storage
from pdf2image import convert_from_path
from PIL import Image

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

THUMBNAIL_MAX_SIZE = (340, 440)
GENERATED_METADATA_KEY = "x-generated-by"
GENERATED_METADATA_VALUE = "image-processor"

# Matches: puzzles/{publication}/{puzzle_id}/{puzzle_id}_(puzzle|solution).{ext}
PATH_PATTERN = re.compile(
    r"^puzzles/(?P<publication>[^/]+)/(?P<puzzle_id>[^/]+)/"
    r"(?P=puzzle_id)_(?P<variant>puzzle|solution)\.(?P<ext>pdf|jpg|jpeg|gif)$"
)

# Extensions we process
PROCESSABLE_EXTENSIONS = {"pdf", "jpg", "jpeg", "gif"}


# ---------------------------------------------------------------------------
# Processing helpers
# ---------------------------------------------------------------------------


def convert_pdf_to_png(input_path: str, output_path: str) -> None:
    """Convert first page of a PDF to PNG."""
    images = convert_from_path(input_path, fmt="png", single_file=True)
    if images:
        images[0].save(output_path, "PNG")


def convert_image_to_png(input_path: str, output_path: str) -> None:
    """Convert a JPEG/GIF image to PNG."""
    with Image.open(input_path) as img:
        img.save(output_path, "PNG")


def create_thumbnail(input_path: str, output_path: str) -> None:
    """Create a thumbnail from a PNG image."""
    with Image.open(input_path) as img:
        img.thumbnail(THUMBNAIL_MAX_SIZE)
        img.save(output_path, "PNG")


def upload_blob(
    bucket: storage.Bucket,
    local_path: str,
    blob_name: str,
    content_type: str = "image/png",
) -> storage.Blob:
    """Upload a file to GCS with generated-by metadata."""
    blob = bucket.blob(blob_name)
    blob.metadata = {GENERATED_METADATA_KEY: GENERATED_METADATA_VALUE}
    blob.upload_from_filename(local_path, content_type=content_type)
    blob.reload()  # populate md5, etag, size
    logger.info("Uploaded: gs://%s/%s", bucket.name, blob_name)
    return blob


def update_firestore_manifest(
    puzzle_id: str,
    variant: str,
    png_blob: storage.Blob,
    thumb_blob: storage.Blob,
) -> None:
    """Update the puzzle's PuzzleFiles manifest in Firestore."""
    db = firestore.Client()
    doc_ref = db.collection("puzzles").document(puzzle_id)
    doc = doc_ref.get()

    if not doc.exists:
        logger.warning("Puzzle %s not found in Firestore — skipping manifest update", puzzle_id)
        return

    png_field = f"files.{variant}_png"
    thumb_field = f"files.{variant}_thumb"

    doc_ref.update(
        {
            png_field: {
                "path": png_blob.name,
                "gcs_md5": png_blob.md5_hash or "",
                "gcs_etag": png_blob.etag or "",
                "size": png_blob.size or 0,
                "content_type": "image/png",
            },
            thumb_field: {
                "path": thumb_blob.name,
                "gcs_md5": thumb_blob.md5_hash or "",
                "gcs_etag": thumb_blob.etag or "",
                "size": thumb_blob.size or 0,
                "content_type": "image/png",
            },
        }
    )
    logger.info("Updated Firestore manifest for %s.%s", puzzle_id, variant)


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------


def should_skip(event: dict) -> str | None:
    """Return a reason string if this event should be skipped, else None."""
    name = event.get("name", "")

    # Skip thumbnails
    if "_thumb." in name:
        return f"thumbnail file: {name}"

    # Skip generated files (metadata check)
    metadata = event.get("metadata", {})
    if metadata.get(GENERATED_METADATA_KEY) == GENERATED_METADATA_VALUE:
        return f"generated file: {name}"

    # Skip non-puzzle paths
    if not name.startswith("puzzles/"):
        return f"not a puzzle path: {name}"

    # Skip non-processable files
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in PROCESSABLE_EXTENSIONS:
        return f"non-processable extension: {ext}"

    # Must match naming convention
    if not PATH_PATTERN.match(name):
        return f"does not match naming convention: {name}"

    return None


@app.route("/", methods=["POST"])
def index():
    """Handle Eventarc GCS finalize event."""
    event = request.get_json(silent=True)
    if not event:
        logger.warning("Received empty event")
        return "no event", 400

    bucket_name = event.get("bucket", "")
    object_name = event.get("name", "")
    logger.info("Event received: gs://%s/%s", bucket_name, object_name)

    # Check skip conditions
    skip_reason = should_skip(event)
    if skip_reason:
        logger.info("Skipping: %s", skip_reason)
        return "skipped", 200

    # Parse the path
    match = PATH_PATTERN.match(object_name)
    if not match:
        return "no match", 200

    puzzle_id = match.group("puzzle_id")
    variant = match.group("variant")  # "puzzle" or "solution"
    ext = match.group("ext")
    base_dir = object_name.rsplit("/", 1)[0]

    # Set up GCS
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(bucket_name)

    # Check blob metadata (Eventarc event may not include it)
    source_blob = bucket.blob(object_name)
    source_blob.reload()
    if (source_blob.metadata or {}).get(GENERATED_METADATA_KEY) == GENERATED_METADATA_VALUE:
        logger.info("Skipping generated file (blob metadata): %s", object_name)
        return "skipped", 200

    # Process in a temp directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Download source file
        source_file = os.path.join(tmp_dir, f"source.{ext}")
        source_blob.download_to_filename(source_file)
        logger.info("Downloaded: %s (%d bytes)", object_name, source_blob.size or 0)

        # Convert to PNG
        png_file = os.path.join(tmp_dir, "output.png")
        if ext == "pdf":
            convert_pdf_to_png(source_file, png_file)
        else:
            convert_image_to_png(source_file, png_file)

        # Create thumbnail
        thumb_file = os.path.join(tmp_dir, "thumb.png")
        create_thumbnail(png_file, thumb_file)

        # Upload PNG and thumbnail
        png_name = f"{base_dir}/{puzzle_id}_{variant}.png"
        thumb_name = f"{base_dir}/{puzzle_id}_{variant}_thumb.png"

        png_blob = upload_blob(bucket, png_file, png_name)
        thumb_blob = upload_blob(bucket, thumb_file, thumb_name)

    # Update Firestore manifest
    try:
        update_firestore_manifest(puzzle_id, variant, png_blob, thumb_blob)
    except Exception:
        logger.exception("Failed to update Firestore manifest for %s", puzzle_id)
        # Don't fail the request — files are uploaded successfully

    return "ok", 200


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return "ok", 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))  # noqa: S104, S201
