resource "google_artifact_registry_repository" "tts" {
  location      = var.region
  repository_id = var.artifact_repo
  description   = "Container images for tts_engine (gateway, piper, irodori)"
  format        = "DOCKER"

  docker_config {
    immutable_tags = false
  }

  vulnerability_scanning_config {
    enablement_config = "INHERITED"
  }

  depends_on = [google_project_service.required]
}
