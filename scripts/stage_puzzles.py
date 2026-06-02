#!/usr/bin/env python3
"""Ingestion Script for Puzzle Staging.

deterministic horizontal gutters + Gemini Flash clue parsing to stage
crossword puzzles for human review and validation before live publication.

Usage:
    # Stage a specific puzzle
    poetry run python scripts/stage_puzzles.py --puzzle-id 1wtRQfsB68mMppdrumt4

    # Stage all unprocessed puzzles (limit to 5)
    poetry run python scripts/stage_puzzles.py --all-unprocessed --limit 5
"""

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from google import genai
from google.cloud import firestore
from firedantic.configurations import configuration
from google.cloud.firestore_v1 import Client

# Add project root to path to resolve scripts imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.pdf_extractor import PDFExtractor, download_puzzle_pdf
from scripts.parse_clues import CLUE_STRUCTURING_PROMPT, PROJECT, MODEL, LOCATION
from services.shared.models import Puzzle, StagingPuzzle
from hexword import ClueGroup, Clue

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

def setup_environment(env_arg: str | None) -> None:
    """Configure environment variables, initialize Firedantic, and inject dynamic config into submodules."""
    import os
    env = env_arg
    if not env:
        # Fallback to existing environment variables, defaulting to dev
        proj = os.environ.get("GOOGLE_CLOUD_PROJECT", "lukwam-hex-dev")
        env = "prod" if proj == "lukwam-hex" else "dev"

    if env == "dev":
        os.environ["GOOGLE_CLOUD_PROJECT"] = "lukwam-hex-dev"
        os.environ["HEX_ENV"] = "dev"
        os.environ["HEX_DB_NAME"] = "(default)"
    else:
        os.environ["GOOGLE_CLOUD_PROJECT"] = "lukwam-hex"
        os.environ["HEX_ENV"] = "prod"
        os.environ["HEX_DB_NAME"] = "(default)"

    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    database = os.environ["HEX_DB_NAME"]

    logger.info("Selected Environment: '%s' (Project: '%s', Database: '%s')", env, project, database)

    # Initialize Firedantic
    configuration.add(
        name="(default)",
        project=project,
        database=database,
        client=Client(project=project, database=database),
    )

    # Dynamically inject the active project ID and bucket name into submodules to guarantee consistency
    import scripts.pdf_extractor
    import scripts.parse_clues

    scripts.pdf_extractor.PROJECT = project
    scripts.pdf_extractor.BUCKET = "lukwam-hex-assets" if env == "prod" else f"lukwam-hex-assets-{env}"
    scripts.parse_clues.PROJECT = project




def stage_single_puzzle(puzzle_id: str) -> bool:
    """Extract PDF text, parse with Gemini, and save to puzzles_staging collection."""
    logger.info("=========================================")
    logger.info("Staging Puzzle: %s", puzzle_id)
    logger.info("=========================================")

    # 1. Fetch metadata from the live puzzles collection
    try:
        live_puzzle = Puzzle.get_by_id(puzzle_id)
    except Exception:
        logger.error("  Puzzle %s not found in the live puzzles collection", puzzle_id)
        return False

    # 2. Extract PDF text
    logger.info("  1. Deterministically extracting PDF layout...")
    try:
        pdf_bytes, _ = download_puzzle_pdf(puzzle_id)
        extractor = PDFExtractor(pdf_bytes, puzzle_id)
        extracted_text = extractor.extract_pdfplumber_dynamic_columns()
    except Exception as e:
        logger.error("  PDF extraction failed: %s", e)
        return False

    if not extracted_text.strip():
        logger.error("  Extracted PDF text is empty. Puzzle may be scanned/image-based only.")
        return False

    # 3. Call Gemini to parse and structure
    logger.info("  2. Calling Gemini Flash to structure clues...")
    try:
        client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)

        response = client.models.generate_content(
            model=MODEL,
            contents=[CLUE_STRUCTURING_PROMPT + extracted_text],
            config=genai.types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        parsed_data = json.loads(response.text or "{}")
    except Exception as e:
        logger.error("  Gemini parsing failed: %s", e)
        return False

    # 4. Map parsed structure to ClueGroup and Clue models
    clue_groups = []
    for g in parsed_data.get("clue_groups", []):
        g_name = str(g.get("name") or "").strip()
        if not g_name:
            continue
        
        clues = []
        for c in g.get("clues", []):
            c_name = str(c.get("name") or "").strip()
            c_text = str(c.get("clue_text") or "").strip()
            c_enum = str(c.get("enumeration") or "").strip()
            
            # Combine clue text and enumeration for standard hexword display
            full_text = f"{c_text} {c_enum}".strip() if c_enum else c_text
            
            clues.append(Clue(
                name=c_name,
                clue_text=full_text,
                starred=bool(c.get("starred", False)),
                answers=[],
                annotations=[],
            ))
        
        clue_groups.append(ClueGroup(name=g_name, clues=clues))

    # 5. Save to the puzzles_staging collection with status "pending"
    staging_puzzle = StagingPuzzle(
        id=puzzle_id,  # Match the document ID exactly
        title=live_puzzle.title,
        author=live_puzzle.author,
        publication=live_puzzle.publication,
        number=live_puzzle.number,
        date=live_puzzle.date,
        issue=live_puzzle.issue,
        editor=live_puzzle.editor,
        shape=live_puzzle.shape,
        year=live_puzzle.year,
        month=live_puzzle.month,
        books=live_puzzle.books,
        links=live_puzzle.links,
        files=live_puzzle.files,
        instructions=parsed_data.get("instructions"),
        clue_groups=clue_groups,
        grid=live_puzzle.grid,
        settings=live_puzzle.settings,
        unclued=live_puzzle.unclued,
        status="pending",
        extracted_at=datetime.now(tz=UTC),
    )
    staging_puzzle.save()
    logger.info("  🎉 Successfully staged puzzle: '%s' (%s)", live_puzzle.title, puzzle_id)
    return True

def get_unprocessed_puzzle_ids() -> list[str]:
    """Find live puzzles that have a PDF but no parsed clues, and aren't already staged."""
    db = firestore.Client(project=PROJECT)
    
    # Get all staging IDs currently pending/active to avoid duplicates
    staging_ids = {doc.id for doc in db.collection("puzzles_staging").stream()}
    
    # Query live puzzles
    puzzles = db.collection("puzzles").stream()
    unprocessed = []
    
    for p in puzzles:
        if p.id in staging_ids:
            continue
            
        data = p.to_dict() or {}
        pub = data.get("publication", "")
        if pub not in ("wsj", "atlantic"):
            continue
            
        clue_groups = data.get("clue_groups", [])
        
        # We need staging if clues are missing/empty
        has_clues = any(len(g.get("clues", [])) > 0 for g in clue_groups)
        if not has_clues:
            files = data.get("files", {})
            pdf_path = files.get("puzzle_pdf", {}).get("path") if isinstance(files, dict) else ""
            if pdf_path:
                unprocessed.append(p.id)
                
    return unprocessed

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest raw PDFs, parse clues, and save to Staging collection.")
    parser.add_argument("-e", "--env", choices=["dev", "prod"], default=None, help="The environment to target (dev or prod).")
    parser.add_argument("--puzzle-id", help="Ingest a specific puzzle ID")
    parser.add_argument("--all-unprocessed", action="store_true", help="Ingest all blank live puzzles that have PDFs")
    parser.add_argument("--limit", type=int, default=5, help="Max puzzles to stage in a batch")
    args = parser.parse_args()

    # Configure connection variables dynamically from env flag
    setup_environment(args.env)


    if args.puzzle_id:
        success = stage_single_puzzle(args.puzzle_id)
        if not success:
            sys.exit(1)
            
    elif args.all_unprocessed:
        logger.info("Searching for unprocessed puzzles with PDFs...")
        unprocessed_ids = get_unprocessed_puzzle_ids()
        logger.info("Found %d unprocessed puzzles", len(unprocessed_ids))
        
        to_process = unprocessed_ids[:args.limit]
        logger.info("Processing batch of %d puzzles", len(to_process))
        
        success_count = 0
        for pid in to_process:
            try:
                if stage_single_puzzle(pid):
                    success_count += 1
            except Exception as e:
                logger.error("Failed to process %s: %s", pid, e)
                
        logger.info("Batch ingestion complete: %d/%d successfully staged.", success_count, len(to_process))
        
    else:
        logger.error("Please specify --puzzle-id or --all-unprocessed")
        sys.exit(1)

if __name__ == "__main__":
    main()
