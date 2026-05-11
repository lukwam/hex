"""Sync puzzle PDFs and SVGs from Google Drive to GCS.

Lists files from the Hex shared drive, matches them to Firestore puzzles
by date+title, and uploads to the consolidated assets bucket using the
new directory layout.

Idempotent: skips files where the destination blob already exists with
a matching MD5 checksum.

Auth: uses impersonated service account credentials via HEX_IMPERSONATE_SA
(set by develop.sh). The SA must be a member of the shared Drive.
Falls back to Application Default Credentials if not set.

Usage:
    python scripts/sync_files.py                    # Dry run (default)
    python scripts/sync_files.py --apply            # Actually upload
    python scripts/sync_files.py --apply --pub wsj  # Only sync WSJ puzzles
"""

from __future__ import annotations

import argparse
import base64
import binascii
import io
import logging
import os
from typing import Any

import google.auth
from google.auth import impersonated_credentials
from google.cloud import storage
from google.cloud.firestore_v1 import Client as FirestoreClient
from googleapiclient.discovery import build

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)

# The Hex shared drive ID
DRIVE_ID = "0ALCeSdEPSCR-Uk9PVA"

# Source: Firestore
PROD_PROJECT = "lukwam-hex"

# Target bucket (env-aware)
DEV_PROJECT = "lukwam-hex-dev"
ASSETS_BUCKET = "lukwam-hex-assets-dev"

# Drive API scopes needed for the impersonated SA
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_credentials():
    """Get credentials for the Drive API.

    If HEX_IMPERSONATE_SA is set, impersonate that service account
    (which should be a member of the shared drive). Otherwise fall
    back to Application Default Credentials.
    """
    sa_email = os.environ.get("HEX_IMPERSONATE_SA")
    if sa_email:
        source_creds, _ = google.auth.default()
        creds = impersonated_credentials.Credentials(
            source_credentials=source_creds,
            target_principal=sa_email,
            target_scopes=DRIVE_SCOPES,
        )
        logger.info("Using impersonated credentials: %s", sa_email)
        return creds

    logger.info("Using Application Default Credentials (no impersonation)")
    creds, _ = google.auth.default(scopes=DRIVE_SCOPES)
    return creds


# ---------------------------------------------------------------------------
# Firestore helpers
# ---------------------------------------------------------------------------


def get_puzzles(db: FirestoreClient) -> dict[str, dict[str, Any]]:
    """Load all puzzles from Firestore, keyed by document ID."""
    puzzles = {}
    for doc in db.collection("puzzles").stream():
        data = doc.to_dict() or {}
        data["id"] = doc.id
        puzzles[doc.id] = data
    return puzzles


def build_drive_name_index(
    puzzles: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build a lookup from Drive filename → puzzle data.

    Drive files are named like:
        "1995-11 Keyholes.pdf"
        "1995-11 Keyholes (solution).pdf"
        "1995-11 Keyholes.svg"
    """
    names: dict[str, dict[str, Any]] = {}
    for puzzle in puzzles.values():
        title = puzzle.get("title", "")
        date = puzzle.get("date")
        pub = puzzle.get("pub", puzzle.get("publication", ""))

        if not title or not date or not pub:
            continue

        # Normalize date to YYYY-MM-DD string
        date_str = str(date)[:10]

        # Build all expected Drive filenames
        doc_name = f"{date_str} {title}"
        for ext in ("pdf", "svg"):
            puzzle_file = f"{date_str} {title}.{ext}"
            solution_file = f"{date_str} {title} (solution).{ext}"
            names[puzzle_file] = puzzle
            names[solution_file] = puzzle
            names[doc_name] = puzzle

    return names


# ---------------------------------------------------------------------------
# Google Drive helpers
# ---------------------------------------------------------------------------


def list_drive_files(credentials) -> list[dict[str, Any]]:
    """List all non-folder, non-doc files from the Hex shared drive."""
    service = build("drive", "v3", credentials=credentials)
    files_resource = service.files()
    fields = "files(id,name,mimeType,driveId,md5Checksum,modifiedTime,size),nextPageToken"
    query = (
        "mimeType != 'application/vnd.google-apps.document'"
        " and mimeType != 'application/vnd.google-apps.folder'"
        " and mimeType != 'application/vnd.google-apps.spreadsheet'"
        " and trashed = false"
    )
    params = {
        "corpora": "drive",
        "driveId": DRIVE_ID,
        "fields": fields,
        "includeItemsFromAllDrives": True,
        "orderBy": "name",
        "pageSize": 1000,
        "q": query,
        "supportsAllDrives": True,
    }
    request = files_resource.list(**params)
    items: list[dict[str, Any]] = []
    while request is not None:
        response = request.execute()
        items.extend(response.get("files", []))
        request = files_resource.list_next(request, response)
    return items


def download_drive_file(file_id: str, credentials) -> io.BytesIO | None:
    """Download a file from Drive by its ID.

    Uses google.auth.transport.requests instead of httplib2 for
    reliable impersonated credential support.
    """
    from google.auth.transport.requests import AuthorizedSession

    session = AuthorizedSession(credentials)
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true"
    try:
        response = session.get(url, timeout=120)
        response.raise_for_status()
        buf = io.BytesIO(response.content)
        return buf
    except Exception as e:
        logger.error("Failed to download %s: %s", file_id, e)
        return None


# ---------------------------------------------------------------------------
# GCS helpers
# ---------------------------------------------------------------------------


def get_dest_blob_md5s(
    gcs: storage.Client,
    bucket_name: str,
    prefix: str = "puzzles/",
) -> dict[str, str]:
    """List all blobs under a prefix and return {name: hex_md5} map."""
    bucket = gcs.bucket(bucket_name)
    blobs: dict[str, str] = {}
    for blob in bucket.list_blobs(prefix=prefix):
        if blob.md5_hash:
            hex_md5 = binascii.hexlify(base64.urlsafe_b64decode(blob.md5_hash)).decode()
            blobs[blob.name] = hex_md5
        else:
            blobs[blob.name] = ""
    return blobs


def build_object_metadata(
    puzzle: dict[str, Any],
    drive_file: dict[str, Any],
    file_type: str,
) -> dict[str, str]:
    """Build GCS custom metadata from puzzle + drive file info."""
    date = puzzle.get("date")
    return {
        "puzzle_id": puzzle["id"],
        "title": puzzle.get("title", ""),
        "pub": puzzle.get("pub", puzzle.get("publication", "")),
        "date": str(date)[:10] if date else "",
        "issue": str(puzzle.get("issue", "")),
        "author": puzzle.get("author", ""),
        "file_type": file_type,
        "file_id": drive_file["id"],
        "md5_checksum": drive_file.get("md5Checksum", ""),
        "mime_type": drive_file.get("mimeType", ""),
        "modified_time": drive_file.get("modifiedTime", ""),
        "size": str(drive_file.get("size", "")),
        "drive_name": drive_file["name"],
    }


# ---------------------------------------------------------------------------
# Core sync logic
# ---------------------------------------------------------------------------


def map_drive_to_gcs(
    drive_files: list[dict[str, Any]],
    puzzle_names: dict[str, dict[str, Any]],
    pub_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Map Drive files to GCS destination paths.

    Returns a list of dicts with keys:
        drive_file, puzzle, object_name, file_type, mime_type
    """
    mappings: list[dict[str, Any]] = []

    for drive_file in drive_files:
        name = drive_file["name"]

        if name not in puzzle_names:
            continue

        puzzle = puzzle_names[name]
        pub = puzzle.get("pub", puzzle.get("publication", ""))
        puzzle_id = puzzle["id"]

        if pub_filter and pub != pub_filter:
            continue

        # Determine file type and destination
        is_solution = "(solution)" in name.lower()

        if name.endswith(".pdf"):
            file_type = "solution_pdf" if is_solution else "puzzle_pdf"
            suffix = "solution.pdf" if is_solution else "puzzle.pdf"
            mime_type = "application/pdf"
        elif name.endswith(".svg"):
            file_type = "solution_svg" if is_solution else "puzzle_svg"
            suffix = "solution.svg" if is_solution else "puzzle.svg"
            mime_type = "image/svg+xml"
        else:
            continue

        object_name = f"puzzles/{pub}/{puzzle_id}/{puzzle_id}_{suffix}"

        mappings.append(
            {
                "drive_file": drive_file,
                "puzzle": puzzle,
                "object_name": object_name,
                "file_type": file_type,
                "mime_type": mime_type,
            }
        )

    return mappings


def sync_files(
    mappings: list[dict[str, Any]],
    existing_blobs: dict[str, str],
    bucket_name: str,
    credentials=None,
    dry_run: bool = True,
) -> dict[str, int]:
    """Sync mapped files to GCS. Returns action counts."""
    gcs = storage.Client(project=DEV_PROJECT)
    bucket = gcs.bucket(bucket_name)

    stats = {"skipped": 0, "uploaded": 0, "failed": 0}

    for mapping in mappings:
        drive_file = mapping["drive_file"]
        puzzle = mapping["puzzle"]
        object_name = mapping["object_name"]
        file_type = mapping["file_type"]
        mime_type = mapping["mime_type"]
        drive_md5 = drive_file.get("md5Checksum", "")

        # Check if blob exists with matching MD5
        existing_md5 = existing_blobs.get(object_name)
        if existing_md5 is not None and existing_md5 == drive_md5:
            stats["skipped"] += 1
            continue

        action = "would upload" if dry_run else "uploading"
        title = puzzle.get("title", "?")
        logger.info(
            "  %s %s → %s (%s)",
            action,
            drive_file["name"],
            object_name,
            title,
        )

        if dry_run:
            stats["uploaded"] += 1
            continue

        # Download from Drive
        contents = download_drive_file(drive_file["id"], credentials)
        if contents is None:
            stats["failed"] += 1
            continue

        # Upload to GCS
        blob = bucket.blob(object_name)
        blob.metadata = build_object_metadata(puzzle, drive_file, file_type)
        blob.upload_from_file(contents, content_type=mime_type)
        stats["uploaded"] += 1

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the Drive → GCS sync."""
    parser = argparse.ArgumentParser(description="Sync puzzle PDFs/SVGs from Google Drive to GCS")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually upload (default is dry run)",
    )
    parser.add_argument(
        "--pub",
        type=str,
        default=None,
        help="Only sync puzzles for this publication (e.g., 'wsj')",
    )
    parser.add_argument(
        "--bucket",
        type=str,
        default=ASSETS_BUCKET,
        help=f"Target bucket (default: {ASSETS_BUCKET})",
    )
    args = parser.parse_args()

    dry_run = not args.apply
    mode = "APPLY" if args.apply else "DRY RUN"
    logger.info("=== Drive → GCS Sync (%s) ===", mode)
    logger.info("Target bucket: %s", args.bucket)
    if args.pub:
        logger.info("Publication filter: %s", args.pub)
    logger.info("")

    # Load puzzle data from Firestore
    logger.info("Loading puzzles from Firestore (%s)...", PROD_PROJECT)
    db = FirestoreClient(project=PROD_PROJECT)
    puzzles = get_puzzles(db)
    logger.info("  Found %d puzzles", len(puzzles))

    # Build Drive filename → puzzle lookup
    puzzle_names = build_drive_name_index(puzzles)
    logger.info("  Built index with %d Drive filename mappings", len(puzzle_names))

    # Get Drive credentials
    credentials = get_drive_credentials()

    # List files from Drive
    logger.info("Listing files from shared drive...")
    drive_files = list_drive_files(credentials)
    logger.info("  Found %d files in Drive", len(drive_files))

    # Map Drive files to GCS destinations
    mappings = map_drive_to_gcs(drive_files, puzzle_names, pub_filter=args.pub)
    logger.info("  Mapped %d files to sync", len(mappings))

    # List existing blobs in destination
    logger.info("Listing existing blobs in %s...", args.bucket)
    gcs = storage.Client(project=DEV_PROJECT)
    existing = get_dest_blob_md5s(gcs, args.bucket, prefix="puzzles/")
    logger.info("  Found %d existing blobs", len(existing))

    # Sync
    logger.info("")
    logger.info("Syncing files...")
    stats = sync_files(mappings, existing, args.bucket, credentials=credentials, dry_run=dry_run)

    logger.info("")
    logger.info("=== Results ===")
    logger.info("  Uploaded:  %d", stats["uploaded"])
    logger.info("  Skipped:   %d (already up-to-date)", stats["skipped"])
    logger.info("  Failed:    %d", stats["failed"])

    if dry_run:
        logger.info("")
        logger.info("This was a dry run. Use --apply to upload.")

    # Report unmatched Drive files
    unmatched = [f for f in drive_files if f["name"] not in puzzle_names and not f["name"].endswith(".png")]
    if unmatched:
        logger.info("")
        logger.info("Unmatched Drive files (%d):", len(unmatched))
        for f in sorted(unmatched, key=lambda x: x["name"])[:20]:
            logger.info("  ? %s", f["name"])
        if len(unmatched) > 20:
            logger.info("  ... and %d more", len(unmatched) - 20)


if __name__ == "__main__":
    main()
