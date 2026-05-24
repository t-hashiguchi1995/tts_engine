resource "google_service_account" "gateway" {
  account_id   = local.gateway_sa_id
  display_name = "TTS API Gateway"
  depends_on   = [google_project_service.required]
}

resource "google_service_account" "piper" {
  account_id   = local.piper_sa_id
  display_name = "TTS Piper backend"
  depends_on   = [google_project_service.required]
}

resource "google_service_account" "irodori" {
  account_id   = local.irodori_sa_id
  display_name = "TTS Irodori backend"
  depends_on   = [google_project_service.required]
}

resource "google_cloud_run_v2_service_iam_member" "gateway_invokes_piper" {
  project  = var.project_id
  location = google_cloud_run_v2_service.piper.location
  name     = google_cloud_run_v2_service.piper.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.gateway.email}"
}

resource "google_cloud_run_v2_service_iam_member" "gateway_invokes_irodori" {
  project  = var.project_id
  location = google_cloud_run_v2_service.irodori.location
  name     = google_cloud_run_v2_service.irodori.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.gateway.email}"
}

resource "google_cloud_run_v2_service_iam_member" "gateway_public" {
  count = var.allow_unauthenticated_gateway ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_service.gateway.location
  name     = google_cloud_run_v2_service.gateway.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "gateway_invoker" {
  for_each = toset(var.gateway_invoker_members)

  project  = var.project_id
  location = google_cloud_run_v2_service.gateway.location
  name     = google_cloud_run_v2_service.gateway.name
  role     = "roles/run.invoker"
  member   = each.value
}

resource "google_secret_manager_secret_iam_member" "irodori_hf_token" {
  count = local.irodori_hf_token_set ? 1 : 0

  project   = var.project_id
  secret_id = var.hf_token_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.irodori.email}"
}
