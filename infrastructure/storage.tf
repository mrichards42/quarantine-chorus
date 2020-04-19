# cloud storage buckets

resource "google_storage_bucket" "upload" {
  project  = google_project_service.storage.project
  name     = "${var.bucket_prefix}-upload"
  location = "US"
}

resource "google_storage_bucket" "aligned" {
  project  = google_project_service.storage.project
  name     = "${var.bucket_prefix}-aligned"
  location = "US"
}

resource "google_storage_bucket" "audio_extracted" {
  project  = google_project_service.storage.project
  name     = "${var.bucket_prefix}-audio-extracted"
  location = "US"
}
