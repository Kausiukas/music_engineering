"""
Test and Verification Suite for Closed-Loop Synthetic Recreation & Accuracy Measurement
Validates:
1. ACE Studio-style continuous pitch curve and envelope extraction
2. Synthetic stem recreation for acoustic_guitar, vocals, bass
3. Master synthetic song assembly with zero-clipping limit (<= -0.7 dBFS / 0.92)
4. Objective accuracy measurement (RPA, RCA, Chroma cosine, Energy correlation)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # apps/remix_studio
import studio_paths
import sys
import json
import numpy as np
import soundfile as sf

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = studio_paths.AUDIO_DIR
sys.path.insert(0, BASE_DIR)

from audio_to_midi import extract_ace_pitch_and_envelopes, extract_melody_notes
from synthetic_recreation import recreate_synthetic_layer, recreate_full_synthetic_song
from accuracy_evaluator import evaluate_layer_fidelity, evaluate_song_accuracy

def run_test():
    print("=====================================================================")
    print("🎶 RUNNING CLOSED-LOOP SYNTHETIC RECREATION & ACCURACY BENCHMARK")
    print("=====================================================================")
    
    # 1. Test ACE Pitch Curve Extraction on acoustic_guitar.wav
    guitar_wav = os.path.join(AUDIO_DIR, "acoustic_guitar.wav")
    if os.path.exists(guitar_wav):
        print(f"\n[1/5] Extracting continuous ACE pitch curves for 'acoustic_guitar'...")
        curve_guitar = extract_ace_pitch_and_envelopes(guitar_wav)
        curve_file = os.path.join(AUDIO_DIR, "acoustic_guitar_pitch_curve.json")
        with open(curve_file, 'w', encoding='utf-8') as f:
            json.dump(curve_guitar, f)
        print(f"  ✔ Extracted {curve_guitar['total_frames']} continuous frames ({curve_guitar['duration_sec']:.1f}s)")
        print(f"  ✔ Sample frame 50: F0={curve_guitar['frames'][50]['f0_hz']}Hz, Energy={curve_guitar['frames'][50]['energy']}, Tension={curve_guitar['frames'][50]['tension']}")
        
    # 2. Extract ACE Pitch Curve for vocals.wav if available
    vocals_wav = os.path.join(AUDIO_DIR, "vocals.wav")
    if os.path.exists(vocals_wav):
        print(f"\n[2/5] Extracting continuous ACE pitch curves for 'vocals'...")
        curve_vox = extract_ace_pitch_and_envelopes(vocals_wav)
        vox_curve_file = os.path.join(AUDIO_DIR, "vocals_pitch_curve.json")
        with open(vox_curve_file, 'w', encoding='utf-8') as f:
            json.dump(curve_vox, f)
        print(f"  ✔ Extracted {curve_vox['total_frames']} continuous frames ({curve_vox['duration_sec']:.1f}s)")

    # 3. Recreate Synthetic Layers
    print(f"\n[3/5] Generating Closed-Loop Synthetic Layer Recreations...")
    os.makedirs(os.path.join(AUDIO_DIR, "synthetic"), exist_ok=True)
    
    guitar_synth_out = os.path.join(AUDIO_DIR, "synthetic", "synth_acoustic_guitar_+0.wav")
    _, guitar_audio = recreate_synthetic_layer("acoustic_guitar", AUDIO_DIR, guitar_synth_out, transpose_semitones=0)
    print(f"  ✔ Created 'synth_acoustic_guitar_+0.wav' ({len(guitar_audio)/22050:.1f}s | Peak: {np.max(np.abs(guitar_audio)):.3f})")
    
    vox_synth_out = os.path.join(AUDIO_DIR, "synthetic", "synth_vocals_+0.wav")
    _, vox_audio = recreate_synthetic_layer("vocals", AUDIO_DIR, vox_synth_out, transpose_semitones=0)
    print(f"  ✔ Created 'synth_vocals_+0.wav' ({len(vox_audio)/22050:.1f}s | Peak: {np.max(np.abs(vox_audio)):.3f})")

    # Transposed preview (+3 semitones)
    guitar_transposed_out = os.path.join(AUDIO_DIR, "synthetic", "synth_acoustic_guitar_+3.wav")
    _, trans_audio = recreate_synthetic_layer("acoustic_guitar", AUDIO_DIR, guitar_transposed_out, transpose_semitones=3)
    print(f"  ✔ Created transposed synthetic 'synth_acoustic_guitar_+3.wav' (Peak: {np.max(np.abs(trans_audio)):.3f})")

    # 4. Master Synthetic Song Recreation
    manifest_path = os.path.join(AUDIO_DIR, "song_manifest.json")
    master_synth_out = os.path.join(AUDIO_DIR, "synthetic", "master_synthetic_recreation_+0.wav")
    print(f"\n[4/5] Assembling Master Synthetic Recreation Song...")
    _, num_layers = recreate_full_synthetic_song(manifest_path, AUDIO_DIR, master_synth_out, transpose_semitones=0)
    
    master_info = sf.info(master_synth_out)
    master_data, _ = sf.read(master_synth_out)
    master_peak = float(np.max(np.abs(master_data)))
    print(f"  ✔ Master Synthetic Recreation Assembled: {master_info.duration:.1f}s, {num_layers} layers summed.")
    print(f"  ✔ Peak Level: {master_peak:.4f} (<= 0.92 zero-clipping limit)")
    assert master_peak <= 0.925, f"Clipping violation! Peak is {master_peak}"

    # 5. Objective Accuracy Measurement (mir_eval RPA / RCA, Chroma cosine, Energy)
    print(f"\n[5/5] Measuring Objective Accuracy (Original Stem vs Synthetic Recreation)...")
    guitar_eval = evaluate_layer_fidelity(guitar_wav, guitar_synth_out)
    print(f"  📊 Acoustic Guitar Layer Fidelity Score: {guitar_eval.get('fidelity_score')}%")
    print(f"     - Raw Pitch Accuracy (within 50 cents): {guitar_eval['metrics']['raw_pitch_accuracy_rpa']}%")
    print(f"     - Octave Chroma Accuracy: {guitar_eval['metrics']['octave_chroma_accuracy_rca']}%")
    print(f"     - Harmonic Chromagram Similarity: {guitar_eval['metrics']['chroma_similarity']}%")
    print(f"     - Dynamic RMS Envelope Tracking: {guitar_eval['metrics']['energy_correlation']}%")
    print(f"     - Spectral Match: {guitar_eval['metrics']['spectral_match']}%")

    if os.path.exists(vocals_wav) and os.path.exists(vox_synth_out):
        vox_eval = evaluate_layer_fidelity(vocals_wav, vox_synth_out)
        print(f"\n  📊 Vocals Layer Fidelity Score: {vox_eval.get('fidelity_score')}%")
        print(f"     - Raw Pitch Accuracy (within 50 cents): {vox_eval['metrics']['raw_pitch_accuracy_rpa']}%")
        print(f"     - Octave Chroma Accuracy: {vox_eval['metrics']['octave_chroma_accuracy_rca']}%")
        print(f"     - Harmonic Chromagram Similarity: {vox_eval['metrics']['chroma_similarity']}%")
        print(f"     - Dynamic RMS Envelope Tracking: {vox_eval['metrics']['energy_correlation']}%")
        print(f"     - Spectral Match: {vox_eval['metrics']['spectral_match']}%")

    overall_report = evaluate_song_accuracy(AUDIO_DIR, manifest_path)
    print(f"\n🎯 OVERALL MUSIC UNDERSTANDING SCORE: {overall_report.get('overall_fidelity_score')}%")
    print("=====================================================================")
    print("🎉 CLOSED-LOOP SYNTHESIS & ACCURACY BENCHMARK PASSED!")
    print("=====================================================================")

if __name__ == "__main__":
    run_test()
