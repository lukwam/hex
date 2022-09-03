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
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "compute.googleapis.com",
    "drive.googleapis.com",
    "eventarc.googleapis.com",
    "iap.googleapis.com",
    "logging.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sheets.googleapis.com",
    "sql-component.googleapis.com",
    "sqladmin.googleapis.com",
    "storage-api.googleapis.com",
    "storage.googleapis.com",
  ])
  project = google_project.project.project_id
  service = each.key
  disable_dependent_services = false
  disable_on_destroy         = false
}

resource "google_service_account" "image-reader" {
  account_id   = "image-reader"
  display_name = "Image Reader"
}

resource "google_service_account_key" "image-reader" {
  service_account_id = google_service_account.image-reader.name
}

resource "google_project_iam_member" "appspot" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",
  ])
  project = google_project_service.services["appengine.googleapis.com"].project
  role    = each.key
  member  = "serviceAccount:${google_project.project.project_id}@appspot.gserviceaccount.com"
}

resource "google_project_iam_member" "cloudbuild" {
  for_each = toset([
    "roles/appengine.appAdmin",
    "roles/cloudbuild.builds.builder",
    "roles/iam.serviceAccountUser",
    "roles/run.admin",
  ])
  project = google_project_service.services["cloudbuild.googleapis.com"].project
  role    = each.key
  member  = "serviceAccount:${google_project.project.number}@cloudbuild.gserviceaccount.com"
}

resource "google_project_iam_member" "compute" {
  for_each = toset([
    "roles/eventarc.eventReceiver",
    "roles/run.invoker",
  ])
  project = google_project_service.services["compute.googleapis.com"].project
  role    = each.key
  member  = "serviceAccount:${google_project.project.number}-compute@developer.gserviceaccount.com"
}

resource "google_project_iam_member" "pubsub" {
  for_each = toset([
    "roles/iam.serviceAccountTokenCreator",
  ])
  project = google_project_service.services["storage.googleapis.com"].project
  role    = each.key
  member  = "serviceAccount:service-${google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "storage" {
  for_each = toset([
    "roles/pubsub.publisher",
  ])
  project = google_project_service.services["storage.googleapis.com"].project
  role    = each.key
  member  = "serviceAccount:service-${google_project.project.number}@gs-project-accounts.iam.gserviceaccount.com"
}
