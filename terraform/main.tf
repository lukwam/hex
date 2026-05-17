terraform {
  backend "gcs" {}
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 7.30.0, < 8.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 7.30.0, < 8.0"
    }
  }
}

provider "google" {
  billing_project       = var.project_id
  project               = var.project_id
  user_project_override = true
}

provider "google-beta" {
  billing_project       = var.project_id
  project               = var.project_id
  user_project_override = true
}

variable "api_domain_name" {}
variable "app_domain_name" {}
variable "app" {}
variable "branch" {}
variable "billing_account" {}
variable "domain_name" {}
variable "folder_id" {}
variable "project_id" {}
variable "project_name" {}
variable "region" {}

locals {
  # Bucket naming: prod = "lukwam-hex-{name}", dev = "lukwam-hex-{name}-dev"
  env_suffix = var.project_id == "lukwam-hex" ? "" : "-${trimprefix(var.project_id, "lukwam-hex-")}"
}
