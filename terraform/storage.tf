resource "google_storage_bucket" "answers" {
  name                        = "lukwam-hex-answers"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "archive" {
  name                        = "lukwam-hex-archive"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
  cors {
    origin          = ["*"]
    method          = ["GET"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}

resource "google_storage_bucket" "archive-images" {
  name                        = "lukwam-hex-archive-images"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "guide" {
  name                        = "lukwam-hex-guide"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "images" {
  name                        = "lukwam-hex-images"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "puzzles" {
  name                        = "lukwam-hex-puzzles"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "thumbnails" {
  name                        = "lukwam-hex-thumbnails"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "wordpress" {
  name                        = "lukwam-hex-wordpress"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_iam_member" "archive-image-reader" {
  bucket = google_storage_bucket.archive.name
  role   = "roles/storage.objectViewer"
  member = module.project.service_accounts["image-reader"].member
}

resource "google_storage_bucket_iam_member" "archive-images-image-reader" {
  bucket = google_storage_bucket.archive-images.name
  role   = "roles/storage.objectViewer"
  member = module.project.service_accounts["image-reader"].member
}

resource "google_storage_bucket_iam_member" "images-image-reader" {
  bucket = google_storage_bucket.images.name
  role   = "roles/storage.objectViewer"
  member = module.project.service_accounts["image-reader"].member
}

resource "google_storage_bucket_iam_member" "thumbnails-image-reader" {
  bucket = google_storage_bucket.thumbnails.name
  role   = "roles/storage.objectViewer"
  member = module.project.service_accounts["image-reader"].member
}
