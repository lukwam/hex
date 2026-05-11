module "cloudbuildv2-connection" {
  source  = "altissimo-hq/cloudbuildv2-connection/google"
  version = "1.0.3"

  github_login               = "lukwam"
  github_app_installation_id = 267250
  project                    = module.project.project_id
  region                     = var.region

  oauth_token_secret = "github-terraform-token"
  secret_project     = "lukwam-dev"

  repositories = [
    "hex",
  ]
}

resource "google_cloudbuild_trigger" "build-app-image" {
  provider    = google-beta
  name        = "build-app-image"
  description = "Build App Image"
  project     = module.project.services["cloudbuild.googleapis.com"].project
  location    = var.region

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  included_files = [
    "app/**",
  ]

  repository_event_config {
    repository = module.cloudbuildv2-connection.repository_ids["hex"]
    push {
      branch = var.branch
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
        "${var.region}-docker.pkg.dev/${module.project.project_id}/docker/hex:latest",
        ".",
      ]
      dir  = "app"
      name = "gcr.io/cloud-builders/docker"
    }
    images = [
      "${var.region}-docker.pkg.dev/${module.project.project_id}/docker/hex:latest"
    ]
  }
}

resource "google_cloudbuild_trigger" "deploy-app" {
  provider    = google-beta
  name        = "deploy-app"
  description = "Deploy App"
  filename    = "app/cloudbuild.yaml"
  project     = module.project.services["cloudbuild.googleapis.com"].project
  location    = var.region

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  included_files = [
    "app/**",
  ]

  repository_event_config {
    repository = module.cloudbuildv2-connection.repository_ids["hex"]
    push {
      branch = var.branch
    }
  }

  substitutions = {
    _REGION = var.region
  }
}

resource "google_cloudbuild_trigger" "deploy-api" {
  provider    = google-beta
  name        = "deploy-api"
  description = "Deploy api Cloud Run Service"
  filename    = "images/api/cloudbuild.yaml"
  project     = module.project.services["cloudbuild.googleapis.com"].project
  location    = var.region

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  included_files = [
    "images/api/**",
  ]

  repository_event_config {
    repository = module.cloudbuildv2-connection.repository_ids["hex"]
    push {
      branch = var.branch
    }
  }

  substitutions = {
    _REGION = var.region
  }
}

resource "google_cloudbuild_trigger" "deploy-image2png" {
  provider    = google-beta
  name        = "deploy-image2png"
  description = "Deploy image2png Cloud Run Service"
  filename    = "images/image2png/cloudbuild.yaml"
  project     = module.project.services["cloudbuild.googleapis.com"].project
  location    = var.region

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  included_files = [
    "images/image2png/**",
  ]

  repository_event_config {
    repository = module.cloudbuildv2-connection.repository_ids["hex"]
    push {
      branch = var.branch
    }
  }

  substitutions = {
    _REGION = var.region
  }
}
