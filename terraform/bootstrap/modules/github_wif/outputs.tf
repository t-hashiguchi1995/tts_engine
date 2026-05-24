output "wif_provider" {
  description = "Workload Identity Pool Provider resource name (GitHub Secret: WIF_PROVIDER)"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "plan_sa_email" {
  description = "Terraform plan SA email (GitHub Secret: WIF_SA_PLAN)"
  value       = google_service_account.plan.email
}

output "deploy_sa_email" {
  description = "Deploy SA email (GitHub Secret: WIF_SA_DEPLOY)"
  value       = google_service_account.deploy.email
}
