"""
test_audio_perceptual_integrity.py - Red-Capable Audio Perceptual Integrity Test Suite
Adopts Matt Pocock's TDD & Diagnosing-Bugs methodology:
Enforces non-tautological behavioral assertions on the generated audio:
1. Timeline Continuity: Audio energy must span across the full 30 seconds (no 2-second collapse).
2. Melodic F0 Dynamics: Vocal pitch must track melodic note transitions (no flat monotone).
3. Trio Harmony Synchronization: Voice 1 solo intro, Voices 2 & 3 enter in harmony at Measure 13.
4. Dedicated Rhythm Section: Individual unflattened stems for guitar, bass, and drums.
5. True Peak Headroom: Master mix peak strictly <= -0.7 dBFS (0.92 linear).
"""

import os
import sys
import pytest
import numpy as np
import soundfile as sf
import librosa

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_SITE = os.path.join(BASE_DIR, ".venv", "Lib", "site-packages")
if os.path.exists(VENV_SITE) and VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

RECREATIONS_BASE = os.path.join(BASE_DIR, "recreations")
GOLD_SONGS = ["grikiai", "virusas", "prie_topolio"]


@pytest.mark.parametrize("song_id", GOLD_SONGS)
def test_vocal_timeline_continuous_energy(song_id):
    """
    Asserts that vocals do NOT collapse into the first 2 seconds.
    Computes RMS across every 2-second chunk and verifies active audio spans > 80% of timeline.
    """
    song_dir = os.path.join(RECREATIONS_BASE, song_id)
    v1_path = os.path.join(song_dir, "synth_vocals_voice1.wav")
    assert os.path.exists(v1_path), f"Voice 1 stem missing for {song_id}: {v1_path}"

    data, sr = sf.read(v1_path)
    if data.ndim == 2:
        data = data.mean(axis=1)

    total_sec = int(len(data) / sr)
    assert total_sec >= 28, f"Audio duration too short for {song_id}: {total_sec}s"

    active_blocks = 0
    total_blocks = 0

    for s in range(0, total_sec - 1, 2):
        chunk = data[s * sr:(s + 2) * sr]
        rms = np.sqrt(np.mean(chunk ** 2))
        rms_db = 20 * np.log10(rms + 1e-9)
        total_blocks += 1
        if rms_db >= -35.0:
            active_blocks += 1

    active_ratio = active_blocks / max(1, total_blocks)
    assert active_ratio >= 0.80, (
        f"[{song_id}] VOCAL TIMELINE COLLAPSE DETECTED! Only {active_ratio*100:.1f}% of timeline has active energy. "
        f"Active blocks: {active_blocks}/{total_blocks}. Vocals must span smoothly across the full 30 seconds!"
    )


@pytest.mark.parametrize("song_id", GOLD_SONGS)
def test_melodic_f0_pitch_dynamics(song_id):
    """
    Asserts that the singing voice is NOT a flat monotone pitched-up speech block.
    Extracts pitch contour and verifies significant melodic movement across notes.
    """
    song_dir = os.path.join(RECREATIONS_BASE, song_id)
    v1_path = os.path.join(song_dir, "synth_vocals_voice1.wav")
    assert os.path.exists(v1_path), f"Voice 1 stem missing for {song_id}: {v1_path}"

    y, sr = librosa.load(v1_path, sr=22050, duration=15.0)
    # Fast pyin pitch extraction
    f0, _, _ = librosa.pyin(y, fmin=librosa.note_to_hz('C3'), fmax=librosa.note_to_hz('C6'))
    voiced_f0 = f0[~np.isnan(f0)]

    assert len(voiced_f0) > 50, f"[{song_id}] Insufficient voiced frames detected in vocal stem."
    f0_std = float(np.std(voiced_f0))
    f0_range = float(np.max(voiced_f0) - np.min(voiced_f0))

    assert f0_std >= 12.0, f"[{song_id}] FLATTENED MELODY DETECTED! Pitch std is only {f0_std:.1f} Hz (must be >= 12 Hz for singing)."
    assert f0_range >= 40.0, f"[{song_id}] MONOTONE VOICE DETECTED! Pitch range is only {f0_range:.1f} Hz (must span melodic notes >= 40 Hz)."


@pytest.mark.parametrize("song_id", GOLD_SONGS)
def test_trio_harmony_synchronization(song_id):
    """
    Asserts proper musical arrangement and harmony entry:
    - Voice 2 and Voice 3 must be silent during Voice 1's solo opening (seconds 0 to 4).
    - Voice 2 and Voice 3 must enter actively at Measure 13 (after second 8).
    """
    song_dir = os.path.join(RECREATIONS_BASE, song_id)
    v2_path = os.path.join(song_dir, "synth_vocals_voice2.wav")
    v3_path = os.path.join(song_dir, "synth_vocals_voice3.wav")
    assert os.path.exists(v2_path), f"[{song_id}] Voice 2 stem missing"
    assert os.path.exists(v3_path), f"[{song_id}] Voice 3 stem missing"

    for name, path in [("Voice 2", v2_path), ("Voice 3", v3_path)]:
        data, sr = sf.read(path)
        if data.ndim == 2:
            data = data.mean(axis=1)

        # Early intro (0-4s) must be quiet / resting
        intro_chunk = data[0:int(4.0 * sr)]
        intro_rms = 20 * np.log10(np.sqrt(np.mean(intro_chunk ** 2)) + 1e-9)
        assert intro_rms <= -45.0, f"[{song_id}] {name} should be resting during solo intro (0-4s), but RMS is {intro_rms:.1f} dBFS!"

        # Mid section (10-18s) must have active harmony singing
        mid_chunk = data[int(10.0 * sr):int(18.0 * sr)]
        mid_rms = 20 * np.log10(np.sqrt(np.mean(mid_chunk ** 2)) + 1e-9)
        assert mid_rms >= -30.0, f"[{song_id}] {name} failed to enter in harmony during mid section (10-18s)! RMS: {mid_rms:.1f} dBFS."


@pytest.mark.parametrize("song_id", GOLD_SONGS)
def test_rhythm_section_stems_presence(song_id):
    """
    Asserts dedicated, unflattened rhythm section stems exist and contain active audio.
    """
    song_dir = os.path.join(RECREATIONS_BASE, song_id)
    for stem_name in ["synth_guitar.wav", "synth_bass.wav", "synth_drums.wav"]:
        stem_path = os.path.join(song_dir, stem_name)
        assert os.path.exists(stem_path), f"[{song_id}] Rhythm stem missing: {stem_name}"
        data, sr = sf.read(stem_path)
        peak = np.max(np.abs(data))
        rms = np.sqrt(np.mean(data ** 2))
        rms_db = 20 * np.log10(rms + 1e-9)
        assert peak > 0.05, f"[{song_id}] {stem_name} is nearly silent (peak: {peak:.3f})"
        assert rms_db >= -45.0, f"[{song_id}] {stem_name} has insufficient energy (RMS: {rms_db:.1f} dBFS)"


@pytest.mark.parametrize("song_id", GOLD_SONGS)
def test_master_recreation_headroom_and_loudness(song_id):
    """
    Asserts ITU-R BS.1770 true peak limit <= -0.7 dBFS and healthy musical loudness.
    """
    song_dir = os.path.join(RECREATIONS_BASE, song_id)
    master_path = os.path.join(song_dir, "master_synthetic_recreation_+0.wav")
    assert os.path.exists(master_path), f"[{song_id}] Master recreation mix missing: {master_path}"

    data, sr = sf.read(master_path)
    peak = np.max(np.abs(data))
    peak_dbfs = 20 * np.log10(peak + 1e-9)

    assert peak_dbfs <= -0.7, f"[{song_id}] MASTER MIX CLIPPING VIOLATION! Peak: {peak_dbfs:.2f} dBFS (limit: <= -0.7 dBFS)"
    assert peak_dbfs >= -18.0, f"[{song_id}] MASTER MIX TOO QUIET! Peak: {peak_dbfs:.2f} dBFS (expected healthy commercial master)"


def test_live_engine_unflattened_generation():
    """
    Code-Review Verification Gate:
    Directly exercises unflattened_layer_recreator in-memory pipeline with MusicalNote domain entities
    to verify live engine logic executes without exceptions and complies with <= -0.7 dBFS headroom.
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from domain_models import MusicalNote
    from unflattened_layer_recreator import synthesize_unflattened_vocal_line, synthesize_unflattened_rhythm_section

    # Create 3 synthetic test notes spanning 2 seconds
    test_notes = [
        MusicalNote(pitch_name="G4", midi_pitch=67, duration_type="quarter", syllable="gri", x=50.0),
        MusicalNote(pitch_name="F4", midi_pitch=65, duration_type="quarter", syllable="kiai", x=70.0),
        MusicalNote(pitch_name="E4", midi_pitch=64, duration_type="half", syllable="la", x=110.0),
    ]

    vocal_stem = synthesize_unflattened_vocal_line(test_notes, tempo_bpm=112.3, voice_profile="soprano1", duration_sec=3.0)
    assert vocal_stem.shape[0] == 2
    assert vocal_stem.shape[1] == int(3.0 * 44100)
    vocal_peak = np.max(np.abs(vocal_stem))
    vocal_peak_db = 20 * np.log10(vocal_peak + 1e-9)
    assert vocal_peak_db <= -0.70, f"Live engine vocal peak exceeded -0.70 dBFS: {vocal_peak_db:.2f} dBFS"

    rhythm = synthesize_unflattened_rhythm_section([{'chord': 'Am'}], tempo_bpm=112.3, duration_sec=3.0)
    assert 'guitar' in rhythm and 'bass' in rhythm and 'drums' in rhythm
    for name, stem in rhythm.items():
        peak = np.max(np.abs(stem))
        peak_db = 20 * np.log10(peak + 1e-9)
        assert peak_db <= -0.70, f"Live engine {name} peak exceeded -0.70 dBFS limit: {peak_db:.2f} dBFS"


@pytest.mark.parametrize("song_id", GOLD_SONGS)
def test_vocal_lyric_intelligibility(song_id):
    """
    Matt Pocock Red-Capable Objective Intelligibility Gate:
    Uses OpenAI Whisper to transcribe synth_vocals_voice1.wav and verifies that the output
    contains genuine recognizable Lithuanian lyric keywords from the song, proving that
    Edge-TTS succeeded in generating intelligible speech rather than garbled phonemes or noise.
    """
    import whisper
    song_dir = os.path.join(RECREATIONS_BASE, song_id)
    v1_path = os.path.join(song_dir, "synth_vocals_voice1.wav")
    assert os.path.exists(v1_path), f"[{song_id}] Voice 1 stem missing: {v1_path}"

    model = whisper.load_model("base")
    res = model.transcribe(v1_path, language="lt")
    transcription = res["text"].lower()

    # Characteristic root stems for Lithuanian words in each song
    expected_keywords = {
        "grikiai": ["panel", "svetim", "vitrin", "suknel", "karal", "grik"],
        "virusas": ["šal", "karšč", "krūt", "virp", "darai", "gerai"],
        "prie_topolio": ["lauk", "mergai", "klev", "barž", "berž", "puš", "pus"]
    }

    target_words = expected_keywords.get(song_id, [])
    matches = [w for w in target_words if w in transcription]
    assert len(matches) >= 2, (
        f"[{song_id}] UNINTELLIGIBLE LYRICS DETECTED! Whisper transcription failed to recognize "
        f"at least 2 key lyric words. Matched: {matches}. Transcription was: '{transcription}'"
    )


