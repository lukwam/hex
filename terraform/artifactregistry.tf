resource "google_artifact_registry_repository" "docker" {
  provider      = google-beta
  location      = var.region
  project       = google_project.project.project_id
  repository_id = "docker"
  description   = "Docker repository"
  format        = "DOCKER"
}
