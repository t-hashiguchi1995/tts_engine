import pytest
from pydantic import ValidationError

from tts_common.schemas import Engine, IrodoriOptions, IrodoriVariant, SynthesizeRequest


def test_piper_request():
    req = SynthesizeRequest(text="hello", engine=Engine.PIPER)
    assert req.engine == Engine.PIPER
    assert req.piper is not None


def test_irodori_voice_design_requires_caption():
    with pytest.raises(ValidationError):
        SynthesizeRequest(
            text="test",
            engine=Engine.IRODORI,
            irodori=IrodoriOptions(irodori_variant=IrodoriVariant.VOICE_DESIGN),
        )


def test_irodori_voice_design_with_caption():
    req = SynthesizeRequest(
        text="test",
        engine=Engine.IRODORI,
        irodori=IrodoriOptions(
            irodori_variant=IrodoriVariant.VOICE_DESIGN,
            caption="calm female voice",
            no_ref=True,
        ),
    )
    assert req.irodori.caption == "calm female voice"
