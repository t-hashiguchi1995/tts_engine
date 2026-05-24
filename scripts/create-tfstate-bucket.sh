#!/usr/bin/env bash
# Create Terraform state bucket (harness-engineering-template: manual step, outside Terraform).
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-asia-northeast1}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "Usage: PROJECT_ID=your-project-id [REGION=asia-northeast1] $0" >&2
  exit 1
fi

BUCKET="${PROJECT_ID}-tfstate"

echo "Creating gs://${BUCKET} in ${REGION}..."
gcloud storage buckets create "gs://${BUCKET}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --uniform-bucket-level-access \
  --public-access-prevention

gcloud storage buckets update "gs://${BUCKET}" --versioning

echo "Done. Use TF_STATE_BUCKET=${BUCKET} for terraform init -backend-config."
