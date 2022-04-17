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
        "pack",
        "build",
        "gcr.io/lukwam-hex/github.com/lukwam/hex:latest",
        "--builder",
        "gcr.io/buildpacks/builder",
      ]
      dir        = "app"
      name       = "gcr.io/k8s-skaffold/pack"
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
