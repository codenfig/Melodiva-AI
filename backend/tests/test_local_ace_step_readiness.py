"""Local ACE-Step engine readiness must not claim a missing service is ready."""
from full_song import _engine_command, _local_ace_step_ready, engine_status


def test_ace_step_disabled_by_default(monkeypatch):
    monkeypatch.delenv("FULL_SONG_VOCAL_EXECUTABLE", raising=False)
    monkeypatch.delenv("MELODIVA_ENABLE_ACESTEP", raising=False)
    assert _engine_command("full_song") is None


def test_missing_ace_step_server_not_ready(monkeypatch):
    monkeypatch.delenv("FULL_SONG_VOCAL_EXECUTABLE", raising=False)
    monkeypatch.setenv("MELODIVA_ENABLE_ACESTEP", "1")
    monkeypatch.setenv("ACESTEP_BASE_URL", "http://127.0.0.1:1")
    assert _engine_command("full_song") is None


def test_auto_discovery_rejects_remote_service(monkeypatch):
    monkeypatch.setenv("ACESTEP_BASE_URL", "https://remote.example")
    assert _local_ace_step_ready() is False


def test_full_song_status_is_distinct_from_vocal_stems(monkeypatch):
    monkeypatch.delenv("FULL_SONG_ENGINE_EXECUTABLE", raising=False)
    monkeypatch.delenv("FULL_SONG_VOCAL_EXECUTABLE", raising=False)
    monkeypatch.delenv("MELODIVA_ENABLE_ACESTEP", raising=False)
    status = engine_status()
    assert status["capabilities"]["full_song"] is False
    assert status["capabilities"]["vocals"] is False


def test_instrumental_ace_step_opt_in(monkeypatch):
    from pathlib import Path
    monkeypatch.delenv("FULL_SONG_ENGINE_EXECUTABLE", raising=False)
    monkeypatch.setenv("MELODIVA_ENABLE_ACESTEP", "1")
    monkeypatch.setattr("full_song._local_ace_step_ready", lambda: True)
    executable = _engine_command("instrumental")
    assert executable is not None
    assert Path(executable).name == "run_ace_step_gpu.sh"
