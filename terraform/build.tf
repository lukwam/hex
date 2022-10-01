resource "google_cloudbuild_trigger" "build-app-image" {
  provider       = google-beta
  name           = "build-app-image"
  description    = "Build App Image"
  project        = google_project_service.services["cloudbuild.googleapis.com"].project
  included_files = [
    "app/**",
  ]
  github {
    name     = "hex"
    owner    = "lukwam"
    push {
      branch = "^${var.branch}$"
    }
  }
  substitutions = {
    _REGION = var.region
  }
  build {
    step {
      args = [
        "build",
        "-t",
        "gcr.io/lukwam-hex/github.com/lukwam/hex:latest",
        ".",
      ]
      dir        = "app"
      name       = "gcr.io/cloud-builders/docker"
    }
    images = [
      "gcr.io/lukwam-hex/github.com/lukwam/hex:latest"
    ]
  }
}

resource "google_cloudbuild_trigger" "deploy-app" {
  provider       = google-beta
  name           = "deploy-app"
  description    = "Deploy App"
  filename       = "app/cloudbuild.yaml"
  project        = google_project_service.services["cloudbuild.googleapis.com"].project
  included_files = [
    "app/**",
  ]
  github {
    name     = "hex"
    owner    = "lukwam"
    push {
      branch = "^${var.branch}$"
    }
  }
  substitutions = {
    _REGION = var.region
  }
}

resource "google_cloudbuild_trigger" "deploy-api" {
  provider       = google-beta
  name           = "deploy-api"
  description    = "Deploy api Cloud Run Service"
  filename       = "images/api/cloudbuild.yaml"
  project        = google_project_service.services["cloudbuild.googleapis.com"].project
  included_files = [
    "images/api/**",
  ]
  github {
    name     = "hex"
    owner    = "lukwam"
    push {
      branch = "^${var.branch}$"
    }
  }
  substitutions = {
    _REGION = var.region
  }
}

resource "google_cloudbuild_trigger" "deploy-image2png" {
  provider       = google-beta
  name           = "deploy-image2png"
  description    = "Deploy image2png Cloud Run Service"
  filename       = "images/image2png/cloudbuild.yaml"
  project        = google_project_service.services["cloudbuild.googleapis.com"].project
  included_files = [
    "images/image2png/**",
  ]
  github {
    name     = "hex"
    owner    = "lukwam"
    push {
      branch = "^${var.branch}$"
    }
  }
  substitutions = {
    _REGION = var.region
  }
}
