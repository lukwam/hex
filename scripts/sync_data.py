#!/usr/bin/env python3
"""Copy Firestore data from production to the dev database.

Reads puzzle metadata from lukwam-hex and enriched data (grid, clues,
files, links) from altissimo-coxrathvon, merges them, then hydrates
through firedantic models and syncs to the dev project.

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
from hexword import HexwordService

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
CR_PROJECT = "altissimo-coxrathvon"
CR_DATABASE = "(default)"
DEV_PROJECT = "lukwam-hex-dev"
DEV_DATABASE = "(default)"

hexword_service = HexwordService()


def read_collection(client: Client, collection: str) -> list[dict[str, Any]]:
    """Read all documents from a Firestore collection."""
    results = []
    for doc in client.collection(collection).stream():
        data = doc.to_dict() or {}
        data["id"] = doc.id
        results.append(data)
    return results


def _transform_hex_puzzle(hex_doc: dict[str, Any]) -> dict[str, Any]:
    """Transform a lukwam-hex puzzle doc to the new model's field names.

    Renames pub→publication, num→number, and nests flat link fields.
    """
    doc = dict(hex_doc)

    # Rename fields
    if "pub" in doc:
        doc["publication"] = doc.pop("pub")
    if "num" in doc:
        doc["number"] = doc.pop("num")

    # Nest flat link fields into a links dict
    link_fields = [
        "puzzle_link",
        "answer_link",
        "googledoc_link",
        "puzzleme_link",
        "web_link",
    ]
    links = {}
    for field in link_fields:
        if field in doc:
            val = doc.pop(field)
            if val:
                links[field] = val
    if links:
        doc["links"] = links

    return doc


def _normalize_settings(settings: dict) -> dict:
    """Normalize legacy type mismatches in puzzle settings.

    Some production docs store string settings as bool and vice versa.
    Fix them here so the data arrives clean in dev.
    """
    patched = dict(settings)

    # String fields that may arrive as bool
    for key, true_val in (("show_enumerations", "answers"), ("show_grid_bars", "all")):
        if key in patched and isinstance(patched[key], bool):
            patched[key] = true_val if patched[key] else ""

    # Bool fields that may arrive as empty string
    for key in (
        "show_grid_border",
        "show_grid_entries",
        "show_grid_labels",
        "show_grid_lines",
        "show_starred_entries_in_grid",
    ):
        if key in patched and isinstance(patched[key], str):
            patched[key] = patched[key].lower() not in ("", "false", "0", "no")

    return patched


def _convert_clue_strings(clue_groups: list[dict]) -> list[dict]:
    """Convert tilde-delimited clue strings to structured Clue dicts.

    If a clue is already a dict (structured), leave it as-is.
    If it's a string (tilde format), parse it via HexwordService.
    """
    converted = []
    for group in clue_groups:
        new_group = dict(group)
        new_clues = []
        for clue in group.get("clues", []):
            if isinstance(clue, dict):
                new_clues.append(clue)
            elif isinstance(clue, str):
                try:
                    parsed = hexword_service.parse_clue(clue)
                    new_clues.append(parsed.model_dump())
                except Exception as e:
                    logger.warning("  Failed to parse clue: %s — %s", clue[:60], e)
                    # Keep as-is in a minimal dict
                    new_clues.append({"name": "?", "clue_text": clue, "answers": [], "annotations": []})
            else:
                new_clues.append(clue)
        new_group["clues"] = new_clues
        converted.append(new_group)
    return converted


def merge_puzzle_sources(
    hex_docs: list[dict[str, Any]],
    cr_docs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge puzzle data from lukwam-hex and altissimo-coxrathvon.

    The coxrathvon data is the richer source (has author, files, links,
    grid data). We use it as the primary, falling back to hex for any
    puzzle that only exists there.
    """
    cr_by_id = {d["id"]: d for d in cr_docs}
    hex_by_id = {d["id"]: d for d in hex_docs}

    merged = []

    # Start with all coxrathvon docs (the primary, richer source)
    for _, cr_doc in cr_by_id.items():
        doc = dict(cr_doc)

        # Convert tilde-delimited clue strings to structured format
        if doc.get("clue_groups"):
            doc["clue_groups"] = _convert_clue_strings(doc["clue_groups"])

        # Normalize settings type mismatches
        if doc.get("settings"):
            doc["settings"] = _normalize_settings(doc["settings"])

        merged.append(doc)

    # Add any hex-only docs (e.g., "Departure")
    for doc_id, hex_doc in hex_by_id.items():
        if doc_id not in cr_by_id:
            transformed = _transform_hex_puzzle(hex_doc)
            logger.info("  Adding hex-only puzzle: %s (%s)", doc_id, transformed.get("title"))
            merged.append(transformed)

    return merged


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
    logger.info("Source (metadata): %s / %s", PROD_PROJECT, PROD_DATABASE)
    logger.info("Source (enriched): %s / %s", CR_PROJECT, CR_DATABASE)
    logger.info("Target: %s / %s", DEV_PROJECT, DEV_DATABASE)
    logger.info("")

    # Source clients
    prod_client = Client(project=PROD_PROJECT, database=PROD_DATABASE)
    cr_client = Client(project=CR_PROJECT, database=CR_DATABASE)

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

        if collection == "puzzles":
            # Two-source merge for puzzles
            logger.info("Reading puzzles from %s ...", PROD_PROJECT)
            hex_docs = read_collection(prod_client, "puzzles")
            logger.info("  Found %d documents", len(hex_docs))

            logger.info("Reading puzzles from %s ...", CR_PROJECT)
            cr_docs = read_collection(cr_client, "puzzles")
            logger.info("  Found %d documents", len(cr_docs))

            logger.info("Merging puzzle sources ...")
            raw_docs = merge_puzzle_sources(hex_docs, cr_docs)
            logger.info("  Merged into %d documents", len(raw_docs))
        else:
            logger.info("Reading %s from %s ...", collection, PROD_PROJECT)
            raw_docs = read_collection(prod_client, collection)
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
