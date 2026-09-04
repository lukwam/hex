#!/usr/bin/env python3
"""General-purpose, Dynamic Solution Ingestion Engine.

Takes a puzzle ID, fetches its staging clues/metadata from Firestore, downloads
the corresponding solution PNG from GCS, and uses Gemini Multimodal Vision to
automatically transcribe the grid, solutions, and cryptic annotations.

Usage:
    poetry run python scripts/transcribe_solution_general.py --env dev --puzzle-id 1XMjckv4tWwvMe2zTMWi
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from PIL import Image

from google import genai
from google.cloud import firestore, storage
from firedantic.configurations import configuration
from google.cloud.firestore_v1 import Client

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from services.shared.models import Puzzle, StagingPuzzle
from hexword import ClueGroup, Clue

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

def setup_environment(env: str) -> str:
    """Setup Firestore and environment config."""
    if env == "dev":
        project = "lukwam-hex-dev"
        bucket = "lukwam-hex-assets-dev"
    else:
        project = "lukwam-hex"
        bucket = "lukwam-hex-assets"

    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    os.environ["HEX_ENV"] = env
    os.environ["HEX_DB_NAME"] = "(default)"

    configuration.add(
        name="(default)",
        project=project,
        database="(default)",
        client=Client(project=project, database="(default)"),
    )
    return bucket

def download_solution_image(project: str, bucket_name: str, puzzle_id: str) -> str:
    """Download the solution PNG from GCS if it doesn't already exist locally."""
    local_path = f"scratch/{puzzle_id}_solution.png"
    if os.path.exists(local_path):
        logger.info("Found local solution image: %s", local_path)
        return local_path

    os.makedirs("scratch", exist_ok=True)
    client = storage.Client(project=project)
    bucket = client.bucket(bucket_name)

    # Atlantic and WSJ folders in GCS: puzzles/<pub>/<id>/<id>_solution.png
    # Let's search under both atlantic and wsj prefixes
    for pub in ["atlantic", "wsj"]:
        blob_name = f"puzzles/{pub}/{puzzle_id}/{puzzle_id}_solution.png"
        blob = bucket.blob(blob_name)
        if blob.exists():
            logger.info("Downloading solution from GCS: %s", blob_name)
            blob.download_to_filename(local_path)
            return local_path

    raise FileNotFoundError(f"Could not find solution image for puzzle {puzzle_id} in GCS.")

def verify_grid_consistency(rows_raw: list[str], cols_raw: list[str], width: int, height: int) -> bool:
    """Validate that grid rows and columns are symmetrical and have correct lengths."""
    logger.info("=== VERIFYING GRID CONSISTENCY (%dx%d) ===", width, height)
    rows = [r.replace("|", "") for r in rows_raw]
    cols = [c.replace("|", "") for c in cols_raw]
    
    has_errors = False
    
    # Check lengths
    for idx, r in enumerate(rows):
        if len(r) != width:
            logger.error("  Row %d length is %d instead of %d! Content: %s", idx+1, len(r), width, r)
            has_errors = True
    for idx, c in enumerate(cols):
        if len(c) != height:
            logger.error("  Col %d length is %d instead of %d! Content: %s", idx+1, len(c), height, c)
            has_errors = True
            
    # Check intersection symmetry
    for r_idx in range(min(height, len(rows))):
        for c_idx in range(min(width, len(cols))):
            r_char = rows[r_idx][c_idx] if c_idx < len(rows[r_idx]) else '?'
            c_char = cols[c_idx][r_idx] if r_idx < len(cols[c_idx]) else '?'
            if r_char != c_char:
                logger.error("  Grid mismatch at Row %d, Col %d: Row has '%s', Col has '%s'", 
                             r_idx+1, c_idx+1, r_char, c_char)
                has_errors = True
                
    if not has_errors:
        logger.info("  Grid is 100%% mathematically consistent and valid!")
    return not has_errors

def main():
    parser = argparse.ArgumentParser(description="Auto-transcribe cryptic puzzle solution using Gemini.")
    parser.add_argument("-e", "--env", choices=["dev", "prod"], default="dev", help="The environment to target.")
    parser.add_argument("--puzzle-id", required=True, help="Puzzle ID to transcribe solutions for.")
    args = parser.parse_args()

    # 1. Setup environment
    bucket_name = setup_environment(args.env)
    project = os.environ["GOOGLE_CLOUD_PROJECT"]

    # 2. Fetch Staging Puzzle from Firestore
    try:
        staging_puzzle = StagingPuzzle.get_by_id(args.puzzle_id)
        logger.info("Loaded Staging Puzzle: '%s' (%s)", staging_puzzle.title, args.puzzle_id)
    except Exception:
        logger.error("Staging puzzle %s not found in Firestore!", args.puzzle_id)
        sys.exit(1)

    # 3. Locate & Download solution image
    try:
        img_path = download_solution_image(project, bucket_name, args.puzzle_id)
        img = Image.open(img_path)
    except Exception as e:
        logger.error("Failed to acquire solution image: %s", e)
        sys.exit(1)

    # 4. Generate dynamic clue context
    clues_context = []
    for g in staging_puzzle.clue_groups:
        clues_context.append(f"Clue Group: {g.name}")
        for c in g.clues:
            clues_context.append(f"  Clue {c.name}: {c.clue_text}")
    clues_str = "\n".join(clues_context)

    # Determine dimensions
    shape = staging_puzzle.shape or "12x12"
    try:
        parts = shape.split("x")
        if len(parts) == 2:
            height = int(parts[0])
            width = int(parts[1])
        else:
            height = width = int(parts[0])
    except Exception:
        height = width = 12

    # 5. Formulate general prompt
    prompt = f"""
You are an expert crossword solver, variety cryptic crossword transcriber, and layout engineer.
The attached solution sheet image may contain the solutions of MULTIPLE different puzzles on the same page.
Your task is to locate and extract ONLY the completed grid, clues, answers, and annotations for the specific cryptic crossword puzzle titled "{staging_puzzle.title}" by Emily Cox & Henry Rathvon.
You MUST completely ignore all other puzzles, grids, and text columns on the page.

Your specific instructions are:
1. Locate the correct grid corresponding to "{staging_puzzle.title}". Since the shape is {shape}, the grid is exactly {height} rows and {width} columns. Extract the completed letters in each cell. Word boundaries (thick black bars/lines) must be represented by pipes '|'.
2. Identify which squares are highlighted in RED in the solution grid. You will output a style mask matching the exact grid cells, using 'r' for red squares and '.' for normal squares.
3. Match the printed solution answers and cryptic annotations/explanations for "{staging_puzzle.title}" to the original clues provided below.

Here are the original clues from the puzzle:
{clues_str}

Please look at the solution grid and the clue text lists extremely carefully. Output a JSON object strictly matching this schema:
{{
  "grid": {{
    "rows": [
      "{width} letters total, separated by pipes '|' at word dividers, for Row 1",
      "{width} letters total, separated by pipes '|' at word dividers, for Row 2",
      ...
    ],
    "columns": [
      "{height} letters total, separated by pipes '|' at word dividers, for Column 1",
      "{height} letters total, separated by pipes '|' at word dividers, for Column 2",
      ...
    ],
    "style": [
      "{width} characters total: use 'r' for red highlighted cells and '.' for normal cells, for Row 1",
      "{width} characters total: use 'r' for red highlighted cells and '.' for normal cells, for Row 2",
      ...
    ]
  }},
  "clue_groups": [
    {{
      "name": "Clue Group Name (must match exactly the original group names, e.g. 'Across' or 'Down')",
      "clues": [
        {{
          "name": "Clue name/number (must match the original clue name exactly, e.g. '1')",
          "answers": [
            {{
              "answer": "UPPERCASE_ANSWER_WORD",
              "annotation": "Cryptic explanation/annotation (e.g., 'BELL(I)E\\'S' or 'anag.')"
            }}
          ]
        }}
      ]
    }}
  ]
}}

Double-check:
- Every row must contain exactly {width} letters when pipes are removed.
- Every column must contain exactly {height} letters when pipes are removed.
- The style grid must contain exactly {height} rows of {width} characters.
- The letter at row R, column C must match exactly with the letter at column C, row R.
- Do not skip any clue. Return all clue answers and annotations.
"""

    # 6. Call Gemini Flash
    logger.info("Calling Gemini Flash with solution image and dynamic clues context...")
    try:
        client = genai.Client(vertexai=True, project=project, location="us-central1")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[img, prompt],
            config=genai.types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            )
        )
        data = json.loads(response.text)
        
        # Cache local transcript for safety/review
        cache_path = f"scratch/{args.puzzle_id}_transcription.json"
        with open(cache_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Saved local transcription cache: %s", cache_path)

    except Exception as e:
        logger.error("Gemini solution transcription failed: %s", e)
        sys.exit(1)

    # 7. Symmetrical Grid Verification
    valid_grid = verify_grid_consistency(data["grid"]["rows"], data["grid"]["columns"], width, height)

    # 8. Merge Solutions back into Staging Firestore Document
    logger.info("Merging transcribed answers and grid back into staging document...")
    from hexword import Grid, GridStyle
    
    # Initialize styles map
    styles_map = {"r": GridStyle(background_color="red")}
    
    staging_puzzle.grid = Grid(
        rows=data["grid"]["rows"],
        columns=data["grid"]["columns"],
        style=data["grid"].get("style", []),
        solution_style=data["grid"].get("style", []),
        styles=styles_map,
        solution_rows=data["grid"]["rows"],
        solution_columns=data["grid"]["columns"]
    )

    # Map groups from response to the staging document
    response_groups = {}
    for g in data.get("clue_groups", []):
        g_name = str(g.get("name") or "").strip().lower()
        response_groups[g_name] = g
    
    for group in staging_puzzle.clue_groups:
        g_name_lower = group.name.lower()
        resp_g = response_groups.get(g_name_lower)
        if not resp_g:
            # Fallback: check substring match (e.g. "across clues" containing "across")
            for k, v in response_groups.items():
                if g_name_lower in k or k in g_name_lower:
                    resp_g = v
                    break
                    
        if not resp_g:
            logger.warning("  Group '%s' was not returned by the transcriber. Skipping.", group.name)
            continue
            
        resp_clues = {}
        for c in resp_g.get("clues", []):
            c_name = str(c.get("name") or "").strip().rstrip(".").lower()
            resp_clues[c_name] = c
        
        for clue in group.clues:
            clue_name_clean = str(clue.name).strip().rstrip(".").lower()
            resp_c = resp_clues.get(clue_name_clean)
            if not resp_c:
                logger.warning("    Clue '%s' was not returned in group '%s'. Skipping.", clue.name, group.name)
                continue
                
            answers_list = []
            annotations_list = []
            
            for ans in resp_c.get("answers", []):
                ans_word = str(ans.get("answer", "")).strip().upper()
                ann_text = str(ans.get("annotation", "")).strip()
                if ans_word:
                    answers_list.append(ans_word)
                    annotations_list.append(ann_text)
                    
            clue.answers = answers_list
            clue.annotations = annotations_list
            logger.info("    Mapped Clue %s: answers=%s, annotations=%s", clue.name, clue.answers, clue.annotations)

    # Save staging document
    staging_puzzle.save()
    logger.info("🎉 Successfully transcribed and updated Staging Puzzle '%s' in Firestore!", staging_puzzle.title)

    if not valid_grid:
        logger.warning("⚠️ Warning: The transcribed grid had mathematical inconsistencies. Please review in the Staging editor.")

if __name__ == "__main__":
    main()
