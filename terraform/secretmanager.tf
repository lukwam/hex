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

resource "google_secret_manager_secret" "oauth2-client-config" {
  secret_id = "oauth2-client-config"
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

# ---------------------------------------------------------------------------
# Per-secret IAM: admin-service
# ---------------------------------------------------------------------------

resource "google_secret_manager_secret_iam_member" "admin-oauth2-client-config" {
  secret_id = google_secret_manager_secret.oauth2-client-config.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:admin-service@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "admin-flask-secret-key" {
  secret_id = google_secret_manager_secret.flask-secret-key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:admin-service@${var.project_id}.iam.gserviceaccount.com"
}
# ---------------------------------------------------------------------------
# API keys (Terraform-managed)
#
# Each client app gets its own API key. Terraform generates a UUID, registers
# it as a Firestore APIKey document (so the API service accepts it), and
# stores the value in Secret Manager (so Cloud Run can inject it).
#
# To import the existing manually-created key:
#   terraform import random_uuid.hex-app-api-key 7e2107f5-76ce-4076-9db3-f59d5b799dcf
#   terraform import google_firestore_document.hex-app-api-key "projects/PROJECT/databases/(default)/documents/api_keys/7e2107f5-..."
# ---------------------------------------------------------------------------

# ── Hex App (this project) ────────────────────────────────────────

resource "random_uuid" "hex-app-api-key" {}

resource "google_firestore_document" "hex-app-api-key" {
  project     = var.project_id
  collection  = "api_keys"
  document_id = random_uuid.hex-app-api-key.result
  fields = jsonencode({
    name        = { stringValue = "hex-app" }
    description = { stringValue = "API key for the Hex front-end app (Terraform-managed)" }
    created_at  = { timestampValue = timestamp() }
  })

  lifecycle {
    ignore_changes = [fields]
  }
}

resource "google_secret_manager_secret" "hex-app-api-key" {
  secret_id = "hex-app-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "hex-app-api-key" {
  secret      = google_secret_manager_secret.hex-app-api-key.id
  secret_data = random_uuid.hex-app-api-key.result
}

resource "google_secret_manager_secret_iam_member" "hex-app-api-key" {
  secret_id = google_secret_manager_secret.hex-app-api-key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:app-service@${var.project_id}.iam.gserviceaccount.com"
}

# ── CoxRathvon App (cross-project) ───────────────────────────────

resource "random_uuid" "coxrathvon-app-api-key" {}

resource "google_firestore_document" "coxrathvon-app-api-key" {
  project     = var.project_id
  collection  = "api_keys"
  document_id = random_uuid.coxrathvon-app-api-key.result
  fields = jsonencode({
    name        = { stringValue = "coxrathvon-app" }
    description = { stringValue = "API key for the CoxRathvon front-end app (Terraform-managed)" }
    created_at  = { timestampValue = timestamp() }
  })

  lifecycle {
    ignore_changes = [fields]
  }
}

resource "google_secret_manager_secret" "coxrathvon-app-api-key" {
  secret_id = "coxrathvon-app-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "coxrathvon-app-api-key" {
  secret      = google_secret_manager_secret.coxrathvon-app-api-key.id
  secret_data = random_uuid.coxrathvon-app-api-key.result
}

# IAM: grant the coxrathvon project's App Engine SA access to read this key.
resource "google_secret_manager_secret_iam_member" "coxrathvon-app-api-key" {
  secret_id = google_secret_manager_secret.coxrathvon-app-api-key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:altissimo-coxrathvon@appspot.gserviceaccount.com"
}
