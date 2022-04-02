resource "google_eventarc_trigger" "image2png" {
    name            = "image2png"
    location        = var.region
    matching_criteria {
        attribute   = "type"
        value       = "google.cloud.storage.object.v1.finalized"
    }
    matching_criteria {
        attribute  = "bucket"
        value       = google_storage_bucket.puzzles.name
    }
    destination {
        cloud_run_service {
            service = "image2png"
            region  = var.region
        }
    }
}
