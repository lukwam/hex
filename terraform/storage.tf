resource "google_storage_bucket" "answers" {
  name          = "lukwam-hex-answers"
  project       = google_project.project.project_id
  location      = "us-east4"
  force_destroy = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "images" {
  name          = "lukwam-hex-images"
  project       = google_project.project.project_id
  location      = "us-east4"
  force_destroy = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "puzzles" {
  name          = "lukwam-hex-puzzles"
  project       = google_project.project.project_id
  location      = "us-east4"
  force_destroy = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "thumbnails" {
  name          = "lukwam-hex-thumbnails"
  project       = google_project.project.project_id
  location      = "us-east4"
  force_destroy = false
  uniform_bucket_level_access = true
}
