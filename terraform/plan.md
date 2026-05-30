# Metaflow GCP Deployment Summary

This document summarizes the changes made to the Terraform configuration to enable a keyless, conflict-free deployment of the Metaflow stack on GCP.

## Comparison with Upstream Repository
Compared to the official [Metaflow Tools GCP Template](https://github.com/outerbounds/metaflow-tools/tree/master/gcp/terraform), the following modifications were introduced:

## 1. Authentication & Security
- **Keyless Setup**: Set `service_account_key_file` to `"NONE"` in `terraform.tfvars` to use Application Default Credentials (ADC) via `gcloud auth application-default login`.
- **Policy Compliance**: Removed `google_service_account_key` resources from `infra/google_service_account.tf` to bypass the `iam.disableServiceAccountKeyCreation` organization constraint.
- **Variable Defaults**: Updated `variables.tf` to make the service account key optional.
- **Removal of Static Keys**: **(Departure from Upstream)** Deleted `google_service_account_key` and `local_file` resources in `infra/google_service_account.tf`. The upstream repo assumes users can generate JSON keys, which is often blocked by GCP Organization Policies.
- **ADC Integration**: Updated `variables.tf` to default `service_account_key_file` to `"NONE"`. This allows local runs via `gcloud auth application-default login` instead of requiring a dangerous local JSON file.

## 2. Resource Naming & Conflict Resolution (Option A)
- **Naming Strategy Change**: **(Departure from Upstream)** Upstream uses `${terraform.workspace}` for resource names. Since most users stay in the `default` workspace, this causes "AlreadyExists" errors in shared projects.
- **Unique Prefixing**: Introduced `org_prefix = "mfsandbox"` to ensure resource names are unique to this deployment.
- **Submodule Updates**: 
    - Declared `org_prefix` in `infra/variables.tf`.
    - Passed the variable from the root `main.tf` to the `infra` module.
- **Refactored Naming Logic**: Updated `infra/network.tf` and `infra/kubernetes.tf` to use `var.org_prefix` for the VPC, Subnetwork, and Service Account names instead of the hardcoded `terraform.workspace` values.

## 3. Infrastructure Reliability
- **Automated API Enablement**: Created `apis.tf` to manage necessary GCP Service APIs (Compute, GKE, SQL, etc.).
- **Self-contained API Enablement**: **(New File)** Created `apis.tf`. Upstream assumes APIs are pre-enabled; this version enables them automatically (Compute, Container, SQL, etc.).
- **Safe Teardown**: Configured `google_project_service` with `disable_on_destroy = false` to ensure that destroying the Metaflow stack does not disable critical services for the entire GCP project.

## 4. Clean Teardown Configuration
- **GCS Buckets**: Added `force_destroy = true` to `infra/storage.tf` to allow `terraform destroy` to remove buckets even if they contain data.
- **Cloud SQL**: Set `deletion_protection = false` in `infra/database.tf` to allow automated removal of the database instance without manual intervention in the GCP Console.
- **GCS Buckets**: Explicitly set `force_destroy = true` in `infra/storage.tf`.
- **Cloud SQL**: Set `deletion_protection = false` in `infra/database.tf`. Upstream often leaves this as `true` (GCP default), which causes `terraform destroy` to fail until manually toggled in the console.

## 5. Code Quality & Bug Fixes
- **Output Fixes**: Cleaned up `output.tf` by removing invalid `local.` references that were causing plan-time errors.
- **Bug Fix in Output**: **(Departure from Upstream)** Fixed references in `output.tf`. Upstream occasionally contains `local.` references for variables that are actually passed via `var.`, leading to `undeclared local value` errors during planning.
- **Variable Completeness**: Defined `db_generation_number` and `project` IDs correctly in the `tfvars` file to prevent interactive prompts.

---

### Deployment Procedure (Stable Flow)
To avoid state inconsistency and "Root resource was present, but now absent" errors (common with GCP IAM and the `-target` flag), use a standard unified apply:

1. **Authenticate**: 
   `gcloud auth application-default login`
2. **Initialize**:
   `terraform init`
3. **Deploy Full Stack**:
   `terraform apply -var-file=terraform.tfvars`
   
*Note: Targeted applies (`-target`) are discouraged for routine use as they skip dependency refreshes that GCP requires for eventual consistency.*

### Troubleshooting

#### Error: deletion_protection is set to true
This is a safety feature for GKE. Terraform cannot delete the cluster while this is enabled.
**Resolution**: Set `deletion_protection = false` in `infra/kubernetes.tf` and run a quick `terraform apply` before trying to destroy again.

#### Error: Producer services are still using this connection
This happens during `destroy` if the Cloud SQL instance hasn't been deleted yet. The private VPC peering cannot be removed while a database is still "attached" to it.
**Resolution**: This is usually a side effect of another resource (like GKE) failing to delete. Fix the primary error first, and Terraform will handle the order correctly in the next attempt.

#### Error 409: Service account already exists
If an `apply` crashes mid-way, GCP resources may be created without Terraform saving them to the state file. To fix this, "adopt" the resources into your state:

```bash
terraform import module.infra.google_service_account.metaflow_kubernetes_workload_identity_service_account projects/<PROJECT_ID>/serviceAccounts/<SA_NAME>@<PROJECT_ID>.iam.gserviceaccount.com
terraform import module.infra.google_sql_database_instance.metaflow_database_server projects/<PROJECT_ID>/instances/<DB_NAME>
terraform import module.infra.google_storage_bucket.metaflow_storage_bucket <BUCKET_NAME>
```

### Cleanup
To remove all resources:
`terraform destroy -var-file=terraform.tfvars`