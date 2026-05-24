#!/usr/bin/env bash
# Download Piper voice model into a local directory (for image bake or GCS upload).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_NAME="${PIPER_MODEL:-ja_JP-tsukuyomi-chan-medium}"
OUT_DIR="${PIPER_MODELS_DIR:-${ROOT}/models/piper}"

mkdir -p "${OUT_DIR}"

if command -v uv >/dev/null 2>&1; then
  cd "${ROOT}"
  uv run --package tts-piper-service python - <<'PY'
import os
from pathlib import Path
from piper.download import download_model

name = os.environ.get("PIPER_MODEL", "ja_JP-tsukuyomi-chan-medium")
out = Path(os.environ.get("PIPER_MODELS_DIR", "models/piper"))
out.mkdir(parents=True, exist_ok=True)
onnx, cfg = download_model(name, out)
print(f"Downloaded Piper model: {onnx}")
PY
else
  python3 -m pip install -q piper-plus onnxruntime soundfile
  PIPER_MODEL="${MODEL_NAME}" PIPER_MODELS_DIR="${OUT_DIR}" python3 - <<'PY'
import os
from pathlib import Path
from piper.download import download_model

name = os.environ["PIPER_MODEL"]
out = Path(os.environ["PIPER_MODELS_DIR"])
out.mkdir(parents=True, exist_ok=True)
onnx, _ = download_model(name, out)
print(f"Downloaded Piper model: {onnx}")
PY
fi

echo "Piper models ready under ${OUT_DIR}"
