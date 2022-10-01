resource "google_firestore_index" "puzzles-by-pub-and-date" {
  project = var.project_id

  collection = "puzzles"

  fields {
    field_path   = "pub"
    order        = "ASCENDING"
  }

  fields {
    field_path   = "date"
    order        = "ASCENDING"
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
    field_path   = "date"
    order        = "ASCENDING"
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
    field_path   = "pub"
    order        = "ASCENDING"
  }

  fields {
    field_path   = "date"
    order        = "ASCENDING"
  }

}
