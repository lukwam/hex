resource "google_project" "project" {
  name                = var.project_name
  project_id          = var.project_id
  folder_id           = var.folder_id
  billing_account     = var.billing_account

  labels = {
      app             = var.app,
      billing         = lower(var.billing_account),
  }

  auto_create_network = false
  skip_delete         = false
}

resource "google_project_service" "services" {
  for_each = toset([
    "appengine.googleapis.com",
    "cloudbuild.googleapis.com",
    "iap.googleapis.com",
    "sheets.googleapis.com",
    "storage-api.googleapis.com",
  ])
  project = google_project.project.project_id
  service = each.key
  disable_dependent_services = false
  disable_on_destroy         = false
}

resource "google_project_iam_member" "cloudbuild" {
  for_each = toset([
    "roles/appengine.appAdmin",
    "roles/cloudbuild.builds.builder",
    "roles/iam.serviceAccountUser",
  ])
  project = google_project_service.services["cloudbuild.googleapis.com"].project
  role    = each.key
  member  = "serviceAccount:${google_project.project.number}@cloudbuild.gserviceaccount.com"
}
