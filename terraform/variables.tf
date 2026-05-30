variable "org_prefix" {
  type        = string
  description = "A short alphanumeric string used for naming resources uniquely."
}

variable "project" {
  type        = string
  description = "The GCP Project ID."
}

variable "db_generation_number" {
  type        = number
  description = "An integer used to generate unique DB instance names."
}

variable "region" {
  type = string
}

variable "zone" {
  type = string
}

variable "database_server_name" {
  type = string
}

variable "kubernetes_cluster_name" {
  type = string
}

variable "metaflow_workload_identity_gsa_name" {
  type = string
}

variable "storage_bucket_name" {
  type = string
}

variable "service_account_key_file" {
  type = string
  default = "NONE"
}

variable "deploy_argo" {
  type    = bool
  default = true
}

variable "deploy_airflow" {
  type    = bool
  default = false
}