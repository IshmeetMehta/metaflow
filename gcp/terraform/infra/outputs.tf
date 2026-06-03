output metaflow_workload_identity_gsa_id {
  value = google_service_account.metaflow_kubernetes_workload_identity_service_account.id
}

output "kubernetes_endpoint" {
  value = google_container_cluster.metaflow_kubernetes.endpoint
}

output "kubernetes_ca_certificate" {
  value = google_container_cluster.metaflow_kubernetes.master_auth[0].cluster_ca_certificate
}

output "database_connection_name" {
  value = google_sql_database_instance.metaflow_database_server.connection_name
}