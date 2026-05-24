resource "google_cloud_run_v2_service" "piper" {
  name                = local.service_names.piper
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = false

  template {
    service_account                  = google_service_account.piper.email
    timeout                          = "300s"
    max_instance_request_concurrency = 4

    scaling {
      max_instance_count = var.piper_max_instances
    }

    containers {
      image = local.images.piper
      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }

      env {
        name  = "PIPER_MODEL"
        value = var.piper_model
      }
      env {
        name  = "PIPER_MODELS_DIR"
        value = "/models/piper"
      }
      env {
        name  = "PIPER_DOWNLOAD_ON_START"
        value = "true"
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        failure_threshold = 30
        period_seconds    = 10
      }
    }

    annotations = {
      "run.googleapis.com/startup-cpu-boost" = "true"
    }
  }

  depends_on = [google_project_service.required]
}
