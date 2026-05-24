# One-time bootstrap (harness-engineering-template 準拠)
#
#   1. scripts/create-tfstate-bucket.sh   # GCS backend（Terraform 管理外）
#   2. cd terraform/bootstrap && terraform init && terraform apply
#   3. scripts/register-github-secrets.sh  # または GitHub UI で Secrets 登録
#
# 詳細: docs/infrastructure.md

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.30.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "required" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

module "github_wif" {
  source = "./modules/github_wif"

  project_id  = var.project_id
  github_repo = "${var.github_org}/${var.github_repo}"
  app_name    = var.app_name

  depends_on = [google_project_service.required]
}

output "github_actions_secrets" {
  description = "Register in GitHub → Settings → Secrets and variables → Actions"
  value = {
    PROJECT_ID      = var.project_id
    WIF_PROVIDER    = module.github_wif.wif_provider
    WIF_SA_PLAN     = module.github_wif.plan_sa_email
    WIF_SA_DEPLOY   = module.github_wif.deploy_sa_email
    TF_STATE_BUCKET = local.tfstate_bucket
  }
}

output "github_actions_variables" {
  description = "Register in GitHub → Actions → Variables"
  value = {
    GCP_REGION = var.region
    APP_NAME   = var.app_name
  }
}

output "tfstate_bucket" {
  value = local.tfstate_bucket
}

output "artifact_registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${var.app_name}"
}

locals {
  tfstate_bucket = coalesce(var.state_bucket_name, "${var.project_id}-tfstate")
}
