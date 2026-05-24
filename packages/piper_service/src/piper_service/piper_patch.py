"""Compatibility patch for piper-plus 1.12.0 speaker_embedding ONNX inputs."""

from __future__ import annotations

from typing import Any

import numpy as np


def apply_piper_speaker_embedding_patch(voice: Any) -> None:
    """Inject zero speaker embeddings for models that declare the ONNX inputs."""
    session = voice.session
    input_names = {inp.name for inp in session.get_inputs()}
    if "speaker_embedding" not in input_names:
        return

    original_run = session.run

    def run_with_embeddings(output_names: list[str], args: dict[str, Any]) -> list[Any]:
        if "speaker_embedding" not in args:
            emb_dim = 256
            for inp in session.get_inputs():
                if inp.name == "speaker_embedding":
                    if len(inp.shape) >= 2 and isinstance(inp.shape[1], int):
                        emb_dim = inp.shape[1]
                    break
            args = dict(args)
            args["speaker_embedding"] = np.zeros((1, emb_dim), dtype=np.float32)
            args["speaker_embedding_mask"] = np.array([[0]], dtype=np.int64)
        return original_run(output_names, args)

    session.run = run_with_embeddings  # type: ignore[method-assign]
