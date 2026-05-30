terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.12.1"
    }
    google = {
      source  = "hashicorp/google"
      version = "4.31.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.3.2"
    }
    local = {
      source  = "hashicorp/local"
      version = "2.2.3"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "2.6.0"
    }
  }
}

locals {
  # Derived paths
  metaflow_datastore_sysroot_gs = "gs://${var.storage_bucket_name}/metaflow"
  airflow_logs_bucket_path      = "${var.storage_bucket_name}/airflow-logs"

  # Default service configurations
  metaflow_workload_identity_ksa_name = "ksa-metaflow"
  metadata_service_image             = "public.ecr.aws/outerbounds/metaflow-metadata-service:v2.2.1"
  metaflow_ui_backend_service_image  = "public.ecr.aws/outerbounds/metaflow-ui-backend:v1.2.0"
  metaflow_ui_static_service_image   = "public.ecr.aws/outerbounds/metaflow-ui-static:v1.2.0"
  airflow_version                    = "2.3.0"
  airflow_frenet_secret              = "B_T9-7_7L_7-8_7-7_7-7_7-7_7-7_7-7_7-7_7=" # Example secret
}

data "google_client_config" "default" {
  provider   = google
}

provider "kubernetes" {
  host                   = "https://${module.infra.kubernetes_endpoint}"
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(module.infra.kubernetes_ca_certificate)
}
provider "helm" {
  kubernetes {
    host                   = "https://${module.infra.kubernetes_endpoint}"
    cluster_ca_certificate = base64decode(module.infra.kubernetes_ca_certificate)
    token                  = data.google_client_config.default.access_token
    # token is required here and we remove `client_certificate` / `client_key` because it results in this error like : 
    # `Error: unable to build kubernetes objects from release manifest: unknown`
    # More notes on this issue can be found here : https://github.com/hashicorp/terraform-provider-helm/issues/513
  }
}

# This will be used for invoking kubectl re: Argo installation
resource "local_file" "kubeconfig" {
  content = templatefile("${path.module}/kubeconfig_template.yaml", {
    cluster_name  = var.kubernetes_cluster_name
    endpoint      = module.infra.kubernetes_endpoint
    cluster_ca    = module.infra.kubernetes_ca_certificate
    cluster_token = data.google_client_config.default.access_token
  })
  filename = "${path.root}/kubeconfig"
}

module "infra" {
  source                              = "./infra"
  org_prefix                          = var.org_prefix
  region                              = var.region
  zone                                = var.zone
  project                             = var.project
  database_server_name                = var.database_server_name
  kubernetes_cluster_name             = var.kubernetes_cluster_name
  storage_bucket_name                 = var.storage_bucket_name
  metaflow_workload_identity_gsa_name = var.metaflow_workload_identity_gsa_name
  service_account_key_file            = var.service_account_key_file
}

module "services" {
  depends_on                          = [module.infra]
  source                              = "./services"
  metaflow_ui_static_service_image    = local.metaflow_ui_static_service_image
  metaflow_ui_backend_service_image   = local.metaflow_ui_backend_service_image
  metaflow_datastore_sysroot_gs       = local.metaflow_datastore_sysroot_gs
  airflow_logs_bucket_path            = local.airflow_logs_bucket_path
  metaflow_db_host                    = "localhost"
  metaflow_db_name                    = "metaflow"
  metaflow_db_user                    = "metaflow"
  metaflow_db_password                = "metaflow"
  metaflow_db_port                    = 5432
  project                             = var.project
  db_connection_name                  = module.infra.database_connection_name
  metaflow_workload_identity_gsa_id   = module.infra.metaflow_workload_identity_gsa_id
  metaflow_workload_identity_gsa_name = var.metaflow_workload_identity_gsa_name
  metaflow_workload_identity_ksa_name = local.metaflow_workload_identity_ksa_name
  metadata_service_image              = local.metadata_service_image
  kubeconfig_path                     = local_file.kubeconfig.filename
  deploy_airflow                      = var.deploy_airflow
  deploy_argo                         = var.deploy_argo
  airflow_version                     = local.airflow_version
  airflow_frenet_secret               = local.airflow_frenet_secret
}