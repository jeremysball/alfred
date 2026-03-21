from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIO_MANAGER = PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/audio-manager.js"


def test_audio_manager_exists_and_requires_explicit_start() -> None:
    assert AUDIO_MANAGER.exists(), "audio-manager.js is missing"

    source = AUDIO_MANAGER.read_text()

    assert "class KidcoreAudioManager" in source
    assert "startMusic" in source
    assert "stopMusic" in source
    assert "mute" in source or "setMuted" in source
    assert "playEffect" in source
    assert "autoplay" not in source.lower()


def test_index_includes_kidcore_audio_controls_and_script() -> None:
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/index.html").read_text()

    assert '/static/js/audio-manager.js?v=3' in source
    assert 'kidcore-audio-controls' in source
    assert 'id="kidcore-audio-play"' in source
    assert 'id="kidcore-audio-mute"' in source
