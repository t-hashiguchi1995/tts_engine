variable "project_id" {
  type = string
}

variable "github_repo" {
  description = "GitHub repository in owner/repo form"
  type        = string
}

variable "app_name" {
  description = "Application name used in resource IDs (e.g. tts-engine)"
  type        = string
}
