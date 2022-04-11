resource "google_secret_manager_secret" "image-reader-key" {
  secret_id = "image-reader-key"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "image-reader-key" {
  secret = google_secret_manager_secret.image-reader-key.id
  secret_data = base64decode(google_service_account_key.image-reader.private_key)
}

resource "google_secret_manager_secret" "oauth2-client-secret" {
  secret_id = "oauth2-client-secret"
  replication {
    automatic = true
  }
}
