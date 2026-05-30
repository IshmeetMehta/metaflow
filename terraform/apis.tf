resource "google_project_service" "metaflow_services" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com"
  ])

  project            = var.project
  service            = each.key
  # Prevents breaking the GCP project by disabling APIs like 'compute' or 'iam' during a destroy
  disable_on_destroy = false
}