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
