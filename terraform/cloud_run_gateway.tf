resource "google_cloud_run_v2_service" "gateway" {
  name                = local.service_names.gateway
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account                  = google_service_account.gateway.email
    timeout                          = "600s"
    max_instance_request_concurrency = 80

    scaling {
      max_instance_count = var.gateway_max_instances
    }

    containers {
      image = local.images.gateway
      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "PIPER_SERVICE_URL"
        value = google_cloud_run_v2_service.piper.uri
      }
      env {
        name  = "IRODORI_SERVICE_URL"
        value = google_cloud_run_v2_service.irodori.uri
      }
      env {
        name  = "INTERNAL_USE_IAM"
        value = "true"
      }
      env {
        name  = "INTERNAL_IAM_AUDIENCE_PIPER"
        value = google_cloud_run_v2_service.piper.uri
      }
      env {
        name  = "INTERNAL_IAM_AUDIENCE_IRODORI"
        value = google_cloud_run_v2_service.irodori.uri
      }
      env {
        name  = "REQUEST_TIMEOUT"
        value = "600"
      }
      env {
        name  = "REQUIRE_API_KEYS"
        value = tostring(var.require_api_keys)
      }
      env {
        name  = "RATE_LIMIT_RPM"
        value = tostring(var.rate_limit_rpm)
      }
      env {
        name  = "MAX_UPLOAD_MB"
        value = tostring(var.max_upload_mb)
      }
      env {
        name  = "ALLOWED_ORIGINS"
        value = var.allowed_origins
      }

      dynamic "env" {
        for_each = local.api_keys_secret_set ? [1] : []
        content {
          name = "API_KEYS"
          value_source {
            secret_key_ref {
              secret  = var.api_keys_secret_id
              version = "latest"
            }
          }
        }
      }

      dynamic "env" {
        for_each = (!local.api_keys_secret_set && trimspace(var.api_keys) != "") ? [1] : []
        content {
          name  = "API_KEYS"
          value = var.api_keys
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        failure_threshold = 10
        period_seconds    = 5
      }
    }
  }

  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_service.piper,
    google_cloud_run_v2_service.irodori,
    google_cloud_run_v2_service_iam_member.gateway_invokes_piper,
    google_cloud_run_v2_service_iam_member.gateway_invokes_irodori,
  ]
}
