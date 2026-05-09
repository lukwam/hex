resource "google_firestore_index" "puzzles-by-pub-and-date" {
  project = var.project_id

  collection = "puzzles"

  fields {
    field_path = "pub"
    order      = "ASCENDING"
  }

  fields {
    field_path = "date"
    order      = "ASCENDING"
  }

}

resource "google_firestore_index" "puzzles-by-books-and-date" {
  project = var.project_id

  collection = "puzzles"

  fields {
    field_path   = "books"
    array_config = "CONTAINS"
  }

  fields {
    field_path = "date"
    order      = "ASCENDING"
  }

}

resource "google_firestore_index" "puzzles-by-books-and-pub-and-date" {
  project = var.project_id

  collection = "puzzles"

  fields {
    field_path   = "books"
    array_config = "CONTAINS"
  }

  fields {
    field_path = "pub"
    order      = "ASCENDING"
  }

  fields {
    field_path = "date"
    order      = "ASCENDING"
  }

}

# Cursor pagination: puzzles sorted by date descending (forward page).
# Required by cursor_paginate(Puzzle, order_by=[("date", "DESCENDING")]).
resource "google_firestore_index" "puzzles-by-date-desc-name-asc" {
  project = var.project_id

  collection = "puzzles"

  fields {
    field_path = "date"
    order      = "DESCENDING"
  }

  fields {
    field_path = "__name__"
    order      = "ASCENDING"
  }

}

# Cursor pagination: puzzles sorted by date descending (reverse/prev page).
# cursor_paginate reverses direction for "prev" queries.
resource "google_firestore_index" "puzzles-by-date-asc-name-desc" {
  project = var.project_id

  collection = "puzzles"

  fields {
    field_path = "date"
    order      = "ASCENDING"
  }

  fields {
    field_path = "__name__"
    order      = "DESCENDING"
  }

}
