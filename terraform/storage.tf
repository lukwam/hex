resource "google_storage_bucket" "answers" {
  name                        = "lukwam-hex-answers${local.env_suffix}"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "archive" {
  name                        = "lukwam-hex-archive${local.env_suffix}"
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
  name                        = "lukwam-hex-archive-images${local.env_suffix}"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "guide" {
  name                        = "lukwam-hex-guide${local.env_suffix}"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "images" {
  name                        = "lukwam-hex-images${local.env_suffix}"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "puzzles" {
  name                        = "lukwam-hex-puzzles${local.env_suffix}"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "thumbnails" {
  name                        = "lukwam-hex-thumbnails${local.env_suffix}"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "wordpress" {
  name                        = "lukwam-hex-wordpress${local.env_suffix}"
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

resource "google_storage_bucket_iam_member" "images-admin-service" {
  bucket = google_storage_bucket.images.name
  role   = "roles/storage.objectViewer"
  member = module.project.service_accounts["admin-service"].member
}

resource "google_storage_bucket_iam_member" "images-api-service" {
  bucket = google_storage_bucket.images.name
  role   = "roles/storage.objectViewer"
  member = module.project.service_accounts["api-service"].member
}

resource "google_storage_bucket_iam_member" "thumbnails-image-reader" {
  bucket = google_storage_bucket.thumbnails.name
  role   = "roles/storage.objectViewer"
  member = module.project.service_accounts["image-reader"].member
}

# Consolidated assets bucket (new layout)
resource "google_storage_bucket" "assets" {
  name                        = "lukwam-hex-assets${local.env_suffix}"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_iam_member" "assets-admin-service" {
  bucket = google_storage_bucket.assets.name
  role   = "roles/storage.objectAdmin"
  member = module.project.service_accounts["admin-service"].member
}

resource "google_storage_bucket_iam_member" "assets-image-reader" {
  bucket = google_storage_bucket.assets.name
  role   = "roles/storage.objectViewer"
  member = module.project.service_accounts["image-reader"].member
}

# Cloud Build Logs Bucket
resource "google_storage_bucket" "cloudbuild-logs" {
  name                        = "${module.project.project_id}-cloudbuild-logs"
  project                     = module.project.project_id
  location                    = "us-east4"
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_iam_binding" "cloudbuild-logs-admin" {
  bucket = google_storage_bucket.cloudbuild-logs.name
  role   = "roles/storage.admin"
  members = [
    module.project.service_accounts["cloudbuild"].member,
  ]
}
