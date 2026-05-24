# Production security preconditions (fail terraform plan/apply early).

resource "terraform_data" "security_policy" {
  lifecycle {
    precondition {
      condition = (
        !var.require_api_keys
        || local.api_keys_secret_set
        || trimspace(var.api_keys) != ""
      )
      error_message = "require_api_keys=true requires api_keys_secret_id (recommended) or api_keys (dev only)."
    }

    precondition {
      condition = (
        var.allow_unauthenticated_gateway
        || length(var.gateway_invoker_members) > 0
      )
      error_message = "allow_unauthenticated_gateway=false requires gateway_invoker_members (e.g. serviceAccount:..., group:..., user:...)."
    }
  }
}
