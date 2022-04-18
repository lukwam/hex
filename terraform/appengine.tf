resource "google_app_engine_application" "app" {
  project       = google_project_service.services["appengine.googleapis.com"].project
  location_id   = var.region
  database_type = "CLOUD_FIRESTORE"

  iap {
    enabled              = false
    oauth2_client_id     = google_iap_client.appengine.client_id
    oauth2_client_secret = google_iap_client.appengine.secret
  }

}

resource "google_app_engine_domain_mapping" "domain_mapping" {
  domain_name = var.domain_name

  ssl_settings {
    ssl_management_type = "AUTOMATIC"
  }

  depends_on = [
    google_project_service.services["appengine.googleapis.com"]
  ]
}
