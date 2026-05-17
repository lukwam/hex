# Admin domain mapping
data "google_cloud_run_service" "admin" {
  count    = var.domain_name != "" ? 1 : 0
  name     = "admin"
  location = var.region
}

resource "google_cloud_run_domain_mapping" "admin" {
  count    = var.domain_name != "" ? 1 : 0
  name     = var.domain_name
  location = data.google_cloud_run_service.admin[0].location
  metadata {
    namespace = module.project.project_id
  }
  spec {
    route_name = data.google_cloud_run_service.admin[0].name
  }

  lifecycle {
    ignore_changes = [
      metadata[0].annotations,
      metadata[0].labels,
    ]
  }
}

# API domain mapping
data "google_cloud_run_service" "api" {
  count    = var.api_domain_name != "" ? 1 : 0
  name     = "api"
  location = var.region
}

resource "google_cloud_run_domain_mapping" "api" {
  count    = var.api_domain_name != "" ? 1 : 0
  name     = var.api_domain_name
  location = data.google_cloud_run_service.api[0].location
  metadata {
    namespace = module.project.project_id
  }
  spec {
    route_name = data.google_cloud_run_service.api[0].name
  }

  lifecycle {
    ignore_changes = [
      metadata[0].annotations,
      metadata[0].labels,
    ]
  }
}

# App domain mapping
data "google_cloud_run_service" "app" {
  count    = var.app_domain_name != "" ? 1 : 0
  name     = "app"
  location = var.region
}

resource "google_cloud_run_domain_mapping" "app" {
  count    = var.app_domain_name != "" ? 1 : 0
  name     = var.app_domain_name
  location = data.google_cloud_run_service.app[0].location
  metadata {
    namespace = module.project.project_id
  }
  spec {
    route_name = data.google_cloud_run_service.app[0].name
  }

  lifecycle {
    ignore_changes = [
      metadata[0].annotations,
      metadata[0].labels,
    ]
  }
}
