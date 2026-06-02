#!/usr/bin/env python3
"""Deterministic Non-AI PDF Text Extractor.

Extracts raw text from puzzle PDFs using various python libraries and layouts
without using any generative AI models.

Usage:
    poetry run python scripts/pdf_extractor.py --puzzle-id 026mb6qKAGfBqarFYgmx
"""

import argparse
import io
import json
import logging
import sys
from pathlib import Path
from typing import Any

import pdfplumber
import pypdf
from google.cloud import firestore, storage  # type: ignore[attr-defined]

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

import os
PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "lukwam-hex")
env = os.environ.get("HEX_ENV", "prod" if PROJECT == "lukwam-hex" else "dev")
BUCKET = "lukwam-hex-assets" if env == "prod" else f"lukwam-hex-assets-{env}"


class PDFExtractor:
    """Handles deterministic text extraction from PDFs using multiple approaches."""

    def __init__(self, pdf_bytes: bytes, puzzle_id: str):
        self.pdf_bytes = pdf_bytes
        self.puzzle_id = puzzle_id

    def extract_pypdf_basic(self) -> str:
        """Basic pypdf text extraction (plain text)."""
        logger.info("  Extracting with pypdf (basic)...")
        try:
            reader = pypdf.PdfReader(io.BytesIO(self.pdf_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n--- PAGE BREAK ---\n\n".join(pages)
        except Exception as e:
            logger.error("  pypdf basic failed: %s", e)
            return f"Error: {e}"

    def extract_pypdf_layout(self) -> str:
        """Layout-aware pypdf text extraction (preserves margins/spacing)."""
        logger.info("  Extracting with pypdf (layout)...")
        try:
            reader = pypdf.PdfReader(io.BytesIO(self.pdf_bytes))
            pages = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
            return "\n\n--- PAGE BREAK ---\n\n".join(pages)
        except Exception as e:
            logger.error("  pypdf layout failed: %s", e)
            return f"Error: {e}"

    def extract_pdfplumber_basic(self) -> str:
        """Basic pdfplumber text extraction (plain text)."""
        logger.info("  Extracting with pdfplumber (basic)...")
        try:
            with pdfplumber.open(io.BytesIO(self.pdf_bytes)) as pdf:
                pages = [page.extract_text(x_tolerance=1.5) or "" for page in pdf.pages]
            return "\n\n--- PAGE BREAK ---\n\n".join(pages)
        except Exception as e:
            logger.error("  pdfplumber basic failed: %s", e)
            return f"Error: {e}"

    def extract_pdfplumber_layout(self) -> str:
        """Spacing-aware pdfplumber text extraction (layout=True)."""
        logger.info("  Extracting with pdfplumber (layout)...")
        try:
            with pdfplumber.open(io.BytesIO(self.pdf_bytes)) as pdf:
                pages = [page.extract_text(layout=True, x_tolerance=1.5) or "" for page in pdf.pages]
            return "\n\n--- PAGE BREAK ---\n\n".join(pages)
        except Exception as e:
            logger.error("  pdfplumber layout failed: %s", e)
            return f"Error: {e}"

    def extract_pdfplumber_dynamic_columns(self, min_gutter_width: float = 12.0, margin_percent: float = 0.08) -> str:
        """Extract text by dynamically detecting vertical gutters (whitespace columns).

        Splits the page vertically along detected gutters and extracts text
        from left to right, column-by-column. Prevents clue column mixing.
        """
        logger.info("  Extracting with pdfplumber (dynamic columns)...")
        try:
            extracted_pages = []
            with pdfplumber.open(io.BytesIO(self.pdf_bytes)) as pdf:
                for idx, page in enumerate(pdf.pages):
                    width = float(page.width)
                    height = float(page.height)
                    
                    # Detect vertical column separators (gutters)
                    columns = self._detect_columns(page, min_gutter_width, margin_percent)
                    logger.info("    Page %d: Detected %d columns", idx + 1, len(columns))
                    
                    col_texts = []
                    for c_idx, bbox in enumerate(columns):
                        # Crop the page to the column bounding box, restricting vertically to exclude grid and header/footer
                        y0 = height * 0.38 if c_idx == 0 else height * 0.43
                        clue_bbox = (bbox[0], y0, bbox[2], height)
                        col_page = page.crop(clue_bbox)
                        col_text = col_page.extract_text(x_tolerance=1.5) or ""
                        if col_text.strip():
                            col_texts.append(f"--- COLUMN {c_idx+1} ---\n{col_text}")
                    
                    extracted_pages.append("\n\n".join(col_texts))
                    
            return "\n\n--- PAGE BREAK ---\n\n".join(extracted_pages)
        except Exception as e:
            logger.error("  pdfplumber dynamic columns failed: %s", e)
            return f"Error: {e}"

    def _detect_columns(self, page: pdfplumber.page.Page, min_gutter_width: float, margin_percent: float) -> list[tuple[float, float, float, float]]:
        """Identify vertical whitespace gutters to divide the page into column bounding boxes."""
        width = float(page.width)
        height = float(page.height)
        words = page.extract_words()
        
        if not words:
            return [(0.0, 0.0, width, height)]
            
        # Discretize into 1-point horizontal occupancy bins
        occupancy = [0] * int(width + 1)
        
        # Filter words to middle range (ignoring grid headers/footers)
        clue_words = [
            w for w in words
            if height * 0.22 < w["top"] < height * 0.88
        ]
        if not clue_words:
            clue_words = words
            
        for w in clue_words:
            x0 = max(0, int(w["x0"]))
            x1 = min(int(width), int(w["x1"]))
            for x in range(x0, x1 + 1):
                if 0 <= x < len(occupancy):
                    occupancy[x] += 1
                    
        # Try 3-column splitting in expected gutter zones
        g1_min_x = int(width * 0.25)
        g1_max_x = int(width * 0.38)
        g2_min_x = int(width * 0.58)
        g2_max_x = int(width * 0.72)
        
        g1_pos = min(range(g1_min_x, g1_max_x + 1), key=lambda x: occupancy[x])
        g2_pos = min(range(g2_min_x, g2_max_x + 1), key=lambda x: occupancy[x])
        
        # Check if 3-column layout is valid (low crossing word count)
        if occupancy[g1_pos] <= 5 and occupancy[g2_pos] <= 5:
            logger.info("  Detected 3-column layout split at x=%.1f and x=%.1f (occupancies: %d, %d)", 
                        g1_pos, g2_pos, occupancy[g1_pos], occupancy[g2_pos])
            return [
                (0.0, 0.0, float(g1_pos), height),
                (float(g1_pos), 0.0, float(g2_pos), height),
                (float(g2_pos), 0.0, width, height)
            ]
            
        # Try 2-column splitting in the middle expected zone
        mid_min_x = int(width * 0.44)
        mid_max_x = int(width * 0.56)
        mid_pos = min(range(mid_min_x, mid_max_x + 1), key=lambda x: occupancy[x])
        
        if occupancy[mid_pos] <= 5:
            logger.info("  Detected 2-column layout split at x=%.1f (occupancy: %d)", mid_pos, occupancy[mid_pos])
            return [
                (0.0, 0.0, float(mid_pos), height),
                (float(mid_pos), 0.0, width, height)
            ]
            
        # Fallback to single page column
        logger.info("  No valid gutters detected. Treating as single column.")
        return [(0.0, 0.0, width, height)]

def download_puzzle_pdf(puzzle_id: str) -> tuple[bytes, dict[str, Any]]:
    """Retrieve puzzle metadata from Firestore and download its PDF from GCS."""
    db = firestore.Client(project=PROJECT)
    doc = db.collection("puzzles").document(puzzle_id).get()
    if not doc.exists:
        raise ValueError(f"Puzzle ID {puzzle_id} not found in Firestore")
        
    data = doc.to_dict() or {}
    files = data.get("files", {})
    pdf_path = ""
    if isinstance(files, dict):
        pf = files.get("puzzle_pdf", {})
        if isinstance(pf, dict):
            pdf_path = pf.get("path", "")
            
    if not pdf_path:
        raise ValueError(f"Puzzle {puzzle_id} has no PDF file listed")
        
    logger.info("Downloading PDF from GCS: %s", pdf_path)
    storage_client = storage.Client(project=PROJECT)
    bucket = storage_client.bucket(BUCKET)
    blob = bucket.blob(pdf_path)
    return blob.download_as_bytes(), data

def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic Non-AI PDF Text Extractor")
    parser.add_argument("--puzzle-id", required=True, help="Firestore ID of the puzzle to extract")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/text_extractions"),
        help="Directory to save extracted outputs",
    )
    args = parser.parse_args()

    try:
        pdf_bytes, metadata = download_puzzle_pdf(args.puzzle_id)
    except Exception as e:
        logger.error("Failed to retrieve puzzle PDF: %s", e)
        sys.exit(1)

    extractor = PDFExtractor(pdf_bytes, args.puzzle_id)

    # Run all extraction methods
    results = {
        "puzzle_id": args.puzzle_id,
        "title": metadata.get("title", "Untitled"),
        "publication": metadata.get("publication", "unknown"),
        "extractions": {
            "pypdf_basic": extractor.extract_pypdf_basic(),
            "pypdf_layout": extractor.extract_pypdf_layout(),
            "pdfplumber_basic": extractor.extract_pdfplumber_basic(),
            "pdfplumber_layout": extractor.extract_pdfplumber_layout(),
            "pdfplumber_dynamic_columns": extractor.extract_pdfplumber_dynamic_columns(),
        }
    }

    # Save results
    puzzle_dir = args.output_dir / args.puzzle_id
    puzzle_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the consolidated JSON
    json_path = puzzle_dir / "all_extractions.json"
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    logger.info("Saved all extractions JSON to %s", json_path)

    # Save each method as a separate plain text file for easy inspection/diffing
    for method, text in results["extractions"].items():
        text_path = puzzle_dir / f"{method}.txt"
        text_path.write_text(text)
        logger.info("Saved %s text to %s", method, text_path)

    logger.info("Text extraction completed successfully!")

if __name__ == "__main__":
    main()
