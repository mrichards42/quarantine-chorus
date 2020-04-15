provider "google" {
  version = "3.5.0"

  credentials = file(var.credentials_file)

  project = var.project
  region  = var.region
  zone    = var.zone
}

# enable services

resource "google_project_service" "functions" {
  project = var.project
  service = "cloudfunctions.googleapis.com"
  disable_dependent_services = true
}

resource "google_project_service" "storage" {
  project = var.project
  service = "storage-component.googleapis.com"
  disable_dependent_services = true
}

resource "google_project_service" "firestore" {
  project = var.project
  service = "firestore.googleapis.com"
  disable_dependent_services = true
}
