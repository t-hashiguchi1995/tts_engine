#!/usr/bin/env bash
# Register bootstrap outputs to GitHub Actions (requires gh CLI + repo admin).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BOOTSTRAP="${ROOT}/terraform/bootstrap"

cd "${BOOTSTRAP}"
terraform output -json github_actions_secrets > /tmp/tts-gh-secrets.json
terraform output -json github_actions_variables > /tmp/tts-gh-vars.json

PROJECT_ID="$(jq -r '.PROJECT_ID' /tmp/tts-gh-secrets.json)"
WIF_PROVIDER="$(jq -r '.WIF_PROVIDER' /tmp/tts-gh-secrets.json)"
WIF_SA_PLAN="$(jq -r '.WIF_SA_PLAN' /tmp/tts-gh-secrets.json)"
WIF_SA_DEPLOY="$(jq -r '.WIF_SA_DEPLOY' /tmp/tts-gh-secrets.json)"
TF_STATE_BUCKET="$(jq -r '.TF_STATE_BUCKET' /tmp/tts-gh-secrets.json)"
GCP_REGION="$(jq -r '.GCP_REGION' /tmp/tts-gh-vars.json)"
APP_NAME="$(jq -r '.APP_NAME' /tmp/tts-gh-vars.json)"

gh secret set PROJECT_ID --body "${PROJECT_ID}"
gh secret set WIF_PROVIDER --body "${WIF_PROVIDER}"
gh secret set WIF_SA_PLAN --body "${WIF_SA_PLAN}"
gh secret set WIF_SA_DEPLOY --body "${WIF_SA_DEPLOY}"
gh secret set TF_STATE_BUCKET --body "${TF_STATE_BUCKET}"

gh variable set GCP_REGION --body "${GCP_REGION}"
gh variable set APP_NAME --body "${APP_NAME}"

echo "GitHub Secrets/Variables updated for $(gh repo view --json nameWithOwner -q .nameWithOwner)"
