"""
Benchmark & Pipeline for Proper Polyphonic Transcription,
Authentic Karplus-Strong Acoustic Timbre, and Music-Aligned Singing TTS.
"""

import os
import sys
import json
import numpy as np
import soundfile as sf

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
sys.path.insert(0, BASE_DIR)

from polyphonic_transcriber import transcribe_polyphonic_stem
from singing_tts_engine import synthesize_aligned_singing_track
from synthetic_recreation import recreate_synthetic_layer, recreate_full_synthetic_song
from accuracy_evaluator import evaluate_layer_fidelity, evaluate_song_accuracy

def main():
    print("=====================================================================")
    print("🎸 RUNNING PROPER ACOUSTIC TIMBRE & ALIGNED SINGING TTS PIPELINE")
    print("=====================================================================")

    # 1. Polyphonic Audio-to-MIDI Transcription for Acoustic Guitar
    guitar_wav = os.path.join(AUDIO_DIR, "acoustic_guitar.wav")
    if os.path.exists(guitar_wav):
        print("\n[1/4] Running High-Resolution Polyphonic Transcription on acoustic_guitar.wav...")
        guitar_notes = transcribe_polyphonic_stem(guitar_wav, instrument_type="acoustic_guitar")
        guitar_notes_file = os.path.join(AUDIO_DIR, "acoustic_guitar_notes.json")
        with open(guitar_notes_file, 'w', encoding='utf-8') as f:
            json.dump(guitar_notes, f, indent=2)
        print(f"  ✔ Extracted {len(guitar_notes)} polyphonic note events (First note: {guitar_notes[0]['note']} at {guitar_notes[0]['start']}s, vel={guitar_notes[0]['velocity']})")

    # 2. Authentic Karplus-Strong Acoustic Guitar Synthesis
    print("\n[2/4] Synthesizing Acoustic Guitar via Karplus-Strong Physical String Model...")
    guitar_synth_out = os.path.join(AUDIO_DIR, "synthetic", "synth_acoustic_guitar_+0.wav")
    _, g_audio = recreate_synthetic_layer("acoustic_guitar", AUDIO_DIR, guitar_synth_out, transpose_semitones=0)
    print(f"  ✔ Generated Physical Guitar Audio: {len(g_audio)/22050:.1f}s | Peak: {np.max(np.abs(g_audio)):.3f}")

    # 3. Music-Aligned Singing TTS
    lyrics_file = os.path.join(AUDIO_DIR, "lyrics.json")
    vocal_notes_file = os.path.join(AUDIO_DIR, "vocal_notes.json")
    vox_synth_out = os.path.join(AUDIO_DIR, "synthetic", "synth_vocals_+0.wav")
    print("\n[3/4] Synthesizing Music-Aligned Singing Vocal (Time-Warped & Note-Tuned)...")
    _, v_audio = synthesize_aligned_singing_track(lyrics_file, vocal_notes_file, vox_synth_out, total_duration_sec=90.0)
    print(f"  ✔ Generated Aligned Singing Vocal: {len(v_audio)/22050:.1f}s | Peak: {np.max(np.abs(v_audio)):.3f}")

    # 4. Master Synthetic Recreation
    manifest_path = os.path.join(AUDIO_DIR, "song_manifest.json")
    master_synth_out = os.path.join(AUDIO_DIR, "synthetic", "master_synthetic_recreation_+0.wav")
    print("\n[4/4] Assembling Master Synthetic Recreation Song...")
    _, num_layers = recreate_full_synthetic_song(manifest_path, AUDIO_DIR, master_synth_out, transpose_semitones=0)
    master_info = sf.info(master_synth_out)
    master_data, _ = sf.read(master_synth_out)
    print(f"  ✔ Master Synthetic Track Assembled: {master_info.duration:.1f}s | Peak: {np.max(np.abs(master_data)):.4f} (<= 0.92 limit)")

    # 5. Accuracy Measurement
    print("\n[5/5] Measuring Objective Accuracy Benchmark...")
    guitar_eval = evaluate_layer_fidelity(guitar_wav, guitar_synth_out)
    print(f"  📊 Physical Acoustic Guitar Fidelity Score: {guitar_eval.get('fidelity_score')}%")
    print(f"     - Harmonic Chromagram Similarity: {guitar_eval['metrics']['chroma_similarity']}%")
    print(f"     - Dynamic Envelope Correlation: {guitar_eval['metrics']['energy_correlation']}%")
    print(f"     - Raw Pitch Accuracy (within 50¢): {guitar_eval['metrics']['raw_pitch_accuracy_rpa']}%")
    print(f"     - Octave Chroma Accuracy: {guitar_eval['metrics']['octave_chroma_accuracy_rca']}%")

    vox_wav = os.path.join(AUDIO_DIR, "vocals.wav")
    if os.path.exists(vox_wav):
        vox_eval = evaluate_layer_fidelity(vox_wav, vox_synth_out)
        print(f"\n  📊 Aligned Singing Vocal Fidelity Score: {vox_eval.get('fidelity_score')}%")
        print(f"     - Harmonic Chromagram Similarity: {vox_eval['metrics']['chroma_similarity']}%")
        print(f"     - Dynamic Envelope Correlation: {vox_eval['metrics']['energy_correlation']}%")

    overall = evaluate_song_accuracy(AUDIO_DIR, manifest_path)
    print(f"\n🎯 OVERALL MUSIC UNDERSTANDING SCORE: {overall.get('overall_fidelity_score')}%")
    print("=====================================================================")
    print("🎉 PROPER ACOUSTIC & SINGING PIPELINE COMPLETED SUCCESSFULLY!")
    print("=====================================================================")

if __name__ == "__main__":
    main()
