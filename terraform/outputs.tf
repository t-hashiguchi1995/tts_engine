output "gateway_url" {
  description = "Public URL of the TTS API gateway"
  value       = google_cloud_run_v2_service.gateway.uri
}

output "piper_url" {
  description = "Internal URL of the Piper backend (requires IAM)"
  value       = google_cloud_run_v2_service.piper.uri
}

output "irodori_url" {
  description = "Internal URL of the Irodori backend (requires IAM)"
  value       = google_cloud_run_v2_service.irodori.uri
}

output "gateway_service_account" {
  value = google_service_account.gateway.email
}

output "piper_service_account" {
  value = google_service_account.piper.email
}

output "irodori_service_account" {
  value = google_service_account.irodori.email
}
