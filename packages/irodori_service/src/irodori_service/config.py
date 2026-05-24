from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    base_hf_repo: str
    voice_design_hf_repo: str
    codec_repo: str
    model_device: str
    codec_device: str
    model_precision: str
    codec_precision: str
    max_ref_bytes: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8080")),
            base_hf_repo=os.getenv(
                "IRODORI_BASE_HF_REPO", "Aratako/Irodori-TTS-500M-v2"
            ),
            voice_design_hf_repo=os.getenv(
                "IRODORI_VOICE_DESIGN_HF_REPO",
                "Aratako/Irodori-TTS-500M-v2-VoiceDesign",
            ),
            codec_repo=os.getenv(
                "IRODORI_CODEC_REPO", "Aratako/Semantic-DACVAE-Japanese-32dim"
            ),
            model_device=os.getenv("IRODORI_MODEL_DEVICE", "auto"),
            codec_device=os.getenv("IRODORI_CODEC_DEVICE", "auto"),
            model_precision=os.getenv("IRODORI_MODEL_PRECISION", "fp32"),
            codec_precision=os.getenv("IRODORI_CODEC_PRECISION", "fp32"),
            max_ref_bytes=int(os.getenv("IRODORI_MAX_REF_BYTES", str(10 * 1024 * 1024))),
        )
