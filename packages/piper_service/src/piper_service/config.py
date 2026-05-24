from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    model_name: str
    models_dir: Path
    download_on_start: bool
    use_cuda: bool

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8080")),
            model_name=os.getenv("PIPER_MODEL", "ja_JP-tsukuyomi-chan-medium"),
            models_dir=Path(os.getenv("PIPER_MODELS_DIR", "/models/piper")),
            download_on_start=os.getenv("PIPER_DOWNLOAD_ON_START", "true").lower()
            in ("1", "true", "yes"),
            use_cuda=os.getenv("PIPER_USE_CUDA", "false").lower() in ("1", "true", "yes"),
        )
