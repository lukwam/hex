resource "google_app_engine_application" "app" {
  project       = module.project.project_id
  location_id   = var.region
  database_type = "CLOUD_FIRESTORE"

  # iap {
  #   enabled              = true
  #   oauth2_client_id     = google_iap_client.appengine.client_id
  #   oauth2_client_secret = google_iap_client.appengine.secret
  # }

}
