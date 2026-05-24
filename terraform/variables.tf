variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Cloud Run region (GPU availability varies by region)"
  type        = string
  default     = "asia-southeast1"
}

variable "artifact_repo" {
  description = "Artifact Registry repository id for container images"
  type        = string
  default     = "tts-engine"
}

variable "image_prefix" {
  description = "Container image prefix without tag. Defaults to regional Artifact Registry when empty."
  type        = string
  default     = ""
}

variable "image_tag" {
  description = "Container image tag for all three services"
  type        = string
  default     = "latest"
}

variable "piper_model" {
  description = "Default Piper voice model name"
  type        = string
  default     = "ja_JP-tsukuyomi-chan-medium"
}

variable "api_keys" {
  description = "DEV ONLY: comma-separated API keys inlined into Cloud Run env. Prefer api_keys_secret_id + Secret Manager in production."
  type        = string
  default     = ""
  sensitive   = true
}

variable "api_keys_secret_id" {
  description = "Secret Manager secret id for gateway API keys (comma-separated values in the secret body)"
  type        = string
  default     = "tts-api-keys"
}

variable "manage_api_keys_secret" {
  description = "If true, Terraform creates the Secret Manager secret resource (versions are still added manually)"
  type        = bool
  default     = true
}

variable "require_api_keys" {
  description = "Gateway rejects startup if no API keys are configured (fail-closed production mode)"
  type        = bool
  default     = true
}

variable "allow_unauthenticated_gateway" {
  description = "Grant roles/run.invoker to allUsers on tts-gateway (needed for internet clients using Bearer API keys)"
  type        = bool
  default     = true
}

variable "gateway_invoker_members" {
  description = "Additional IAM members with run.invoker on the gateway (used when allow_unauthenticated_gateway=false)"
  type        = list(string)
  default     = []
}

variable "rate_limit_rpm" {
  description = "Per-client-IP requests per minute on /v1/* (0 = disabled)"
  type        = number
  default     = 60
}

variable "max_upload_mb" {
  description = "Maximum multipart upload size in megabytes"
  type        = number
  default     = 25
}

variable "allowed_origins" {
  description = "Comma-separated CORS allowed origins (empty = CORS disabled)"
  type        = string
  default     = ""
}

variable "gateway_max_instances" {
  type    = number
  default = 20
}

variable "piper_max_instances" {
  type    = number
  default = 10
}

variable "irodori_min_instances" {
  description = "Minimum GPU instances (1 recommended for production to avoid multi-minute cold starts)"
  type        = number
  default     = 1
}

variable "irodori_max_instances" {
  type    = number
  default = 3
}

variable "irodori_max_concurrency" {
  description = "Requests per GPU instance (keep 1 for large VRAM footprint per request)"
  type        = number
  default     = 1
}

variable "irodori_cpu" {
  description = "vCPU for Irodori (L4 requires minimum 4; 8 recommended by GCP for GPU inference)"
  type        = number
  default     = 8
}

variable "irodori_memory" {
  description = "Memory for Irodori (L4 requires minimum 16Gi; 32Gi recommended for 500M + DACVAE)"
  type        = string
  default     = "32Gi"
}

variable "irodori_timeout_seconds" {
  description = "Request timeout including HF model download on cold start"
  type        = number
  default     = 600
}

variable "irodori_startup_failure_threshold" {
  type    = number
  default = 60
}

variable "irodori_gpu_type" {
  description = "Cloud Run GPU accelerator. nvidia-l4 is recommended for Irodori-TTS-500M-v2 (24GB VRAM)."
  type        = string
  default     = "nvidia-l4"

  validation {
    condition     = var.irodori_gpu_type == "nvidia-l4"
    error_message = "Irodori-TTS-500M-v2 is validated for NVIDIA L4 on Cloud Run. Other GPU types may work but are untested."
  }
}

variable "irodori_gpu_zonal_redundancy" {
  description = "DISABLED reduces cost; ENABLED improves availability across zones"
  type        = string
  default     = "GPU_ZONAL_REDUNDANCY_DISABLED"

  validation {
    condition = contains(
      ["GPU_ZONAL_REDUNDANCY_DISABLED", "GPU_ZONAL_REDUNDANCY_ENABLED"],
      var.irodori_gpu_zonal_redundancy,
    )
    error_message = "Must be GPU_ZONAL_REDUNDANCY_DISABLED or GPU_ZONAL_REDUNDANCY_ENABLED."
  }
}

variable "irodori_model_precision" {
  description = "PyTorch precision for Irodori diffusion model on CUDA"
  type        = string
  default     = "bf16"

  validation {
    condition     = contains(["bf16", "fp32"], var.irodori_model_precision)
    error_message = "Use bf16 on CUDA L4 for best throughput; fp32 for debugging."
  }
}

variable "irodori_codec_precision" {
  description = "PyTorch precision for DACVAE codec on CUDA"
  type        = string
  default     = "bf16"
}

variable "hf_token_secret_id" {
  description = "Optional Secret Manager secret id for HF_TOKEN (e.g. hf-token). Empty = no secret."
  type        = string
  default     = ""
}
