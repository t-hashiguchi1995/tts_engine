#!/usr/bin/env bash
# Clone Irodori-TTS v2 into vendor/ (required for irodori_service).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR="${ROOT}/vendor/Irodori-TTS"

if [[ -d "${VENDOR}/irodori_tts" ]]; then
  echo "vendor/Irodori-TTS already present"
  exit 0
fi

mkdir -p "${ROOT}/vendor"
git clone --depth 1 --branch v2 https://github.com/Aratako/Irodori-TTS.git "${VENDOR}"
echo "Cloned Irodori-TTS to ${VENDOR}"
