#!/usr/bin/env bash
# Smoke test against a running gateway (default http://localhost:8080).
set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080}"
OUT_DIR="${OUT_DIR:-./outputs}"
mkdir -p "${OUT_DIR}"

echo "==> Health"
curl -sf "${GATEWAY_URL}/health" | python3 -m json.tool

echo "==> Engines"
curl -sf "${GATEWAY_URL}/v1/engines" | python3 -m json.tool

echo "==> Piper synthesize"
curl -sf -X POST "${GATEWAY_URL}/v1/tts/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text":"こんにちは。","engine":"piper","format":"wav"}' \
  -o "${OUT_DIR}/piper_smoke.wav"
file "${OUT_DIR}/piper_smoke.wav"

if curl -sf "${GATEWAY_URL}/health" | grep -q '"irodori".*"healthy"'; then
  echo "==> Irodori base (no_ref)"
  curl -sf -X POST "${GATEWAY_URL}/v1/tts/synthesize" \
    -H "Content-Type: application/json" \
    -d '{"text":"今日はいい天気ですね。","engine":"irodori","irodori":{"irodori_variant":"base","no_ref":true}}' \
    -o "${OUT_DIR}/irodori_base_smoke.wav" || true
  file "${OUT_DIR}/irodori_base_smoke.wav" 2>/dev/null || echo "Irodori skipped (not healthy)"
else
  echo "Irodori backend not healthy — skipping irodori tests (start with: docker compose --profile gpu up)"
fi

echo "Smoke test done. Outputs in ${OUT_DIR}"
