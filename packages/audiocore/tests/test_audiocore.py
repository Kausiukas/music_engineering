import asyncio
import sys
import types

import numpy as np
import pytest

from audiocore import dsp, pitch, tts
from audiocore.paths import workspace_data_dir


# ---- pitch -----------------------------------------------------------------

def test_midi_hz_reference_points():
    assert pitch.midi_to_hz(69) == 440.0
    assert pitch.midi_to_hz(57) == pytest.approx(220.0)
    assert np.allclose(pitch.midi_to_hz(np.array([60.0, 72.0])), [261.6255653, 523.2511306])


def test_hz_to_midi_rounds_and_defaults():
    assert pitch.hz_to_midi(440.0) == 69
    assert pitch.hz_to_midi(452.0) == 69  # +46 cents still rounds down
    assert pitch.hz_to_midi(0) is None
    assert pitch.hz_to_midi(None, default=60) == 60


def test_hz_to_midi_cents():
    assert pitch.hz_to_midi_cents(440.0) == (69, 0)
    note, cents = pitch.hz_to_midi_cents(pitch.midi_to_hz(60.25))
    assert (note, cents) == (60, 25)
    assert pitch.hz_to_midi_cents(-1) == (None, 0)


def test_round_trip_and_names():
    for m in range(21, 109):
        assert pitch.hz_to_midi(pitch.midi_to_hz(m)) == m
    assert pitch.midi_to_name(60) == "C4"
    assert pitch.midi_to_name(70) == "A#4"
    assert len(pitch.KEY_NAMES) == len(pitch.NOTE_NAMES_SHARP) == 12


# ---- dsp -------------------------------------------------------------------

def inline_limit(x, c=0.92):  # the idiom audiocore.dsp.limit_peak replaced
    peak = np.max(np.abs(x))
    if peak > c:
        x = (x / peak) * c
    return x


def inline_norm(x, t=None):
    peak = np.max(np.abs(x))
    if peak > 0:
        x = x / peak if t is None else x * (t / peak)
    return x


@pytest.mark.parametrize("scale", [0.1, 0.92, 0.95, 3.0])
def test_limit_peak_is_bit_identical_to_inline_idiom(scale):
    x = np.random.default_rng(1).standard_normal((2, 4096)).astype(np.float32) * scale
    assert np.array_equal(dsp.limit_peak(x.copy()), inline_limit(x.copy()))
    assert dsp.sample_peak(dsp.limit_peak(x)) <= dsp.PEAK_CEILING + 1e-7


@pytest.mark.parametrize("target", [None, 0.85, 0.88])
def test_normalize_peak_is_bit_identical_to_inline_idiom(target):
    x = np.random.default_rng(2).standard_normal(4096) * 0.3
    got = dsp.normalize_peak(x.copy()) if target is None else dsp.normalize_peak(x.copy(), target)
    assert np.array_equal(got, inline_norm(x.copy(), target))


def test_silence_passes_through():
    z = np.zeros(128)
    assert dsp.normalize_peak(z) is z and dsp.limit_peak(z) is z


def test_ceiling_meets_minus_0_7_dbfs_rule():
    assert dsp.to_dbfs(dsp.PEAK_CEILING) <= -0.7


def test_true_peak_exceeds_sample_peak_for_intersample_overs():
    sr, f = 48000, 12000.0
    t = np.arange(4800) / sr
    x = np.sin(2 * np.pi * f * t + np.pi / 4)  # samples land at +-0.707, true peak is 1.0
    assert dsp.to_dbfs(dsp.sample_peak(x)) == pytest.approx(-3.01, abs=0.05)
    assert dsp.true_peak_dbfs(x) == pytest.approx(0.0, abs=0.2)


# ---- tts -------------------------------------------------------------------

def test_save_speech_passes_rate_pitch(monkeypatch, tmp_path):
    calls = {}

    class FakeCommunicate:
        def __init__(self, text, voice, rate, pitch):
            calls.update(text=text, voice=voice, rate=rate, pitch=pitch)

        async def save(self, path):
            calls["path"] = path

    monkeypatch.setitem(sys.modules, "edge_tts", types.SimpleNamespace(Communicate=FakeCommunicate))
    out = str(tmp_path / "x.mp3")
    asyncio.run(tts.save_speech("labas", "lt-LT-OnaNeural", out, pitch="+20Hz"))
    assert calls == {"text": "labas", "voice": "lt-LT-OnaNeural", "rate": "+0%", "pitch": "+20Hz", "path": out}


# ---- paths -----------------------------------------------------------------

def test_workspace_data_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIO_LAB_DATA", str(tmp_path))
    assert workspace_data_dir() == tmp_path


def test_workspace_data_dir_found_in_repo(monkeypatch):
    monkeypatch.delenv("AUDIO_LAB_DATA", raising=False)
    found = workspace_data_dir()
    assert found is not None and (found / "README.md").is_file()
