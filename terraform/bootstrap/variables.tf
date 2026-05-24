variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "asia-northeast1"
}

variable "github_org" {
  type    = string
  default = "t-hashiguchi1995"
}

variable "github_repo" {
  type    = string
  default = "tts_engine"
}

variable "app_name" {
  description = "Artifact Registry repository id and WIF resource prefix (harness template: APP_NAME)"
  type        = string
  default     = "tts-engine"
}

variable "state_bucket_name" {
  description = "GCS bucket for Terraform state. Default: {project_id}-tfstate (template convention)"
  type        = string
  default     = null
}
