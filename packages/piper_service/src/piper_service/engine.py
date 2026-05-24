from __future__ import annotations

import io
import logging
import wave
from pathlib import Path
from threading import Lock

from piper import PiperVoice
from piper.download import download_model

from piper_service.config import Settings

_LOGGER = logging.getLogger(__name__)


class PiperEngine:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._voice: PiperVoice | None = None
        self._lock = Lock()
        self._ready = False
        self._model_path: Path | None = None

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def model_path(self) -> Path | None:
        return self._model_path

    def load(self) -> None:
        settings = self._settings
        settings.models_dir.mkdir(parents=True, exist_ok=True)
        if settings.download_on_start:
            onnx_path, _config_path = download_model(
                settings.model_name,
                settings.models_dir,
            )
        else:
            onnx_path = settings.models_dir / f"{settings.model_name}.onnx"
            if not onnx_path.exists():
                for child in settings.models_dir.glob("*.onnx"):
                    onnx_path = child
                    break
            if not onnx_path.exists():
                raise FileNotFoundError(
                    f"Piper model not found under {settings.models_dir}. "
                    "Set PIPER_DOWNLOAD_ON_START=true or mount models."
                )
        _LOGGER.info("Loading Piper model from %s", onnx_path)
        voice = PiperVoice.load(onnx_path, use_cuda=settings.use_cuda)
        with self._lock:
            self._voice = voice
            self._model_path = Path(onnx_path)
            self._ready = True

    def synthesize_wav(
        self,
        text: str,
        *,
        speaker_id: int | None = None,
        length_scale: float | None = None,
        noise_scale: float | None = None,
        noise_scale_w: float | None = None,
        language: str | None = None,
    ) -> bytes:
        if not self._ready or self._voice is None:
            raise RuntimeError("Piper model is not loaded")

        language_id: int | None = None
        if language:
            lang_map = {"ja": 0, "en": 1, "zh": 2, "es": 3, "fr": 4, "pt": 5, "sv": 6, "ko": 7}
            language_id = lang_map.get(language.lower())

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            with self._lock:
                self._voice.synthesize(
                    text,
                    wav_file,
                    speaker_id=speaker_id,
                    length_scale=length_scale,
                    noise_scale=noise_scale,
                    noise_w=noise_scale_w,
                    language_id=language_id,
                )
        return buffer.getvalue()
