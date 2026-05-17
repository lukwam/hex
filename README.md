# Hex

Management site and tools for the Cox & Rathvon puzzle archive.

## Architecture

- **`app/`** — Flask web app (App Engine, behind IAP)
- **`terraform/`** — Infrastructure as code (GCP resources)
- **`docs/`** — Project documentation

## Legacy Services (removed, to be rebuilt)

The following services existed in the pre-v2 codebase and were removed during
the rewrite. Their functionality should be rebuilt as needed.

### API (`images/api/` → `hexapi.lukwam.dev`)

Read-only REST API for puzzle data. Deployed on Cloud Run,
consumed by the (now-removed) GitHub Pages SPA. Broke in May 2023
when a Dependabot Flask bump removed `flask.json.JSONEncoder`.
A modern replacement should live in `services/api/` using FastAPI
and firedantic models. See [#42](https://github.com/lukwam/hex/issues/42).

### Image Converter (`images/image2png/`)

Cloud Run service triggered via Eventarc when files are uploaded to
the `answers`, `archive`, or `puzzles` GCS buckets. Converts PDFs
and images to PNG, generates thumbnails for archive files, and uploads
results to the `lukwam-hex-images` and `lukwam-hex-thumbnails` buckets.

### Puzzle File Creator (`images/create/`)

Web UI for creating `.puz` crossword puzzle files from form input.
Was never deployed (no Cloud Build trigger existed). Could be rebuilt
as a route in the main app or as a standalone tool.

### Drive-to-Storage Sync (`functions/drive_to_storage/`)

Local-only script (run manually, not deployed). Syncs puzzle PDFs and
SVGs from a Google Drive shared drive (`0ALCeSdEPSCR-Uk9PVA`) to the
`lukwam-hex-archive` GCS bucket. Matches files against Firestore puzzle
records by title and date, sets metadata on GCS objects.

### Thumbnail Generator (`functions/create_thumbs/`)

Local-only batch script. Iterates the `lukwam-hex-archive-images` bucket
and creates thumbnails in `lukwam-hex-thumbnails` for any missing images.
Largely superseded by `image2png` which generates thumbnails inline.

## Firestore Schema

See [#40](https://github.com/lukwam/hex/issues/40) for the firedantic
model specifications.

### books

- `id`: Examples include `ap`, `gdn`, `rha`, `rhg`, `sb`
- `title`: Title of the book
- `isbn_10`: ISBN-10 of the book
- `isbn_13`: ISBN-13 of the book
- `date`: Date the book was originally published
- `pages`: Number of pages in the book
- `amazon_url`: Amazon URL to purchase the book
- `cover_url`: URL of the cover of the book
- `images`: Dictionary of cached images associated with the book

### publications

- `id`: Examples include `wsj`, `atlantic`, etc.
- `name`: Examples include `Wall Street Journal`, `The Atlantic Puzzler`
- `url`: URL of the publication

### puzzles

- `title`: Title of the puzzle (not unique)
- `publication`: `id` from the `publications` collection
- `date`: Date the puzzle was published
- `issue`: Issue in which the puzzle was published
- `web_url`: URL of puzzle web site (if available online)
- `puzzle_url`: URL of the puzzle file (PDF, etc.)
- `answer_url`: URL of the answer file (PDF, etc.)
- `images`: Dictionary of cached images associated with the puzzle

### users

- `id`: The unique ID of the user
- `email`: The email of the user
- `handle`: The user's handle for social features
- `books_owned`: List of books the user owns.
- `favorites`: List of puzzles the user has favorited
- `puzzles_solved`: List of puzzles the user has solved.
- `is_admin`: True if the user is an admin
