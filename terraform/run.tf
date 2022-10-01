data "google_cloud_run_service" "api" {
  name = "api"
  location = var.region
}

resource "google_cloud_run_domain_mapping" "api" {
  name     = var.api_domain_name
  location = data.google_cloud_run_service.api.location
  metadata {
    namespace = google_project.project.project_id
  }
  spec {
    route_name = data.google_cloud_run_service.api.name
  }
}
