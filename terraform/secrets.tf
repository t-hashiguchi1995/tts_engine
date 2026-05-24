# API keys and runtime secrets (values are created outside Terraform — see docs/SECURITY.md).

resource "google_secret_manager_secret" "api_keys" {
  count = var.manage_api_keys_secret ? 1 : 0

  project   = var.project_id
  secret_id = var.api_keys_secret_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_iam_member" "gateway_api_keys" {
  count = local.api_keys_secret_set ? 1 : 0

  project   = var.project_id
  secret_id = var.api_keys_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.gateway.email}"
}
