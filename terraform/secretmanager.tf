resource "random_password" "flask-secret-key" {
  length  = 64
  special = true
}

resource "google_secret_manager_secret" "flask-secret-key" {
  secret_id = "flask-secret-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "flask-secret-key" {
  secret      = google_secret_manager_secret.flask-secret-key.id
  secret_data = random_password.flask-secret-key.result
}

resource "google_secret_manager_secret" "image-reader-key" {
  secret_id = "image-reader-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "image-reader-key" {
  secret      = google_secret_manager_secret.image-reader-key.id
  secret_data = base64decode(google_service_account_key.image-reader.private_key)
}

resource "google_secret_manager_secret" "oauth2-client-secret" {
  secret_id = "oauth2-client-secret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "wordpress-password" {
  secret_id = "wordpress-password"
  replication {
    auto {}
  }
}
