"""Audit GCS buckets against Firestore puzzle/book data.

Builds a manifest of expected files from the database, lists actual
files in each bucket, and reports differences.
"""

from __future__ import annotations

from google.cloud import storage
from google.cloud.firestore_v1 import Client as FirestoreClient

PROJECT = "lukwam-hex"

# Bucket definitions
BUCKETS = {
    "archive": "lukwam-hex-archive",  # PDFs + SVGs
    "archive_images": "lukwam-hex-archive-images",  # Full-size PNGs
    "thumbnails": "lukwam-hex-thumbnails",  # Thumbnail PNGs
    "images": "lukwam-hex-images",  # Gen1 flat images (puzzle/answer PNGs)
    "puzzles": "lukwam-hex-puzzles",  # Gen1 flat puzzles (PDFs/JPGs)
    "answers": "lukwam-hex-answers",  # Gen1 flat answers (PDFs/JPGs)
}


def get_puzzles(db: FirestoreClient) -> list[dict]:
    """Get all puzzles from Firestore."""
    puzzles = []
    for doc in db.collection("puzzles").stream():
        data = doc.to_dict()
        data["id"] = doc.id
        puzzles.append(data)
    return puzzles


def get_publications(db: FirestoreClient) -> dict[str, str]:
    """Get publication code mapping {code: name}."""
    pubs = {}
    for doc in db.collection("publications").stream():
        data = doc.to_dict()
        code = data.get("code", doc.id)
        pubs[code] = data.get("name", code)
    return pubs


def get_books(db: FirestoreClient) -> list[dict]:
    """Get all books from Firestore."""
    books = []
    for doc in db.collection("books").stream():
        data = doc.to_dict()
        data["id"] = doc.id
        books.append(data)
    return books


def list_bucket_files(client: storage.Client, bucket_name: str) -> set[str]:
    """List all object names in a bucket."""
    try:
        bucket = client.bucket(bucket_name)
        return {blob.name for blob in bucket.list_blobs()}
    except Exception as e:
        print(f"  ERROR listing {bucket_name}: {e}")
        return set()


def build_manifest(puzzles: list[dict], books: list[dict]) -> dict[str, set[str]]:
    """Build expected file manifest from database records."""
    manifest: dict[str, set[str]] = {
        "archive": set(),
        "archive_images": set(),
        "thumbnails": set(),
        "images": set(),  # Gen1 flat
        "puzzles": set(),  # Gen1 flat
        "answers": set(),  # Gen1 flat
        "book_covers": set(),  # lukwam-hex-images
    }

    for p in puzzles:
        pid = p["id"]
        pub = p.get("pub", p.get("publication", ""))

        if not pub:
            continue

        # Gen 2 (archive) — expected files per puzzle
        # Archive: PDFs + SVGs
        manifest["archive"].add(f"{pub}/{pid}_puzzle.pdf")
        manifest["archive"].add(f"{pub}/{pid}_solution.pdf")
        manifest["archive"].add(f"{pub}/{pid}_puzzle.svg")
        manifest["archive"].add(f"{pub}/{pid}_solution.svg")

        # Archive images: full-size PNGs
        manifest["archive_images"].add(f"{pub}/{pid}_puzzle.png")
        manifest["archive_images"].add(f"{pub}/{pid}_solution.png")

        # Thumbnails: smaller PNGs
        manifest["thumbnails"].add(f"{pub}/{pid}_puzzle.png")
        manifest["thumbnails"].add(f"{pub}/{pid}_solution.png")

        # Gen 1 (flat) — check files field if present
        files = p.get("files", {})
        if isinstance(files, dict):
            for field in (
                "puzzle_pdf",
                "puzzle_png",
                "puzzle_svg",
                "puzzle_thumbnail_png",
                "solution_pdf",
                "solution_png",
                "solution_svg",
                "solution_thumbnail_png",
            ):
                val = files.get(field)
                if val:
                    # Determine which Gen1 bucket
                    if "puzzle" in field and "thumbnail" not in field:
                        if field.endswith("_pdf"):
                            manifest["puzzles"].add(val)
                        elif field.endswith("_png"):
                            manifest["images"].add(val)
                    elif "solution" in field and "thumbnail" not in field:
                        if field.endswith("_pdf"):
                            manifest["answers"].add(val)
                        elif field.endswith("_png"):
                            manifest["images"].add(val)

    # Book covers
    for b in books:
        bid = b["id"]
        # Convention: {bookId}_cover.png
        cover = b.get("cover_image") or b.get("files", {}).get("cover")
        if cover:
            manifest["book_covers"].add(cover)
        else:
            manifest["book_covers"].add(f"{bid}_cover.png")

    return manifest


def compare(label: str, bucket_name: str, expected: set[str], actual: set[str]) -> dict:
    """Compare expected vs actual and return stats."""
    in_db_not_disk = expected - actual
    on_disk_not_db = actual - expected

    result = {
        "bucket": bucket_name,
        "expected": len(expected),
        "actual": len(actual),
        "missing_from_disk": len(in_db_not_disk),
        "orphaned_on_disk": len(on_disk_not_db),
        "matched": len(expected & actual),
    }

    print(f"\n{'=' * 60}")
    print(f"  {label}: {bucket_name}")
    print(f"{'=' * 60}")
    print(f"  Expected (from DB):  {result['expected']}")
    print(f"  Actual (on disk):    {result['actual']}")
    print(f"  ✅ Matched:          {result['matched']}")
    print(f"  ❌ Missing from disk: {result['missing_from_disk']}")
    print(f"  ⚠️  Orphaned on disk: {result['orphaned_on_disk']}")

    if in_db_not_disk and len(in_db_not_disk) <= 20:
        print("\n  Missing files (sample):")
        for f in sorted(in_db_not_disk)[:20]:
            print(f"    - {f}")

    if on_disk_not_db and len(on_disk_not_db) <= 20:
        print("\n  Orphaned files (sample):")
        for f in sorted(on_disk_not_db)[:20]:
            print(f"    + {f}")
    elif on_disk_not_db:
        print(f"\n  Orphaned files (first 20 of {len(on_disk_not_db)}):")
        for f in sorted(on_disk_not_db)[:20]:
            print(f"    + {f}")

    return result


def main():
    print("Hex GCS Bucket Audit")
    print("=" * 60)

    # Connect
    db = FirestoreClient(project=PROJECT)
    gcs = storage.Client(project=PROJECT)

    # Load data
    print("\nLoading Firestore data...")
    puzzles = get_puzzles(db)
    pubs = get_publications(db)
    books = get_books(db)
    print(f"  Puzzles: {len(puzzles)}")
    print(f"  Publications: {len(pubs)}")
    print(f"  Books: {len(books)}")

    # Check pub distribution
    pub_counts: dict[str, int] = {}
    no_pub = 0
    for p in puzzles:
        pub = p.get("pub", p.get("publication", ""))
        if pub:
            pub_counts[pub] = pub_counts.get(pub, 0) + 1
        else:
            no_pub += 1
    print("\n  Puzzles by publication:")
    for code, count in sorted(pub_counts.items(), key=lambda x: -x[1]):
        print(f"    {code}: {count}")
    if no_pub:
        print(f"    (no pub): {no_pub}")

    # Build manifest
    print("\nBuilding expected file manifest...")
    manifest = build_manifest(puzzles, books)
    for key, files in manifest.items():
        print(f"  {key}: {len(files)} expected files")

    # List actual bucket contents
    print("\nListing bucket contents...")
    actual: dict[str, set[str]] = {}
    for key, bucket_name in BUCKETS.items():
        print(f"  {bucket_name}...", end=" ", flush=True)
        actual[key] = list_bucket_files(gcs, bucket_name)
        print(f"{len(actual[key])} files")

    # Compare Gen 2 buckets
    results = []
    results.append(compare("Archive (PDFs+SVGs)", BUCKETS["archive"], manifest["archive"], actual["archive"]))
    results.append(
        compare(
            "Archive Images (PNGs)", BUCKETS["archive_images"], manifest["archive_images"], actual["archive_images"]
        )
    )
    results.append(compare("Thumbnails", BUCKETS["thumbnails"], manifest["thumbnails"], actual["thumbnails"]))

    # Compare Gen 1 buckets (only if manifest has entries)
    if manifest["puzzles"]:
        results.append(compare("Gen1 Puzzles", BUCKETS["puzzles"], manifest["puzzles"], actual["puzzles"]))
    else:
        print(f"\n  Gen1 puzzles: no files referenced in DB (bucket has {len(actual['puzzles'])} files)")

    if manifest["answers"]:
        results.append(compare("Gen1 Answers", BUCKETS["answers"], manifest["answers"], actual["answers"]))
    else:
        print(f"\n  Gen1 answers: no files referenced in DB (bucket has {len(actual['answers'])} files)")

    if manifest["images"]:
        results.append(compare("Gen1 Images", BUCKETS["images"], manifest["images"], actual["images"]))
    else:
        print(f"\n  Gen1 images: no files referenced in DB (bucket has {len(actual['images'])} files)")

    # Summary
    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")
    total_missing = sum(r["missing_from_disk"] for r in results)
    total_orphaned = sum(r["orphaned_on_disk"] for r in results)
    total_matched = sum(r["matched"] for r in results)
    print(f"  Total matched:        {total_matched}")
    print(f"  Total missing:        {total_missing}")
    print(f"  Total orphaned:       {total_orphaned}")


if __name__ == "__main__":
    main()
