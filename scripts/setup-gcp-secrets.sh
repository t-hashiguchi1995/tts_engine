#!/usr/bin/env bash
# Create Secret Manager secrets for tts_engine (run once per GCP project).
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-asia-northeast1}"
API_KEYS_SECRET="${API_KEYS_SECRET:-tts-api-keys}"
HF_SECRET="${HF_SECRET:-hf-token}"

usage() {
  echo "Usage: PROJECT_ID=your-project $0 [--api-keys-file path] [--hf-token-file path]"
  echo "  Or pipe keys: echo -n 'key1,key2' | PROJECT_ID=... $0 --api-keys-stdin"
  exit 1
}

[[ -n "${PROJECT_ID}" ]] || usage

gcloud config set project "${PROJECT_ID}" >/dev/null

enable_apis() {
  gcloud services enable secretmanager.googleapis.com --project="${PROJECT_ID}"
}

create_secret_if_missing() {
  local name="$1"
  if gcloud secrets describe "${name}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "Secret ${name} already exists"
  else
    gcloud secrets create "${name}" \
      --project="${PROJECT_ID}" \
      --replication-policy="automatic"
    echo "Created secret ${name}"
  fi
}

add_api_keys() {
  if [[ "${1:-}" == "--api-keys-stdin" ]]; then
    gcloud secrets versions add "${API_KEYS_SECRET}" \
      --project="${PROJECT_ID}" \
      --data-file=-
    return
  fi
  local file="${1:-}"
  [[ -n "${file}" && -f "${file}" ]] || {
    echo "Provide --api-keys-file with comma-separated keys (no newlines in file)." >&2
    exit 1
  }
  gcloud secrets versions add "${API_KEYS_SECRET}" \
    --project="${PROJECT_ID}" \
    --data-file="${file}"
}

add_hf_token() {
  local file="$1"
  [[ -f "${file}" ]] || {
    echo "HF token file not found: ${file}" >&2
    exit 1
  }
  gcloud secrets versions add "${HF_SECRET}" \
    --project="${PROJECT_ID}" \
    --data-file="${file}"
}

enable_apis
create_secret_if_missing "${API_KEYS_SECRET}"
create_secret_if_missing "${HF_SECRET}"

API_KEYS_FILE=""
HF_FILE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-keys-file)
      API_KEYS_FILE="$2"
      shift 2
      ;;
    --api-keys-stdin)
      add_api_keys --api-keys-stdin
      shift
      ;;
    --hf-token-file)
      HF_FILE="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

if [[ -n "${API_KEYS_FILE}" ]]; then
  add_api_keys "${API_KEYS_FILE}"
fi
if [[ -n "${HF_FILE}" ]]; then
  add_hf_token "${HF_FILE}"
fi

cat <<EOF

Next steps:
  1. GitHub Variable: HF_TOKEN_SECRET_ID=${HF_SECRET}
  2. Terraform: api_keys_secret_id = "${API_KEYS_SECRET}", require_api_keys = true
  3. terraform apply

Verify:
  gcloud secrets versions access latest --secret=${API_KEYS_SECRET} --project=${PROJECT_ID} | wc -c

EOF
