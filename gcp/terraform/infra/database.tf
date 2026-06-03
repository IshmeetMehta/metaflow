resource "time_sleep" "wait_after_db_instance_destroy" {
  # Buffer for GCP to release the VPC Peering locks after DB deletion.
  # 300s (5 mins) is recommended for Cloud SQL to fully unhook from Service Networking.
  destroy_duration = "300s"

  depends_on = [google_service_networking_connection.metaflow_database_private_vpc_connection]
}

resource "google_sql_database_instance" "metaflow_database_server" {
  provider = google-beta

  name             = var.database_server_name
  region           = var.region
  database_version = "POSTGRES_14"

  # Allows Terraform to delete the instance without manual intervention in the GCP Console
  deletion_protection = false

  depends_on = [time_sleep.wait_after_db_instance_destroy]

  settings {
    tier = "db-custom-1-3840"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.metaflow_compute_network.id
    }
    backup_configuration {
      enabled = true
    }
  }
}

resource "google_sql_user" "metaflow_db_user" {
  provider = google-beta
  name     = "metaflow"
  instance = google_sql_database_instance.metaflow_database_server.id
  password = "metaflow"
  deletion_policy = "ABANDON"

  depends_on = [time_sleep.wait_after_db_instance_destroy]
}

resource "google_sql_database" "metaflow_database" {
  provider = google-beta
  name     = "metaflow"
  instance = google_sql_database_instance.metaflow_database_server.id

  depends_on = [time_sleep.wait_after_db_instance_destroy]
}
