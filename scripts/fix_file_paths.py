#!/usr/bin/env python3
"""Fix legacy gs:// file paths in Firestore puzzle documents.

The sync_data.py migration preserved the original gs:// URIs from the
coxrathvon source (e.g., gs://lukwam-hex-archive/wsj/ID_puzzle.pdf).
The files were already copied to the consolidated assets bucket during
copy_bucket_files.py, but the Firestore records still point to the old
bucket paths.

This script rewrites those paths to relative paths in the consolidated
assets bucket (e.g., puzzles/wsj/ID/ID_puzzle.pdf) and verifies each
file exists before updating.

Usage:
    # Dry run against dev
    poetry run python scripts/fix_file_paths.py --env dev

    # Dry run against prod
    poetry run python scripts/fix_file_paths.py --env prod

    # Apply changes
    poetry run python scripts/fix_file_paths.py --env dev --apply
"""

from __future__ import annotations

import argparse
import logging
import sys

from google.cloud import firestore, storage  # type: ignore[attr-defined]

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

ENV_CONFIG = {
    "dev": {
        "project": "lukwam-hex-dev",
        "bucket": "lukwam-hex-assets-dev",
    },
    "prod": {
        "project": "lukwam-hex",
        "bucket": "lukwam-hex-assets",
    },
}

# The 8 file slots in the PuzzleFiles model
FILE_KEYS = [
    "puzzle_pdf",
    "puzzle_png",
    "puzzle_svg",
    "puzzle_thumb",
    "solution_pdf",
    "solution_png",
    "solution_svg",
    "solution_thumb",
]


def resolve_legacy_path(
    gs_uri: str,
    puzzle_id: str,
    publication: str,
    file_key: str,
) -> str:
    """Convert a legacy gs:// URI to a relative assets-bucket path.

    Legacy format:  gs://lukwam-hex-archive/wsj/ID_puzzle.pdf
    Target format:  puzzles/wsj/ID/ID_puzzle.pdf
    """
    # Extract the filename from the gs:// URI
    # e.g., gs://lukwam-hex-archive/wsj/ID_puzzle.pdf -> ID_puzzle.pdf
    filename = gs_uri.rsplit("/", 1)[-1]

    # Build the expected path
    return f"puzzles/{publication}/{puzzle_id}/{filename}"


def main() -> None:
    """Fix legacy file paths in Firestore."""
    parser = argparse.ArgumentParser(description="Fix legacy gs:// file paths in Firestore")
    parser.add_argument(
        "--env",
        required=True,
        choices=list(ENV_CONFIG.keys()),
        help="Target environment",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write changes (default is dry run)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of puzzles to process (0 = all)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Verify files exist in assets bucket before updating (default: True)",
    )
    args = parser.parse_args()

    env = ENV_CONFIG[args.env]
    project = env["project"]
    bucket_name = env["bucket"]
    dry_run = not args.apply
    mode = "DRY RUN" if dry_run else "APPLY"

    logger.info("=== Fix File Paths (%s) — env=%s ===", mode, args.env)
    logger.info("Project: %s", project)
    logger.info("Assets bucket: %s", bucket_name)
    logger.info("")

    db = firestore.Client(project=project)
    sc = storage.Client(project=project)
    bucket = sc.bucket(bucket_name)

    # Read all puzzles
    all_puzzles = list(db.collection("puzzles").stream())
    logger.info("Found %d puzzles", len(all_puzzles))

    # Stats
    total_fixes = 0
    total_verified = 0
    total_missing = 0
    total_skipped = 0
    puzzles_updated = 0
    puzzles_with_issues = []

    processed = 0
    for doc in all_puzzles:
        if args.limit and processed >= args.limit:
            break

        data = doc.to_dict()
        if data is None:
            continue
        puzzle_id = doc.id
        publication = data.get("publication", "")
        files = data.get("files", {})

        if not isinstance(files, dict):
            continue

        # Check each file slot
        updates = {}
        for file_key in FILE_KEYS:
            fv = files.get(file_key, {})
            if not isinstance(fv, dict):
                continue

            path = fv.get("path", "")
            if not path or not path.startswith("gs://"):
                continue

            # Resolve the legacy path
            new_path = resolve_legacy_path(path, puzzle_id, publication, file_key)

            # Verify the file exists in the assets bucket
            if args.verify:
                blob = bucket.blob(new_path)
                if blob.exists():
                    total_verified += 1
                else:
                    total_missing += 1
                    logger.warning(
                        "  MISSING: %s → %s (file not in assets bucket)",
                        path,
                        new_path,
                    )
                    puzzles_with_issues.append((puzzle_id, file_key, path, new_path))
                    continue

            updates[f"files.{file_key}.path"] = new_path
            total_fixes += 1

        if updates:
            processed += 1
            puzzles_updated += 1
            title = data.get("title", "")
            logger.info(
                "  %s [%s] %s — %d path(s) to fix",
                puzzle_id,
                publication,
                title[:40],
                len(updates),
            )
            for field, new_path in updates.items():
                old_val: object = data
                for part in field.split("."):
                    old_val = old_val.get(part, {}) if isinstance(old_val, dict) else ""
                logger.info("    %s: %s → %s", field, old_val, new_path)

            if not dry_run:
                db.collection("puzzles").document(puzzle_id).update(updates)
        else:
            total_skipped += 1

    # Summary
    logger.info("")
    logger.info("=== Summary ===")
    logger.info("Puzzles scanned: %d", len(all_puzzles))
    logger.info("Puzzles with fixes: %d", puzzles_updated)
    logger.info("Puzzles skipped (no legacy paths): %d", total_skipped)
    logger.info("Total paths fixed: %d", total_fixes)
    logger.info("Files verified in bucket: %d", total_verified)
    logger.info("Files MISSING from bucket: %d", total_missing)

    if puzzles_with_issues:
        logger.warning("")
        logger.warning("=== Missing Files ===")
        for pid, fkey, old, new in puzzles_with_issues:
            logger.warning("  %s.%s: %s → %s", pid, fkey, old, new)

    if dry_run:
        logger.info("")
        logger.info("This was a dry run. Use --apply to write changes.")

    if total_missing > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
