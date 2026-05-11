# Single Eventarc trigger for the consolidated assets bucket.
# Replaces the 3 old triggers (answers, archive, puzzles).
resource "google_eventarc_trigger" "assets-to-image-processor" {
  name     = "assets-to-image-processor"
  location = var.region
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.assets.name
  }
  destination {
    cloud_run_service {
      service = "image-processor"
      region  = var.region
    }
  }
  service_account = module.project.service_accounts["image-processor-service"].email
}
