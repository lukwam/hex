resource "google_storage_bucket" "answers" {
  name          = "lukwam-hex-answers"
  project       = google_project.project.project_id
  location      = "us-east4"
  force_destroy = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "archive" {
  name          = "lukwam-hex-archive"
  project       = google_project.project.project_id
  location      = "us-east4"
  force_destroy = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "archive-images" {
  name          = "lukwam-hex-archive-images"
  project       = google_project.project.project_id
  location      = "us-east4"
  force_destroy = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "guide" {
  name          = "lukwam-hex-guide"
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

resource "google_storage_bucket" "wordpress" {
  name          = "lukwam-hex-wordpress"
  project       = google_project.project.project_id
  location      = "us-east4"
  force_destroy = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_iam_member" "archive-images-image-reader" {
  bucket = google_storage_bucket.archive-images.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.image-reader.email}"
}

resource "google_storage_bucket_iam_member" "images-image-reader" {
  bucket = google_storage_bucket.images.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.image-reader.email}"
}
