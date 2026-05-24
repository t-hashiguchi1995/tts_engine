from __future__ import annotations

from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator


class Engine(StrEnum):
    PIPER = "piper"
    IRODORI = "irodori"


class IrodoriVariant(StrEnum):
    BASE = "base"
    VOICE_DESIGN = "voice_design"


class AudioFormat(StrEnum):
    WAV = "wav"


class PiperOptions(BaseModel):
    language: str | None = Field(default=None, description="Language code (e.g. ja, en)")
    speaker_id: int | None = None
    length_scale: float | None = Field(default=None, ge=0.1, le=3.0)
    noise_scale: float | None = Field(default=None, ge=0.0, le=2.0)
    noise_scale_w: float | None = Field(default=None, ge=0.0, le=2.0)


class IrodoriOptions(BaseModel):
    irodori_variant: IrodoriVariant = IrodoriVariant.BASE
    caption: str | None = None
    no_ref: bool = False
    num_steps: int = Field(default=40, ge=1, le=200)
    seed: int | None = None
    cfg_scale_text: float = Field(default=3.0, ge=0.0)
    cfg_scale_caption: float = Field(default=3.0, ge=0.0)
    cfg_scale_speaker: float = Field(default=5.0, ge=0.0)


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    engine: Engine
    format: AudioFormat = AudioFormat.WAV
    piper: PiperOptions | None = None
    irodori: IrodoriOptions | None = None

    @model_validator(mode="after")
    def validate_engine_options(self) -> Self:
        if self.engine == Engine.PIPER:
            if self.irodori is not None:
                raise ValueError("irodori options are not valid when engine=piper")
            if self.piper is None:
                self.piper = PiperOptions()
            return self
        if self.piper is not None:
            raise ValueError("piper options are not valid when engine=irodori")
        opts = self.irodori or IrodoriOptions()
        if opts.irodori_variant == IrodoriVariant.VOICE_DESIGN:
            if not opts.caption or not opts.caption.strip():
                raise ValueError("caption is required for irodori_variant=voice_design")
        self.irodori = opts
        return self


class EngineInfo(BaseModel):
    id: Engine
    description: str
    variants: list[str] | None = None


class EnginesResponse(BaseModel):
    engines: list[EngineInfo]


class ServiceHealth(BaseModel):
    status: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    gateway: ServiceHealth
    backends: dict[str, ServiceHealth]
    details: dict[str, Any] | None = None
