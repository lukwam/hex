resource "google_eventarc_trigger" "answers-to-image2png" {
    name            = "answers-to-image2png"
    location        = var.region
    matching_criteria {
        attribute   = "type"
        value       = "google.cloud.storage.object.v1.finalized"
    }
    matching_criteria {
        attribute  = "bucket"
        value       = google_storage_bucket.answers.name
    }
    destination {
        cloud_run_service {
            service = "image2png"
            region  = var.region
        }
    }
}

resource "google_eventarc_trigger" "puzzles-to-image2png" {
    name            = "puzzles-to-image2png"
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
