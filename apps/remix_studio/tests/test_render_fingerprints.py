"""Golden render fingerprints: refactors must not change the sound.

Renders fixed inputs (seeded) through every synthesis engine and compares a sha256 of the output
samples with tests/golden/render_fingerprints.json. A mismatch means the audio changed. If the
change is intended (new timbre, dependency bump), listen to it, then regenerate with:

    REMIX_UPDATE_GOLDEN=1 uv run pytest tests/test_render_fingerprints.py
"""
import hashlib
import json
import os

import numpy as np
import pytest
import soundfile as sf

import studio_paths

pytestmark = [pytest.mark.artifact, pytest.mark.slow]

GOLDEN = os.path.join(os.path.dirname(__file__), "golden", "render_fingerprints.json")
A = studio_paths.AUDIO_DIR


def fingerprint(arr):
    return hashlib.sha256(np.ascontiguousarray(np.asarray(arr, dtype=np.float64)).tobytes()).hexdigest()[:16]


def seeded(fn, *a, **k):
    np.random.seed(1234)
    return fn(*a, **k)


@pytest.fixture(scope="module")
def renders(tmp_path_factory):
    for name in ("guitar_notes.json", "bass_notes.json", "vocals_pitch_curve.json", "vocals.wav"):
        if not os.path.exists(os.path.join(A, name)):
            pytest.skip(f"needs ingested song data: {name}")
    notes = json.load(open(os.path.join(A, "guitar_notes.json")))[:40]
    bass_notes = json.load(open(os.path.join(A, "bass_notes.json")))[:40]
    curve = json.load(open(os.path.join(A, "vocals_pitch_curve.json")))
    out = {}

    import acoustic_timbre_engine as ate
    for inst, ns in [("acoustic_guitar", notes), ("piano", notes), ("acoustic_bass", bass_notes)]:
        out[f"timbre_{inst}"] = fingerprint(seeded(ate.render_instrument_notes, ns, inst, 22050, 20.0, 0))

    import synthetic_recreation as sr_
    out["poly_notes"] = fingerprint(seeded(sr_.synthesize_polyphonic_notes, notes, 22050, 20.0, "acoustic_guitar", 2))
    out["pitch_curve"] = fingerprint(seeded(sr_.synthesize_continuous_pitch_stem, curve, 22050, 20.0, "acoustic_guitar", 0))

    from trio_synthetic_recreator import TrioSyntheticRecreator
    trio = TrioSyntheticRecreator(44100)
    vn = [{"pitch": n["pitch"] + 12, "start": n["start"], "end": n["end"]} for n in notes[:20]]
    out["trio_vocal"] = fingerprint(seeded(trio.synthesize_vocal_line, vn, 12.0, "soprano1", 0.0, 0))
    ch = [{"chord": n.get("chord", "C"), "start": n["start"], "end": n["end"]} for n in notes[:20]]
    out["trio_instruments"] = fingerprint(seeded(trio.synthesize_instruments, ch, 12.0, 150.0, 0))

    import jungle_remix_engine as jre
    import multi_genre_engine as mge
    tmp = tmp_path_factory.mktemp("remixes")
    for name, fn in [("techno", mge.render_techno_remix), ("house", mge.render_house_remix), ("jungle", jre.render_jungle_remix)]:
        p = str(tmp / f"{name}.wav")
        seeded(fn, os.path.join(A, "vocals.wav"), p, bars=4)
        out[f"remix_{name}"] = fingerprint(sf.read(p)[0])
    return out


def test_renders_match_golden(renders):
    if os.environ.get("REMIX_UPDATE_GOLDEN"):
        with open(GOLDEN, "w", encoding="utf-8") as f:
            json.dump(renders, f, indent=1, sort_keys=True)
        pytest.skip("golden fingerprints regenerated")
    with open(GOLDEN, encoding="utf-8") as f:
        golden = json.load(f)
    changed = {k: (golden.get(k), v) for k, v in renders.items() if golden.get(k) != v}
    assert not changed, f"audio output changed: {changed}"
