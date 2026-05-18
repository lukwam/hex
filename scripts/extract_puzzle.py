#!/usr/bin/env python3
"""Extract puzzle data from PDFs/images using Gemini Flash.

Usage:
    # Extract one puzzle and dump JSON
    poetry run python scripts/extract_puzzle.py --puzzle-id 026mb6qKAGfBqarFYgmx

    # Extract and compare against existing data
    poetry run python scripts/extract_puzzle.py --puzzle-id 026mb6qKAGfBqarFYgmx --compare

    # Extract first N test puzzles (those with existing grid data)
    poetry run python scripts/extract_puzzle.py --test --limit 3
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import sys
from pathlib import Path
from typing import Any

import pdfplumber
import pypdf
from google import genai
from google.cloud import firestore, storage  # type: ignore[attr-defined]

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

PROJECT = "lukwam-hex"
BUCKET = "lukwam-hex-assets"
MODEL = "gemini-2.5-flash-preview-05-20"

# ---------------------------------------------------------------------------
# PDF text extraction (deterministic, no AI)
# ---------------------------------------------------------------------------


def extract_text_pypdf(pdf_bytes: bytes) -> str:
    """Extract text using pypdf (fast, basic)."""
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n--- PAGE BREAK ---\n\n".join(pages)


def extract_text_pdfplumber(pdf_bytes: bytes) -> str:
    """Extract text using pdfplumber (layout-aware)."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n\n--- PAGE BREAK ---\n\n".join(pages)


# ---------------------------------------------------------------------------
# Gemini agent prompts
# ---------------------------------------------------------------------------

GRID_ANALYSIS_PROMPT = """\
You are an expert puzzle grid analyst. Analyze this cryptic crossword puzzle image.

Determine:
1. **Shape**: Is the grid square, rectangular, circular, diamond, hexagonal, or some other shape?
2. **Dimensions**: How many rows and columns (for rectangular grids)?
3. **Cell types**: Identify which cells are:
   - Empty (white, available for letters)
   - Blocked (solid black/dark)
   - Shaded (light color, usually meaningful)
   - Circled (cell has a circle drawn around it)
   - Numbered (has a small number in the corner)
   - Barred (has thick lines on certain edges instead of blocked cells)
4. **Numbers**: List all cell numbers and their positions (row, column), 0-indexed.
5. **Bars**: If this is a barred grid (no black squares, uses thick lines), describe the bar positions.

Return your analysis as JSON with this structure:
{
  "shape": "square|rectangle|circle|diamond|hexagonal|other",
  "rows": <number>,
  "columns": <number>,
  "is_barred": true/false,
  "numbered_cells": [{"number": 1, "row": 0, "col": 0}, ...],
  "blocked_cells": [{"row": 0, "col": 5}, ...],
  "shaded_cells": [{"row": 0, "col": 3, "color": "lightgreen"}, ...],
  "circled_cells": [{"row": 0, "col": 3}, ...],
  "bars": [{"row": 0, "col": 0, "side": "right|bottom"}, ...],
  "notes": "Any other observations about the grid structure"
}
"""

CLUE_PARSING_PROMPT = """\
You are an expert cryptic crossword clue parser. Parse the following text extracted \
from a cryptic crossword puzzle PDF.

Extract:
1. **Instructions**: Any theme description or special instructions at the top \
(before the clues). This is often a paragraph explaining how the puzzle works.
2. **Clue groups**: Identify each group of clues (usually "ACROSS" and "DOWN", \
but could be "CLUES", lettered groups like "A" and "B", or other headings).
3. **Individual clues**: For each clue, extract:
   - **name**: The clue number or letter (e.g., "1", "5", "A")
   - **clue_text**: The full clue text
   - **enumeration**: The length indicator in parentheses, e.g., "(4)", "(3,5)", "(4-2)"
   - **starred**: Whether the clue is marked with an asterisk/star

Important rules:
- The enumeration is usually at the END of the clue in parentheses like (4) or (3,5)
- Some puzzles have "two-part" clue numbers like "1, 5" meaning the answer spans two entries
- Do NOT include the enumeration in the clue_text — separate them
- Cryptic crossword clues are a single sentence; don't split them

Return your analysis as JSON:
{
  "instructions": "theme text or null",
  "clue_groups": [
    {
      "name": "Across",
      "clues": [
        {
          "name": "1",
          "clue_text": "Sort of lily branch holding up halfway",
          "enumeration": "(4)",
          "starred": false
        }
      ]
    }
  ]
}

Here is the extracted text:

"""

SOLUTION_PROMPT = """\
You are an expert puzzle solution reader. Analyze this cryptic crossword SOLUTION image.

The grid shows the filled-in answers. Extract:
1. Every letter in each cell, reading left-to-right, top-to-bottom.
2. For blocked/empty cells, use a dot "."

Return as JSON:
{
  "rows": <number>,
  "columns": <number>,
  "solution_grid": [
    "ARUM.CARET",
    "P.SEALEVEL",
    ...
  ],
  "notes": "any observations"
}
"""

# ---------------------------------------------------------------------------
# GCS helpers
# ---------------------------------------------------------------------------


def download_blob(bucket_name: str, blob_path: str) -> bytes:
    """Download a blob from GCS and return its bytes."""
    client = storage.Client(project=PROJECT)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    return blob.download_as_bytes()  # type: ignore[no-any-return]


def resolve_and_download(path: str) -> bytes:
    """Resolve a file path (gs:// URI or relative) and download it."""
    if path.startswith("gs://"):
        # Parse gs://bucket-name/object/path
        parts = path[5:].split("/", 1)
        bucket_name = parts[0]
        blob_path = parts[1] if len(parts) > 1 else ""
        return download_blob(bucket_name, blob_path)

    # Relative path — use the consolidated assets bucket
    return download_blob(BUCKET, path)


# ---------------------------------------------------------------------------
# Gemini calls
# ---------------------------------------------------------------------------


def call_gemini_text(prompt: str) -> str:
    """Call Gemini with a text-only prompt."""
    client = genai.Client(
        vertexai=True,
        project=PROJECT,
        location="us-east4",
    )
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    return response.text or ""


def call_gemini_vision(prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
    """Call Gemini with an image + text prompt."""
    client = genai.Client(
        vertexai=True,
        project=PROJECT,
        location="us-east4",
    )
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],  # type: ignore[arg-type]
        config=genai.types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    return response.text or ""


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def extract_puzzle(puzzle_id: str, puzzle_data: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    """Run the full extraction pipeline on a single puzzle."""
    pub = puzzle_data.get("publication", "unknown")
    title = puzzle_data.get("title", "Untitled")
    files = puzzle_data.get("files", {})
    logger.info("Extracting: %s [%s] %s", puzzle_id, pub, title)

    result = {
        "puzzle_id": puzzle_id,
        "publication": pub,
        "title": title,
        "agents": {},
    }

    # --- Step 1: Get the puzzle PDF text ---
    pdf_path = ""
    if isinstance(files, dict):
        pf = files.get("puzzle_pdf", {})
        if isinstance(pf, dict):
            pdf_path = pf.get("path", "")

    if pdf_path:
        logger.info("  Downloading puzzle PDF: %s", pdf_path)
        pdf_bytes = download_blob(BUCKET, pdf_path)

        # Extract text both ways
        text_pypdf = extract_text_pypdf(pdf_bytes)
        text_pdfplumber = extract_text_pdfplumber(pdf_bytes)

        result["text_pypdf"] = text_pypdf
        result["text_pdfplumber"] = text_pdfplumber

        # Use pdfplumber text (better layout) for clue parsing
        logger.info("  Calling Gemini for clue/instruction extraction...")
        try:
            clue_json = call_gemini_text(CLUE_PARSING_PROMPT + text_pdfplumber)
            result["agents"]["clues"] = json.loads(clue_json)
        except Exception as e:
            logger.warning("  Clue extraction failed: %s", e)
            result["agents"]["clues"] = {"error": str(e)}
    else:
        logger.warning("  No puzzle PDF available")

    # --- Step 2: Analyze the puzzle grid image ---
    png_path = ""
    if isinstance(files, dict):
        pf = files.get("puzzle_png", {})
        if isinstance(pf, dict):
            png_path = pf.get("path", "")

    if png_path:
        logger.info("  Downloading puzzle PNG: %s", png_path)
        png_bytes = download_blob(BUCKET, png_path)

        logger.info("  Calling Gemini for grid analysis...")
        try:
            grid_json = call_gemini_vision(GRID_ANALYSIS_PROMPT, png_bytes)
            result["agents"]["grid"] = json.loads(grid_json)
        except Exception as e:
            logger.warning("  Grid analysis failed: %s", e)
            result["agents"]["grid"] = {"error": str(e)}
    else:
        logger.warning("  No puzzle PNG available")

    # --- Step 3: Analyze the solution image ---
    sol_path = ""
    if isinstance(files, dict):
        sf = files.get("solution_png", {})
        if isinstance(sf, dict):
            sol_path = sf.get("path", "")

    if sol_path:
        logger.info("  Downloading solution PNG: %s", sol_path)
        sol_bytes = download_blob(BUCKET, sol_path)

        logger.info("  Calling Gemini for solution extraction...")
        try:
            sol_json = call_gemini_vision(SOLUTION_PROMPT, sol_bytes)
            result["agents"]["solution"] = json.loads(sol_json)
        except Exception as e:
            logger.warning("  Solution extraction failed: %s", e)
            result["agents"]["solution"] = {"error": str(e)}
    else:
        logger.info("  No solution PNG available (skipping)")

    # --- Write output ---
    out_file = output_dir / f"{puzzle_id}.json"
    out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    logger.info("  Output: %s", out_file)

    return result


def compare_with_existing(puzzle_id: str, extracted: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    """Compare extracted data against existing Firestore data."""
    diffs = {}

    # Compare instructions
    ext_instr = (extracted.get("agents", {}).get("clues", {}).get("instructions") or "").strip()
    ex_instr = (existing.get("instructions") or "").strip()
    if ext_instr and ex_instr:
        diffs["instructions_match"] = ext_instr == ex_instr
        if not diffs["instructions_match"]:
            diffs["instructions_extracted"] = ext_instr[:200]
            diffs["instructions_existing"] = ex_instr[:200]

    # Compare grid dimensions
    ext_grid = extracted.get("agents", {}).get("grid", {})
    ex_grid = existing.get("grid", {})
    if ext_grid and ex_grid.get("rows"):
        ext_dims = (ext_grid.get("rows", 0), ext_grid.get("columns", 0))
        ex_dims = (len(ex_grid.get("rows", [])), len(ex_grid.get("rows", [""])[0]) if ex_grid.get("rows") else 0)
        diffs["grid_dims_extracted"] = ext_dims
        diffs["grid_dims_existing"] = ex_dims
        diffs["grid_dims_match"] = ext_dims == ex_dims

    # Compare clue counts
    ext_groups = extracted.get("agents", {}).get("clues", {}).get("clue_groups", [])
    ex_groups = existing.get("clue_groups", [])
    if ext_groups and ex_groups:
        ext_counts = {g.get("name", ""): len(g.get("clues", [])) for g in ext_groups}
        ex_counts = {g.get("name", ""): len(g.get("clues", [])) for g in ex_groups}
        diffs["clue_counts_extracted"] = ext_counts
        diffs["clue_counts_existing"] = ex_counts
        diffs["clue_counts_match"] = ext_counts == ex_counts

    return diffs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run puzzle extraction."""
    parser = argparse.ArgumentParser(description="Extract puzzle data using Gemini")
    parser.add_argument("--puzzle-id", help="Extract a specific puzzle by ID")
    parser.add_argument("--test", action="store_true", help="Run on test set (puzzles with existing data)")
    parser.add_argument("--limit", type=int, default=3, help="Max puzzles to process in test mode")
    parser.add_argument("--compare", action="store_true", help="Compare extraction against existing data")
    parser.add_argument(
        "--publication",
        choices=["wsj", "atlantic"],
        help="Filter by publication",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/extractions"),
        help="Output directory for JSON dumps",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    db = firestore.Client(project=PROJECT)

    if args.puzzle_id:
        # Single puzzle
        doc = db.collection("puzzles").document(args.puzzle_id).get()
        if not doc.exists:  # type: ignore[union-attr]
            logger.error("Puzzle %s not found", args.puzzle_id)
            sys.exit(1)
        data = doc.to_dict()  # type: ignore[union-attr]
        if data is None:
            logger.error("Puzzle %s has no data", args.puzzle_id)
            sys.exit(1)
        result = extract_puzzle(args.puzzle_id, data, args.output_dir)

        if args.compare:
            diffs = compare_with_existing(args.puzzle_id, result, data)
            logger.info("Comparison: %s", json.dumps(diffs, indent=2))

    elif args.test:
        # Run on test set
        logger.info("Finding test puzzles (with existing grid data)...")
        all_puzzles = list(db.collection("puzzles").stream())
        test_set = []
        for p in all_puzzles:
            d = p.to_dict()
            if d is None:
                continue
            pub = d.get("publication", "")
            if pub not in ("wsj", "atlantic"):
                continue
            if args.publication and pub != args.publication:
                continue
            if not d.get("grid", {}).get("rows"):
                continue
            files = d.get("files", {})
            pdf = files.get("puzzle_pdf", {})
            if isinstance(pdf, dict) and pdf.get("path"):
                test_set.append((p.id, d))

        logger.info("Found %d test puzzles, processing %d", len(test_set), min(args.limit, len(test_set)))

        for puzzle_id, data in test_set[: args.limit]:
            result = extract_puzzle(puzzle_id, data, args.output_dir)
            if args.compare:
                diffs = compare_with_existing(puzzle_id, result, data)
                logger.info("Comparison: %s", json.dumps(diffs, indent=2))
            logger.info("")

    else:
        logger.error("Specify --puzzle-id or --test")
        sys.exit(1)


if __name__ == "__main__":
    main()
