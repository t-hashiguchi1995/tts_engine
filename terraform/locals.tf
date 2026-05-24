locals {
  name_prefix = "tts"

  service_names = {
    gateway = "${local.name_prefix}-gateway"
    piper   = "${local.name_prefix}-piper"
    irodori = "${local.name_prefix}-irodori"
  }

  image_prefix = var.image_prefix != "" ? var.image_prefix : "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repo}"

  images = {
    gateway = "${local.image_prefix}/gateway:${var.image_tag}"
    piper   = "${local.image_prefix}/piper:${var.image_tag}"
    irodori = "${local.image_prefix}/irodori:${var.image_tag}"
  }

  gateway_sa_id = "${local.name_prefix}-gateway"
  piper_sa_id   = "${local.name_prefix}-piper"
  irodori_sa_id = "${local.name_prefix}-irodori"

  irodori_hf_token_set = var.hf_token_secret_id != ""
  api_keys_secret_set  = var.api_keys_secret_id != ""
}
