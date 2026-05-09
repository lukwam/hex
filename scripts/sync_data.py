#!/usr/bin/env python3
"""Copy Firestore data from production to the dev database.

Reads raw documents from the prod Firestore, hydrates them through
firedantic models, then uses CollectionSync from firedantic-extras
to write to the dev project with batching, diffs, and dry-run support.

Usage:
    python scripts/sync_data.py                    # Dry run (default)
    python scripts/sync_data.py --apply            # Actually write
    python scripts/sync_data.py --collections puzzles books
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

from firedantic.configurations import configuration
from firedantic_extras import CollectionSync
from google.cloud.firestore_v1 import Client

# Add repo root to path
sys.path.insert(0, ".")

from services.shared.models import Book, Publication, Puzzle, Solve, User  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)

# Model registry: collection name → firedantic model class
COLLECTION_MODELS: dict[str, type] = {
    "books": Book,
    "publications": Publication,
    "puzzles": Puzzle,
    "solves": Solve,
    "users": User,
}

# Source and target configuration
PROD_PROJECT = "lukwam-hex"
PROD_DATABASE = "(default)"
DEV_PROJECT = "lukwam-hex-dev"
DEV_DATABASE = "(default)"


def read_collection(client: Client, collection: str) -> list[dict[str, Any]]:
    """Read all documents from a Firestore collection."""
    results = []
    for doc in client.collection(collection).stream():
        data = doc.to_dict() or {}
        data["id"] = doc.id
        results.append(data)
    return results


def hydrate(model_class: type, raw_docs: list[dict[str, Any]]) -> list:
    """Hydrate raw Firestore dicts into firedantic model instances."""
    instances = []
    for data in raw_docs:
        try:
            instance = model_class(**data)
            instances.append(instance)
        except Exception as e:
            logger.warning("  Skipping %s: %s", data.get("id", "?"), e)
    return instances


def main() -> None:
    """Run the sync."""
    parser = argparse.ArgumentParser(description="Sync Firestore data from prod to dev")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write to dev (default is dry run)",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show field-level diffs for updated documents",
    )
    parser.add_argument(
        "--collections",
        nargs="+",
        choices=list(COLLECTION_MODELS.keys()),
        default=list(COLLECTION_MODELS.keys()),
        help="Collections to sync (default: all)",
    )
    args = parser.parse_args()

    dry_run = not args.apply
    mode = "APPLY" if args.apply else "DRY RUN"
    logger.info("=== Hex Data Sync (%s) ===", mode)
    logger.info("Source: %s / %s", PROD_PROJECT, PROD_DATABASE)
    logger.info("Target: %s / %s", DEV_PROJECT, DEV_DATABASE)
    logger.info("")

    # Source client (raw Firestore reads from prod)
    source_client = Client(project=PROD_PROJECT, database=PROD_DATABASE)

    # Configure firedantic to target dev
    configuration.add(
        name="(default)",
        project=DEV_PROJECT,
        database=DEV_DATABASE,
        client=Client(project=DEV_PROJECT, database=DEV_DATABASE),
    )

    has_errors = False

    for collection in args.collections:
        model_class = COLLECTION_MODELS[collection]

        logger.info("Reading %s from %s ...", collection, PROD_PROJECT)
        raw_docs = read_collection(source_client, collection)
        logger.info("  Found %d documents", len(raw_docs))

        instances = hydrate(model_class, raw_docs)
        logger.info("  Hydrated %d / %d", len(instances), len(raw_docs))

        result = CollectionSync.sync(
            model_class,
            instances,
            dry_run=dry_run,
            diff=args.diff,
            on_error="collect",
            output_writer=lambda msg: logger.info("  %s", msg),
        )

        logger.info("  %s", result.summary())

        if result.diffs:
            for key, doc_diff in result.diffs.items():
                for fd in doc_diff.changes:
                    logger.info("    %s.%s: %s → %s", key, fd.field, fd.before, fd.after)

        if result.has_errors:
            has_errors = True
            for err in result.errors:
                logger.warning("  Error: %s — %s", err.sync_key_value, err.error)

    logger.info("")
    if dry_run:
        logger.info("This was a dry run. Use --apply to write to dev.")

    if has_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
