"""Copy puzzle files from prod buckets to the new consolidated assets bucket.

One-time bootstrap: copies files from the existing Gen2 prod buckets
(archive, archive-images, thumbnails) into the new `lukwam-hex-assets-dev`
bucket using the standard directory layout. Also copies book covers.

Uses server-side blob.rewrite() for speed — no local download/upload.
Idempotent: skips blobs that already exist at the destination.

After copying, records each file's GCS state (md5, etag, metageneration)
in the puzzle's Firestore manifest (puzzle.files) for future sync checks.

Also scans existing dest blobs to backfill manifest entries for files
that were copied before the manifest existed (e.g. from the Drive sync).

Usage:
    python scripts/copy_bucket_files.py                # Dry run (default)
    python scripts/copy_bucket_files.py --apply         # Actually copy
    python scripts/copy_bucket_files.py --apply --pub wsj
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

from firedantic.configurations import configuration
from google.cloud import storage
from google.cloud.firestore_v1 import Client as FirestoreClient

# Add repo root to path
sys.path.insert(0, ".")

from services.shared.models import FileRecord, Puzzle  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)

# Source (prod)
PROD_PROJECT = "lukwam-hex"

# Destination
DEV_PROJECT = "lukwam-hex-dev"
ASSETS_BUCKET = "lukwam-hex-assets-dev"

# Source buckets and their file type mappings
# Gen2 bucket → suffix → (dest_suffix, content_type, file_type_field)
SOURCE_MAP = {
    "lukwam-hex-archive": {
        "_puzzle.pdf": ("_puzzle.pdf", "application/pdf", "puzzle_pdf"),
        "_solution.pdf": ("_solution.pdf", "application/pdf", "solution_pdf"),
        "_puzzle.svg": ("_puzzle.svg", "image/svg+xml", "puzzle_svg"),
        "_solution.svg": ("_solution.svg", "image/svg+xml", "solution_svg"),
    },
    "lukwam-hex-archive-images": {
        "_puzzle.png": ("_puzzle.png", "image/png", "puzzle_png"),
        "_solution.png": ("_solution.png", "image/png", "solution_png"),
    },
    "lukwam-hex-thumbnails": {
        "_puzzle.png": ("_puzzle_thumb.png", "image/png", "puzzle_thumb"),
        "_solution.png": ("_solution_thumb.png", "image/png", "solution_thumb"),
    },
}

# Maps GCS dest path suffix → PuzzleFiles field name
SUFFIX_TO_FIELD = {
    "_puzzle.pdf": "puzzle_pdf",
    "_solution.pdf": "solution_pdf",
    "_puzzle.svg": "puzzle_svg",
    "_solution.svg": "solution_svg",
    "_puzzle.png": "puzzle_png",
    "_solution.png": "solution_png",
    "_puzzle_thumb.png": "puzzle_thumb",
    "_solution_thumb.png": "solution_thumb",
}


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


def get_books(db: FirestoreClient) -> dict[str, dict[str, Any]]:
    """Load all books from Firestore, keyed by document ID."""
    books = {}
    for doc in db.collection("books").stream():
        data = doc.to_dict() or {}
        data["id"] = doc.id
        books[doc.id] = data
    return books


def load_dev_puzzles() -> dict[str, Puzzle]:
    """Load puzzles from dev Firestore as model instances."""
    puzzles = {}
    for p in Puzzle.find({}):
        puzzles[p.id] = p
    return puzzles


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------


def parse_gen2_name(blob_name: str) -> tuple[str, str, str] | None:
    """Parse a Gen2 blob name like 'wsj/abc123_puzzle.pdf'.

    Returns (pub, puzzle_id, suffix) or None if not parseable.
    """
    if "/" not in blob_name:
        return None
    pub, filename = blob_name.split("/", 1)
    # filename is like 'abc123_puzzle.pdf'
    for suffix in ("_puzzle.pdf", "_solution.pdf", "_puzzle.svg", "_solution.svg", "_puzzle.png", "_solution.png"):
        if filename.endswith(suffix):
            puzzle_id = filename[: -len(suffix)]
            return pub, puzzle_id, suffix
    return None


def parse_dest_name(dest_name: str) -> tuple[str, str] | None:
    """Parse a dest blob name like 'puzzles/wsj/abc123/abc123_puzzle.pdf'.

    Returns (puzzle_id, file_field) or None if not parseable.
    """
    parts = dest_name.split("/")
    if len(parts) != 4 or parts[0] != "puzzles":
        return None
    puzzle_id = parts[2]
    filename = parts[3]
    # Strip puzzle_id prefix to get the suffix
    if filename.startswith(puzzle_id):
        suffix = filename[len(puzzle_id) :]
        field = SUFFIX_TO_FIELD.get(suffix)
        if field:
            return puzzle_id, field
    return None


def build_metadata(
    puzzle: dict[str, Any],
    file_type: str,
    source_bucket: str,
) -> dict[str, str]:
    """Build GCS custom metadata from puzzle data."""
    date = puzzle.get("date")
    return {
        "puzzle_id": puzzle["id"],
        "title": puzzle.get("title", ""),
        "pub": puzzle.get("pub", puzzle.get("publication", "")),
        "date": str(date)[:10] if date else "",
        "issue": str(puzzle.get("issue", "")),
        "author": puzzle.get("author", ""),
        "file_type": file_type,
        "source_bucket": source_bucket,
    }


def blob_to_file_record(blob: storage.Blob) -> FileRecord:
    """Build a FileRecord from a GCS blob's properties."""
    return FileRecord(
        path=blob.name,
        gcs_md5=blob.md5_hash or "",
        gcs_etag=blob.etag or "",
        gcs_metageneration=blob.metageneration or 0,
        size=blob.size or 0,
        content_type=blob.content_type or "",
    )


def update_puzzle_manifest(
    puzzle: Puzzle,
    field_name: str,
    record: FileRecord,
) -> None:
    """Update a puzzle's file manifest with a new FileRecord and save."""
    setattr(puzzle.files, field_name, record)
    puzzle.save()


# ---------------------------------------------------------------------------
# Copy logic
# ---------------------------------------------------------------------------


def copy_puzzle_files(
    gcs: storage.Client,
    prod_puzzles: dict[str, dict[str, Any]],
    dev_puzzles: dict[str, Puzzle],
    existing_dest: dict[str, storage.Blob],
    pub_filter: str | None = None,
    dry_run: bool = True,
) -> dict[str, int]:
    """Copy puzzle files from prod Gen2 buckets to the assets bucket."""
    dest_bucket = gcs.bucket(ASSETS_BUCKET)
    stats = {"copied": 0, "skipped": 0, "unmatched": 0, "manifest_updated": 0}

    for source_bucket_name, suffix_map in SOURCE_MAP.items():
        logger.info("Processing %s...", source_bucket_name)
        source_bucket = gcs.bucket(source_bucket_name)

        for blob in source_bucket.list_blobs():
            parsed = parse_gen2_name(blob.name)
            if parsed is None:
                stats["unmatched"] += 1
                continue

            pub, puzzle_id, suffix = parsed

            if pub_filter and pub != pub_filter:
                continue

            if puzzle_id not in prod_puzzles:
                stats["unmatched"] += 1
                continue

            # Look up the suffix mapping for this source bucket
            if suffix not in suffix_map:
                continue

            dest_suffix, content_type, file_type = suffix_map[suffix]
            dest_name = f"puzzles/{pub}/{puzzle_id}/{puzzle_id}{dest_suffix}"

            # Determine the manifest field name
            field_name = SUFFIX_TO_FIELD.get(dest_suffix)

            # Idempotent: skip if already exists in dest bucket
            if dest_name in existing_dest:
                # File exists — check if manifest needs backfilling
                if field_name and puzzle_id in dev_puzzles:
                    dev_puzzle = dev_puzzles[puzzle_id]
                    existing_record = getattr(dev_puzzle.files, field_name)
                    if not existing_record.path:
                        # Manifest missing — backfill from existing blob
                        existing_blob = existing_dest[dest_name]
                        record = blob_to_file_record(existing_blob)
                        action = "would backfill manifest" if dry_run else "backfilling manifest"
                        logger.info("  %s %s (%s)", action, dest_name, field_name)
                        if not dry_run:
                            update_puzzle_manifest(dev_puzzle, field_name, record)
                        stats["manifest_updated"] += 1

                stats["skipped"] += 1
                continue

            puzzle = prod_puzzles[puzzle_id]
            action = "would copy" if dry_run else "copying"
            logger.info("  %s %s → %s", action, blob.name, dest_name)

            if not dry_run:
                dest_blob = dest_bucket.blob(dest_name)
                dest_blob.content_type = content_type
                dest_blob.metadata = build_metadata(puzzle, file_type, source_bucket_name)

                # Server-side copy (rewrite handles cross-location/project)
                token = None
                while True:
                    token, _, _ = dest_blob.rewrite(blob, token=token)
                    if token is None:
                        break

                # Update metadata after copy
                dest_blob.patch()

                # Re-read blob to get final GCS state (etag, metageneration)
                dest_blob.reload()

                # Update Firestore manifest
                if field_name and puzzle_id in dev_puzzles:
                    record = blob_to_file_record(dest_blob)
                    update_puzzle_manifest(dev_puzzles[puzzle_id], field_name, record)
                    stats["manifest_updated"] += 1

            stats["copied"] += 1
            existing_dest[dest_name] = dest_blob if not dry_run else None  # type: ignore

    return stats


def copy_book_covers(
    gcs: storage.Client,
    books: dict[str, dict[str, Any]],
    existing_dest: dict[str, storage.Blob],
    dry_run: bool = True,
) -> dict[str, int]:
    """Copy book cover images from lukwam-hex-images to the assets bucket."""
    source_bucket = gcs.bucket("lukwam-hex-images")
    dest_bucket = gcs.bucket(ASSETS_BUCKET)
    stats = {"copied": 0, "skipped": 0}

    for blob in source_bucket.list_blobs():
        if not blob.name.endswith("_cover.png"):
            continue

        # Extract book ID: {bookId}_cover.png
        book_id = blob.name.replace("_cover.png", "")
        if book_id not in books:
            continue

        dest_name = f"books/{book_id}/{book_id}_cover.png"

        if dest_name in existing_dest:
            stats["skipped"] += 1
            continue

        book = books[book_id]
        action = "would copy" if dry_run else "copying"
        logger.info("  %s %s → %s (%s)", action, blob.name, dest_name, book.get("title", "?"))

        if not dry_run:
            dest_blob = dest_bucket.blob(dest_name)
            dest_blob.content_type = "image/png"
            dest_blob.metadata = {
                "book_id": book_id,
                "title": book.get("title", ""),
                "file_type": "cover",
                "source_bucket": "lukwam-hex-images",
            }
            token = None
            while True:
                token, _, _ = dest_blob.rewrite(blob, token=token)
                if token is None:
                    break
            dest_blob.patch()

        stats["copied"] += 1
        existing_dest[dest_name] = dest_blob if not dry_run else None  # type: ignore

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the bucket copy."""
    parser = argparse.ArgumentParser(description="Copy puzzle files from prod buckets to the new assets bucket")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually copy (default is dry run)",
    )
    parser.add_argument(
        "--pub",
        type=str,
        default=None,
        help="Only copy puzzles for this publication",
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
    logger.info("=== Bucket Copy (%s) ===", mode)
    logger.info("Target: %s", args.bucket)
    if args.pub:
        logger.info("Publication filter: %s", args.pub)
    logger.info("")

    # Load puzzle data from prod Firestore (for object metadata)
    logger.info("Loading puzzle data from %s...", PROD_PROJECT)
    prod_db = FirestoreClient(project=PROD_PROJECT)
    prod_puzzles = get_puzzles(prod_db)
    books = get_books(prod_db)
    logger.info("  Puzzles: %d, Books: %d", len(prod_puzzles), len(books))

    # Configure firedantic to target dev Firestore (for manifest writes)
    dev_client = FirestoreClient(project=DEV_PROJECT)
    configuration.add(
        name="(default)",
        project=DEV_PROJECT,
        database="(default)",
        client=dev_client,
    )

    # Load dev puzzles (for manifest read/write)
    logger.info("Loading dev puzzles for manifest...")
    dev_puzzles = load_dev_puzzles()
    logger.info("  Found %d dev puzzles", len(dev_puzzles))

    # GCS client
    gcs = storage.Client(project=PROD_PROJECT)

    # List existing destination blobs (with full metadata)
    logger.info("Listing existing blobs in %s...", args.bucket)
    dest_bucket = gcs.bucket(args.bucket)
    existing: dict[str, storage.Blob] = {blob.name: blob for blob in dest_bucket.list_blobs()}
    logger.info("  Found %d existing blobs", len(existing))

    # Copy puzzle files
    logger.info("")
    logger.info("Copying puzzle files...")
    puzzle_stats = copy_puzzle_files(
        gcs,
        prod_puzzles,
        dev_puzzles,
        existing,
        pub_filter=args.pub,
        dry_run=dry_run,
    )
    logger.info(
        "  Copied: %d, Skipped: %d, Unmatched: %d, Manifest: %d",
        puzzle_stats["copied"],
        puzzle_stats["skipped"],
        puzzle_stats["unmatched"],
        puzzle_stats["manifest_updated"],
    )

    # Copy book covers
    if not args.pub:
        logger.info("")
        logger.info("Copying book covers...")
        book_stats = copy_book_covers(gcs, books, existing, dry_run=dry_run)
        logger.info("  Copied: %d, Skipped: %d", book_stats["copied"], book_stats["skipped"])

    logger.info("")
    if dry_run:
        logger.info("This was a dry run. Use --apply to copy.")


if __name__ == "__main__":
    main()
