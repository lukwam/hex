resource "google_eventarc_trigger" "answers-to-image2png" {
  name     = "answers-to-image2png"
  location = var.region
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.answers.name
  }
  destination {
    cloud_run_service {
      service = "image2png"
      region  = var.region
    }
  }
  transport {
    pubsub {
      topic = "projects/lukwam-hex/topics/eventarc-us-east4-answers-to-image2png-679"
    }
  }
  service_account = "${module.project.project_id}@appspot.gserviceaccount.com"
}

resource "google_eventarc_trigger" "archive-to-image2png" {
  name     = "archive-to-image2png"
  location = var.region
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.archive.name
  }
  destination {
    cloud_run_service {
      service = "image2png"
      region  = var.region
    }
  }
  service_account = "${module.project.project_id}@appspot.gserviceaccount.com"
}

resource "google_eventarc_trigger" "puzzles-to-image2png" {
  name     = "puzzles-to-image2png"
  location = var.region
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.puzzles.name
  }
  destination {
    cloud_run_service {
      service = "image2png"
      region  = var.region
    }
  }
  transport {
    pubsub {
      topic = "projects/lukwam-hex/topics/eventarc-us-east4-puzzles-to-image2png-592"
    }
  }
  service_account = "${module.project.project_id}@appspot.gserviceaccount.com"
}
