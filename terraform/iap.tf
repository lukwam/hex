resource "google_iap_web_type_app_engine_iam_member" "http-resource-accessors" {
  for_each = toset([
    "user:admin@lukwam.dev",
    "user:coxrathvon@gmail.com",
    "user:danchall@gmail.com",
    "user:karlsson@altissimo.io",
    "user:lukwam@gmail.com",
  ])
  project = google_app_engine_application.app.project
  app_id  = google_app_engine_application.app.app_id
  role    = "roles/iap.httpsResourceAccessor"
  member  = each.key
}
