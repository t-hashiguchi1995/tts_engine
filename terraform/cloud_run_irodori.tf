# Irodori-TTS-500M-v2: Flow Matching + DACVAE on GPU.
# Cloud Run L4 (24GB VRAM) with 8 vCPU / 32GiB matches GCP guidance for GPU inference
# and comfortably fits the 500M checkpoint + codec on a single GPU.
resource "google_cloud_run_v2_service" "irodori" {
  name                = local.service_names.irodori
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = false

  template {
    service_account                  = google_service_account.irodori.email
    execution_environment            = "EXECUTION_ENVIRONMENT_GEN2"
    timeout                          = "${var.irodori_timeout_seconds}s"
    max_instance_request_concurrency = var.irodori_max_concurrency

    scaling {
      min_instance_count = var.irodori_min_instances
      max_instance_count = var.irodori_max_instances
    }

    node_selector {
      accelerator = var.irodori_gpu_type
    }

    gpu_zonal_redundancy_disabled = var.irodori_gpu_zonal_redundancy == "GPU_ZONAL_REDUNDANCY_DISABLED"

    containers {
      image = local.images.irodori
      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu              = tostring(var.irodori_cpu)
          memory           = var.irodori_memory
          "nvidia.com/gpu" = "1"
        }
      }

      env {
        name  = "IRODORI_MODEL_DEVICE"
        value = "cuda"
      }
      env {
        name  = "IRODORI_CODEC_DEVICE"
        value = "cuda"
      }
      env {
        name  = "IRODORI_MODEL_PRECISION"
        value = var.irodori_model_precision
      }
      env {
        name  = "IRODORI_CODEC_PRECISION"
        value = var.irodori_codec_precision
      }
      env {
        name  = "HF_HOME"
        value = "/tmp/huggingface"
      }

      dynamic "env" {
        for_each = local.irodori_hf_token_set ? { HF_TOKEN = var.hf_token_secret_id } : {}
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        failure_threshold     = var.irodori_startup_failure_threshold
        period_seconds        = 10
        initial_delay_seconds = 30
        timeout_seconds       = 10
      }
    }

    annotations = merge(
      {
        "run.googleapis.com/cpu-throttling"    = "false"
        "run.googleapis.com/startup-cpu-boost" = "true"
      },
      var.irodori_gpu_zonal_redundancy == "GPU_ZONAL_REDUNDANCY_DISABLED" ? {
        "run.googleapis.com/gpu-zonal-redundancy" = "false"
      } : {}
    )
  }

  depends_on = [
    google_project_service.required,
    google_artifact_registry_repository.tts,
  ]

  lifecycle {
    ignore_changes = [
      client,
      client_version,
    ]
  }
}
