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
    service_account = "${google_project.project.project_id}@appspot.gserviceaccount.com"
}

resource "google_eventarc_trigger" "archive-to-image2png" {
    name            = "archive-to-image2png"
    location        = var.region
    matching_criteria {
        attribute   = "type"
        value       = "google.cloud.storage.object.v1.finalized"
    }
    matching_criteria {
        attribute   = "bucket"
        value       = google_storage_bucket.archive.name
    }
    destination {
        cloud_run_service {
            service = "image2png"
            region  = var.region
        }
    }
    service_account = "${google_project.project.project_id}@appspot.gserviceaccount.com"
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
    service_account = "${google_project.project.project_id}@appspot.gserviceaccount.com"
}
