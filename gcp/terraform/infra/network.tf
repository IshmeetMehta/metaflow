resource "google_compute_network" "metaflow_compute_network" {
  provider = google-beta

  name = "vpc-metaflow-${var.org_prefix}"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "metaflow_subnet_for_kubernetes" {
  provider = google-beta

  name          = "subnet-metaflow-kubernetes-${var.org_prefix}"
  ip_cidr_range = "10.2.0.0/16"
  region        = var.region
  network       = google_compute_network.metaflow_compute_network.id
}

resource "google_compute_global_address" "metaflow_database_private_ip_address" {
  provider = google-beta

  name          = "ip-metaflow-private-${var.org_prefix}"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.metaflow_compute_network.id
}

resource "google_service_networking_connection" "metaflow_database_private_vpc_connection" {
  provider = google-beta

  network                 = google_compute_network.metaflow_compute_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.metaflow_database_private_ip_address.name]
}