module "project" {
  source  = "altissimo-hq/project/google"
  version = "1.0.14"

  billing_account = var.billing_account
  folder_id       = var.folder_id
  project_id      = var.project_id
  project_name    = var.project_name

  gcloud_command = "gcloud"

  labels = {
    app = var.app
  }

  services = [
    "appengine.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "drive.googleapis.com",
    "eventarc.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "iap.googleapis.com",
    "logging.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sheets.googleapis.com",
    "sql-component.googleapis.com",
    "sqladmin.googleapis.com",
    "storage-api.googleapis.com",
    "storage.googleapis.com",
  ]

  iam_policy = {
    "roles/appengine.appAdmin" = [
      "serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com",
    ]
    "roles/appengine.serviceAgent" = [
      "serviceAccount:service-PROJECT_NUMBER@gcp-gae-service.iam.gserviceaccount.com",
    ]
    "roles/artifactregistry.serviceAgent" = [
      "serviceAccount:service-PROJECT_NUMBER@gcp-sa-artifactregistry.iam.gserviceaccount.com",
    ]
    "roles/cloudbuild.builds.builder" = [
      "serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com",
      "serviceAccount:cloudbuild@${var.project_id}.iam.gserviceaccount.com",
    ]
    "roles/cloudbuild.serviceAgent" = [
      "serviceAccount:service-PROJECT_NUMBER@gcp-sa-cloudbuild.iam.gserviceaccount.com",
    ]
    "roles/cloudfunctions.serviceAgent" = [
      "serviceAccount:service-PROJECT_NUMBER@gcf-admin-robot.iam.gserviceaccount.com",
    ]
    "roles/cloudsecuritycompliance.serviceAgent" = [
      "serviceAccount:service-PROJECT_NUMBER@gcp-sa-csc-hpsa.iam.gserviceaccount.com",
    ]
    "roles/compute.instanceGroupManagerServiceAgent" = [
      "serviceAccount:PROJECT_NUMBER@cloudservices.gserviceaccount.com",
    ]
    "roles/compute.serviceAgent" = [
      "serviceAccount:service-PROJECT_NUMBER@compute-system.iam.gserviceaccount.com",
    ]
    "roles/containerregistry.ServiceAgent" = [
      "serviceAccount:service-PROJECT_NUMBER@containerregistry.iam.gserviceaccount.com",
    ]
    "roles/datastore.user" = [
      "serviceAccount:altissimo-coxrathvon@appspot.gserviceaccount.com",
    ]
    "roles/documentaicore.serviceAgent" = [
      "serviceAccount:service-PROJECT_NUMBER@gcp-sa-prod-dai-core.iam.gserviceaccount.com",
    ]
    "roles/editor" = [
      "serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com",
      "serviceAccount:PROJECT_NUMBER@cloudservices.gserviceaccount.com",
      "serviceAccount:${var.project_id}@appspot.gserviceaccount.com",
    ]
    "roles/eventarc.eventReceiver" = [
      "serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com",
    ]
    "roles/eventarc.serviceAgent" = [
      "serviceAccount:service-PROJECT_NUMBER@gcp-sa-eventarc.iam.gserviceaccount.com",
    ]
    "roles/firebaserules.system" = [
      "serviceAccount:service-PROJECT_NUMBER@firebase-rules.iam.gserviceaccount.com",
    ]
    "roles/firestore.serviceAgent" = [
      "serviceAccount:service-PROJECT_NUMBER@gcp-sa-firestore.iam.gserviceaccount.com",
    ]
    "roles/iam.serviceAccountTokenCreator" = [
      "serviceAccount:service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com",
      "serviceAccount:${var.project_id}@appspot.gserviceaccount.com",
      "serviceAccount:admin-service@${var.project_id}.iam.gserviceaccount.com",
      "serviceAccount:api-service@${var.project_id}.iam.gserviceaccount.com",
      "user:admin@lukwam.dev",
      "user:karlsson@altissimo.io",
    ]
    "roles/iam.serviceAccountUser" = [
      "serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com",
      "serviceAccount:cloudbuild@${var.project_id}.iam.gserviceaccount.com",
    ]
    "roles/owner" = [
      "user:admin@lukwam.dev",
      "user:karlsson@altissimo.io",
    ]
    "roles/pubsub.publisher" = [
      "serviceAccount:service-PROJECT_NUMBER@gs-project-accounts.iam.gserviceaccount.com",
    ]
    "roles/pubsub.serviceAgent" = [
      "serviceAccount:service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com",
    ]
    "roles/run.admin" = [
      "serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com",
      "serviceAccount:cloudbuild@${var.project_id}.iam.gserviceaccount.com",
    ]
    "roles/run.invoker" = [
      "serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com",
    ]
    "roles/run.serviceAgent" = [
      "serviceAccount:service-PROJECT_NUMBER@serverless-robot-prod.iam.gserviceaccount.com",
    ]
    "roles/secretmanager.secretAccessor" = [
      "serviceAccount:${var.project_id}@appspot.gserviceaccount.com",
      "serviceAccount:altissimo-coxrathvon@appspot.gserviceaccount.com",
    ]
    "roles/storage.objectViewer" = [
      "serviceAccount:altissimo-coxrathvon@appspot.gserviceaccount.com",
    ]
    "roles/viewer" = [
      "serviceAccount:altissimo-coxrathvon@appspot.gserviceaccount.com",
    ]
  }

  service_accounts = {
    "admin-service" = {
      display_name = "Admin Service"
    }
    "api-service" = {
      display_name = "API Service"
    }
    "cloudbuild" = {
      display_name = "Cloud Build"
    }
    "image-reader" = {
      display_name = "Image Reader"
    }
  }
}

resource "google_service_account_key" "image-reader" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/image-reader@${var.project_id}.iam.gserviceaccount.com"

  depends_on = [module.project]
}

output "project_number" {
  value = module.project.number
}

output "project_id" {
  value = module.project.project_id
}
