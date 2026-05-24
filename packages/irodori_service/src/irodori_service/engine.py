from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from threading import Lock

from huggingface_hub import hf_hub_download
import soundfile as sf

from irodori_service._vendor import ensure_irodori_path

ensure_irodori_path()

from irodori_tts.inference_runtime import (
    InferenceRuntime,
    RuntimeKey,
    SamplingRequest,
    default_runtime_device,
    list_available_runtime_precisions,
)

from irodori_service.config import Settings

_LOGGER = logging.getLogger(__name__)


def _resolve_device(requested: str) -> str:
    if requested == "auto":
        return default_runtime_device()
    return requested


def _resolve_precision(requested: str, device: str) -> str:
    import torch

    dev = torch.device(_resolve_device(device) if device != "auto" else _resolve_device("auto"))
    available = list_available_runtime_precisions(dev)
    if requested in available:
        return requested
    return available[0]


class IrodoriEngine:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._runtimes: dict[str, InferenceRuntime] = {}
        self._checkpoint_paths: dict[str, str] = {}
        self._lock = Lock()

    def _variant_repo(self, variant: str) -> str:
        if variant == "voice_design":
            return self._settings.voice_design_hf_repo
        return self._settings.base_hf_repo

    def _resolve_checkpoint(self, variant: str) -> str:
        if variant in self._checkpoint_paths:
            return self._checkpoint_paths[variant]
        repo_id = self._variant_repo(variant)
        path = hf_hub_download(repo_id=repo_id, filename="model.safetensors")
        self._checkpoint_paths[variant] = str(path)
        _LOGGER.info("Resolved checkpoint for %s: %s", variant, path)
        return str(path)

    def get_runtime(self, variant: str) -> InferenceRuntime:
        with self._lock:
            if variant in self._runtimes:
                return self._runtimes[variant]
        checkpoint = self._resolve_checkpoint(variant)
        model_device = _resolve_device(self._settings.model_device)
        codec_device = _resolve_device(self._settings.codec_device)
        model_precision = _resolve_precision(self._settings.model_precision, model_device)
        codec_precision = _resolve_precision(self._settings.codec_precision, codec_device)
        key = RuntimeKey(
            checkpoint=checkpoint,
            model_device=model_device,
            codec_repo=self._settings.codec_repo,
            model_precision=model_precision,
            codec_device=codec_device,
            codec_precision=codec_precision,
        )
        _LOGGER.info("Loading Irodori runtime variant=%s device=%s", variant, model_device)
        runtime = InferenceRuntime.from_key(key)
        with self._lock:
            self._runtimes[variant] = runtime
        return runtime

    def is_variant_ready(self, variant: str) -> bool:
        return variant in self._runtimes

    def synthesize_wav(
        self,
        *,
        variant: str,
        text: str,
        caption: str | None = None,
        ref_wav_path: str | None = None,
        no_ref: bool = False,
        num_steps: int = 40,
        seed: int | None = None,
        cfg_scale_text: float = 3.0,
        cfg_scale_caption: float = 3.0,
        cfg_scale_speaker: float = 5.0,
    ) -> tuple[bytes, dict]:
        runtime = self.get_runtime(variant)
        req = SamplingRequest(
            text=text,
            caption=caption,
            ref_wav=ref_wav_path,
            no_ref=no_ref,
            num_steps=num_steps,
            seed=seed,
            cfg_scale_text=cfg_scale_text,
            cfg_scale_caption=cfg_scale_caption,
            cfg_scale_speaker=cfg_scale_speaker,
        )
        result = runtime.synthesize(req)
        buffer = io.BytesIO()
        sf.write(
            buffer,
            result.audio.squeeze(0).cpu().numpy(),
            result.sample_rate,
            format="WAV",
        )
        buffer.seek(0)
        meta = {
            "used_seed": result.used_seed,
            "sample_rate": result.sample_rate,
            "stage_timings": result.stage_timings,
            "messages": result.messages,
        }
        return buffer.getvalue(), meta

    @staticmethod
    def write_ref_audio(content: bytes, suffix: str) -> str:
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            tmp.write(content)
            tmp.flush()
            return tmp.name
        finally:
            tmp.close()

    @staticmethod
    def cleanup_ref(path: str | None) -> None:
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass
