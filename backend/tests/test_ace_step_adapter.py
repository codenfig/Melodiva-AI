"""ACE-Step adapter checks without downloading models or making network requests."""
import wave

import numpy as np
import soundfile as sf
import pytest

from ace_step_adapter import make_payload, normalize_pcm_wav


def test_full_song_payload_includes_lyrics_and_voice():
    project = {
        "output": "full_song", "voice": "female", "genre": "Pop",
        "description": "warm guitar", "lyrics": "[Chorus] Hello",
        "bpm": 110, "minutes": 3,
    }
    payload = make_payload(project)
    assert "female lead singing" in payload["prompt"]
    assert payload["lyrics"] == project["lyrics"]
    assert payload["audio_duration"] == 180


def test_stem_request_is_not_falsely_supported():
    with pytest.raises(ValueError, match="full_song"):
        make_payload({"output": "vocals"})


def test_convert_float_wav_to_pcm16(tmp_path):
    source, destination = tmp_path / "float.wav", tmp_path / "output.wav"
    audio = np.sin(np.linspace(0, 4, 48000, dtype=np.float32))[:, None]
    sf.write(source, audio, 24000, subtype="FLOAT")
    normalize_pcm_wav(source, destination)
    with wave.open(str(destination), "rb") as wav:
        assert wav.getsampwidth() == 2
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 24000
        assert wav.getnframes() == 48000


def test_reject_empty_wav(tmp_path):
    source = tmp_path / "empty.wav"
    sf.write(source, np.empty((0, 1), dtype=np.float32), 24000)
    with pytest.raises(RuntimeError, match="invalid audio"):
        normalize_pcm_wav(source, tmp_path / "output.wav")


def test_instrumental_generation_uses_inst_token():
    payload = make_payload({"output": "instrumental", "description": "bright guitar", "genre": "Pop", "minutes": 2})
    assert payload["lyrics"] == "[inst]"
    assert "instrumental, no vocals" in payload["prompt"]
    assert payload["audio_duration"] == 120


def test_ace_step_generation_controls():
    payload = make_payload({"output": "full_song", "description": "jazz", "lyrics": "hello",
                            "vocal_language": "sw", "key_scale": "C Major", "time_signature": "4/4",
                            "seed": 42, "inference_steps": 12, "guidance_scale": 6.5,
                            "thinking": True, "use_format": True, "model": "acestep-v15-turbo"})
    assert payload["vocal_language"] == "sw"
    assert payload["key_scale"] == "C Major"
    assert payload["time_signature"] == "4/4"
    assert payload["seed"] == 42
    assert payload["inference_steps"] == 12
    assert payload["guidance_scale"] == 6.5
    assert payload["thinking"] is True
    assert payload["use_format"] is True
    assert payload["model"] == "acestep-v15-turbo"


def test_invalid_ace_step_options():
    with pytest.raises(ValueError, match="inference_steps"):
        make_payload({"output": "instrumental", "description": "jazz", "inference_steps": 0})
    with pytest.raises(ValueError, match="vocal language"):
        make_payload({"output": "instrumental", "description": "jazz", "vocal_language": "../../etc"})
