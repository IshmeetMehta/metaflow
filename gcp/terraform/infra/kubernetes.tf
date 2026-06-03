resource "google_service_account" "metaflow_kubernetes_control_plane_service_account" {
  provider = google-beta
  account_id   = "sa-mf-k8s-${var.org_prefix}"
  display_name = "Service Account for Kubernetes Control Plane (${var.org_prefix})"
}

resource "google_container_cluster" "metaflow_kubernetes" {
  provider = google-beta
  name               = var.kubernetes_cluster_name
  initial_node_count = 1

  # Allow Terraform to delete the cluster without manual intervention
  deletion_protection = false

  # Ensure networking and database are ready before the cluster is created,
  # and that the cluster is deleted before the networking bridge is removed.
  depends_on = [
    google_sql_database_instance.metaflow_database_server,
    google_service_networking_connection.metaflow_database_private_vpc_connection
  ]

  location = var.zone
  workload_identity_config {
    workload_pool = "${var.project}.svc.id.goog"
  }
  node_config {
    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    service_account = google_service_account.metaflow_kubernetes_control_plane_service_account.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
  cluster_autoscaling {
    enabled = true
    resource_limits {
      resource_type = "cpu"
      minimum = 1
      maximum = 200
    }
    resource_limits {
      resource_type = "memory"
      minimum = 2
      maximum = 400
    }
  }
  network = google_compute_network.metaflow_compute_network.name
  subnetwork = google_compute_subnetwork.metaflow_subnet_for_kubernetes.name
  networking_mode = "VPC_NATIVE"
  # empty block is required
  ip_allocation_policy {}
}