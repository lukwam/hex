resource "google_iap_brand" "project" {
  support_email     = "admin@lukwam.dev"
  application_title = var.project_name
  project           = google_project.project.number
  depends_on = [
    google_project_service.services["iap.googleapis.com"]
  ]
}

resource "google_iap_client" "appengine" {
  display_name = "IAP-App-Engine-app"
  brand        =  google_iap_brand.project.name
}

resource "google_iap_web_type_app_engine_iam_member" "http-resource-accessors" {
for_each = toset([
    "user:admin@lukwam.dev",
    "user:coxrathvon@gmail.com",
    "user:danchall@gmail.com",
    "user:lukwam@gmail.com",
  ])
  project = google_app_engine_application.app.project
  app_id  = google_app_engine_application.app.app_id
  role    = "roles/iap.httpsResourceAccessor"
  member  = each.key
}
