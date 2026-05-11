# Terraform Configuration

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_google"></a> [google](#requirement\_google) | >= 7.30.0, < 8.0 |
| <a name="requirement_google-beta"></a> [google-beta](#requirement\_google-beta) | >= 7.30.0, < 8.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_google"></a> [google](#provider\_google) | 7.31.0 |
| <a name="provider_google-beta"></a> [google-beta](#provider\_google-beta) | 7.31.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_cloudbuildv2-connection"></a> [cloudbuildv2-connection](#module\_cloudbuildv2-connection) | altissimo-hq/cloudbuildv2-connection/google | 1.0.3 |
| <a name="module_project"></a> [project](#module\_project) | altissimo-hq/project/google | 1.0.14 |

## Resources

| Name | Type |
|------|------|
| [google-beta_google_artifact_registry_repository.docker](https://registry.terraform.io/providers/hashicorp/google-beta/latest/docs/resources/google_artifact_registry_repository) | resource |
| [google-beta_google_cloudbuild_trigger.build-app-image](https://registry.terraform.io/providers/hashicorp/google-beta/latest/docs/resources/google_cloudbuild_trigger) | resource |
| [google-beta_google_cloudbuild_trigger.deploy-api](https://registry.terraform.io/providers/hashicorp/google-beta/latest/docs/resources/google_cloudbuild_trigger) | resource |
| [google-beta_google_cloudbuild_trigger.deploy-app](https://registry.terraform.io/providers/hashicorp/google-beta/latest/docs/resources/google_cloudbuild_trigger) | resource |
| [google-beta_google_cloudbuild_trigger.deploy-image2png](https://registry.terraform.io/providers/hashicorp/google-beta/latest/docs/resources/google_cloudbuild_trigger) | resource |
| [google_app_engine_application.app](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/app_engine_application) | resource |
| [google_app_engine_domain_mapping.domain_mapping](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/app_engine_domain_mapping) | resource |
| [google_cloud_run_domain_mapping.api](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_domain_mapping) | resource |
| [google_eventarc_trigger.answers-to-image2png](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/eventarc_trigger) | resource |
| [google_eventarc_trigger.archive-to-image2png](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/eventarc_trigger) | resource |
| [google_eventarc_trigger.puzzles-to-image2png](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/eventarc_trigger) | resource |
| [google_firestore_index.puzzles-by-books-and-date](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/firestore_index) | resource |
| [google_firestore_index.puzzles-by-books-and-pub-and-date](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/firestore_index) | resource |
| [google_firestore_index.puzzles-by-date-asc-name-desc](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/firestore_index) | resource |
| [google_firestore_index.puzzles-by-date-desc-name-asc](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/firestore_index) | resource |
| [google_firestore_index.puzzles-by-pub-and-date](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/firestore_index) | resource |
| [google_iap_web_type_app_engine_iam_member.http-resource-accessors](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/iap_web_type_app_engine_iam_member) | resource |
| [google_secret_manager_secret.flask-secret-key](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret) | resource |
| [google_secret_manager_secret.image-reader-key](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret) | resource |
| [google_secret_manager_secret.oauth2-client-secret](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret) | resource |
| [google_secret_manager_secret.wordpress-password](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret) | resource |
| [google_secret_manager_secret_version.image-reader-key](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret_version) | resource |
| [google_service_account_key.image-reader](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/service_account_key) | resource |
| [google_storage_bucket.answers](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket) | resource |
| [google_storage_bucket.archive](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket) | resource |
| [google_storage_bucket.archive-images](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket) | resource |
| [google_storage_bucket.assets](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket) | resource |
| [google_storage_bucket.guide](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket) | resource |
| [google_storage_bucket.images](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket) | resource |
| [google_storage_bucket.puzzles](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket) | resource |
| [google_storage_bucket.thumbnails](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket) | resource |
| [google_storage_bucket.wordpress](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket) | resource |
| [google_storage_bucket_iam_member.archive-image-reader](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket_iam_member) | resource |
| [google_storage_bucket_iam_member.archive-images-image-reader](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket_iam_member) | resource |
| [google_storage_bucket_iam_member.assets-admin-service](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket_iam_member) | resource |
| [google_storage_bucket_iam_member.assets-image-reader](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket_iam_member) | resource |
| [google_storage_bucket_iam_member.images-admin-service](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket_iam_member) | resource |
| [google_storage_bucket_iam_member.images-api-service](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket_iam_member) | resource |
| [google_storage_bucket_iam_member.images-image-reader](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket_iam_member) | resource |
| [google_storage_bucket_iam_member.thumbnails-image-reader](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket_iam_member) | resource |
| [google_cloud_run_service.api](https://registry.terraform.io/providers/hashicorp/google/latest/docs/data-sources/cloud_run_service) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_api_domain_name"></a> [api\_domain\_name](#input\_api\_domain\_name) | n/a | `any` | n/a | yes |
| <a name="input_app"></a> [app](#input\_app) | n/a | `any` | n/a | yes |
| <a name="input_billing_account"></a> [billing\_account](#input\_billing\_account) | n/a | `any` | n/a | yes |
| <a name="input_branch"></a> [branch](#input\_branch) | n/a | `any` | n/a | yes |
| <a name="input_domain_name"></a> [domain\_name](#input\_domain\_name) | n/a | `any` | n/a | yes |
| <a name="input_folder_id"></a> [folder\_id](#input\_folder\_id) | n/a | `any` | n/a | yes |
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | n/a | `any` | n/a | yes |
| <a name="input_project_name"></a> [project\_name](#input\_project\_name) | n/a | `any` | n/a | yes |
| <a name="input_region"></a> [region](#input\_region) | n/a | `any` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_project_id"></a> [project\_id](#output\_project\_id) | n/a |
| <a name="output_project_number"></a> [project\_number](#output\_project\_number) | n/a |
<!-- END_TF_DOCS -->
