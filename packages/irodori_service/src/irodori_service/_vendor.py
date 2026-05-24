"""Ensure vendored Irodori-TTS sources are on sys.path."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_irodori_path() -> Path | None:
    candidates = [
        Path(__file__).resolve().parents[4] / "vendor" / "Irodori-TTS",
        Path("/opt/Irodori-TTS"),
        Path("/app/vendor/Irodori-TTS"),
    ]
    for root in candidates:
        pkg = root / "irodori_tts"
        if pkg.is_dir():
            root_str = str(root)
            if root_str not in sys.path:
                sys.path.insert(0, root_str)
            return root
    return None
