terraform {
  backend "gcs" {
    bucket = "lukwam-hex-tf"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "7.30.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "7.30.0"
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
variable "app" {}
variable "branch" {}
variable "billing_account" {}
variable "domain_name" {}
variable "folder_id" {}
variable "project_id" {}
variable "project_name" {}
variable "region" {}
