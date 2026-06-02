#!/usr/bin/env python3
"""Clue Structure & Alignment Parser (Tool 2 & 3).

Takes the raw spacing-preserved text blob from the PDF, splits it
into distinct columns dynamically, and uses Gemini to structure it into
clues, instructions, and metadata.

Usage:
    poetry run python scripts/parse_clues.py --puzzle-id 026mb6qKAGfBqarFYgmx
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from google import genai
from google.cloud import firestore  # type: ignore[attr-defined]

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

PROJECT = "lukwam-hex"
MODEL = "gemini-2.5-flash"
LOCATION = "us-central1"

CLUE_STRUCTURING_PROMPT = """\
You are an expert cryptic crossword clue parser. Below is a cleanly separated, \
sequential text block extracted from a crossword puzzle PDF.

Parse this text and extract:
1. **Instructions**: The introductory theme explanation or special rules at the top \
(before the clues begin). This is usually a paragraph explaining how answers are altered \
or what the shaded squares spell.
2. **Clue Groups**: Identify groups of clues (typically "Across" and "Down", but could \
be lettered groups like "A" and "B" or other headings).
3. **Clues**: For each individual clue, extract:
   - **name**: The clue number or letter identifier (e.g., "1", "26", "A")
   - **clue_text**: The clue text. Do NOT include the number or enumeration here.
   - **enumeration**: The length indicator at the end in parentheses, e.g., "(4)", "(3,5)", "(4-2)"
   - **starred**: A boolean (true/false) indicating if the clue has an asterisk/star prepended.

Important Rules:
- The enumeration is always at the end in parentheses, e.g., (4). Keep it separate from the clue text.
- Do not lose or truncate any clue. Every clue from the text MUST be parsed.
- Cryptic crossword clues are single semantic sentences. Do not split or group them incorrectly.

Return your parsed result strictly as JSON matching this schema:
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

Here is the clean, column-separated puzzle text:

"""

def split_text_columns(text: str, min_gutter_chars: int = 5, margin_percent: float = 0.1) -> list[str]:
    """Identify vertical whitespace gutters in the layout text and split it into columns."""
    lines = text.splitlines()
    if not lines:
        return []

    max_len = max(len(line) for line in lines)
    # Track character occupancy at each column index
    occupancy = [False] * max_len
    
    # We only analyze lines below the grid and above the footer
    # Typically, the grid is in the first 25% of lines, and title/footer are single lines.
    # To be safe, we use lines from 20% to 90%
    start_line = int(len(lines) * 0.20)
    end_line = int(len(lines) * 0.90)
    
    clue_lines = lines[start_line:end_line] if len(lines) > 5 else lines
    
    for line in clue_lines:
        for idx, char in enumerate(line):
            if char != ' ':
                if idx < len(occupancy):
                    occupancy[idx] = True

    # Find channels of spaces
    gutters = []
    in_gutter = False
    start_x = 0
    for x in range(len(occupancy)):
        if not occupancy[x]:
            if not in_gutter:
                in_gutter = True
                start_x = x
        else:
            if in_gutter:
                in_gutter = False
                end_x = x - 1
                gutters.append((start_x, end_x))
    if in_gutter:
        gutters.append((start_x, len(occupancy) - 1))

    # Filter gutters: must be wide enough and located away from the side margins
    left_margin = max_len * margin_percent
    right_margin = max_len * (1 - margin_percent)
    
    valid_gutters = []
    for g_start, g_end in gutters:
        g_width = g_end - g_start + 1
        if g_width >= min_gutter_chars:
            g_center = (g_start + g_end) / 2
            if left_margin <= g_center <= right_margin:
                valid_gutters.append((g_start, g_end))

    # Sort gutters left-to-right
    valid_gutters.sort(key=lambda g: g[0])
    
    # If no gutters found, return text as a single column
    if not valid_gutters:
        logger.info("  No vertical gutters detected in text. Treating as 1 column.")
        return [text]

    logger.info("  Detected %d vertical whitespace gutters in text. Splitting into %d columns.", len(valid_gutters), len(valid_gutters) + 1)

    # Define column ranges: (start_idx, end_idx)
    col_ranges = []
    curr_x = 0
    for g_start, g_end in valid_gutters:
        col_ranges.append((curr_x, g_start))
        curr_x = g_end + 1
    col_ranges.append((curr_x, max_len))

    # Extract text for each column
    columns = [[] for _ in range(len(col_ranges))]
    for line in lines:
        for c_idx, (start, end) in enumerate(col_ranges):
            col_text = line[start:end].strip()
            if col_text:
                # Add clue-like lines
                columns[c_idx].append(col_text)

    return ["\n".join(col) for col in columns]

def main() -> None:
    parser = argparse.ArgumentParser(description="Clue Structure & Alignment Parser")
    parser.add_argument("--puzzle-id", required=True, help="Firestore ID of the puzzle to parse")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("output/text_extractions"),
        help="Directory containing raw text extractions",
    )
    args = parser.parse_args()

    puzzle_dir = args.input_dir / args.puzzle_id
    layout_file = puzzle_dir / "pdfplumber_dynamic_columns.txt"
    
    if not layout_file.exists():
        logger.error("Dynamic columns text file not found at %s. Please run pdf_extractor.py first.", layout_file)
        sys.exit(1)

    clean_reconstructed_text = layout_file.read_text()
    logger.info("Loaded pre-split dynamic column text from %s", layout_file)

    # Step 2: Use Gemini to parse clues and metadata from the clean text
    logger.info("Calling Gemini Flash to structure clues and metadata...")
    client = genai.Client(
        vertexai=True,
        project=PROJECT,
        location=LOCATION,
    )
    
    response = client.models.generate_content(
        model=MODEL,
        contents=[CLUE_STRUCTURING_PROMPT + clean_reconstructed_text],
        config=genai.types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    
    parsed_json = response.text or ""
    
    # Save parsed clues JSON
    output_path = puzzle_dir / "parsed_clues.json"
    output_path.write_text(parsed_json)
    logger.info("Saved structured parsed clues JSON to %s", output_path)
    
    # Print summary
    try:
        data = json.loads(parsed_json)
        logger.info("\n=== Parse Summary ===")
        logger.info("Instructions: %s", data.get("instructions"))
        for g in data.get("clue_groups", []):
            logger.info("Group '%s': %d clues extracted", g.get("name"), len(g.get("clues", [])))
    except Exception as e:
        logger.warning("Failed to print summary: %s", e)

if __name__ == "__main__":
    main()
