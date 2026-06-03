resource "google_storage_bucket" metaflow_storage_bucket {
  provider = google-beta
  name          = var.storage_bucket_name
  location      = var.region
  force_destroy = true # Allows deleting the bucket even if it contains Metaflow data

  uniform_bucket_level_access = true
}
