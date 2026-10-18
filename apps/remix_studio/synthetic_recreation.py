"""
Closed-Loop Synthetic Recreation Engine
Incorporates ACE Studio continuous pitch curve modeling, multi-parametric envelopes,
and harmonic additive/wavetable synthesis to regenerate stems and master song tracks.
"""

import os
import sys
import json
import numpy as np
from audiocore.dsp import limit_peak
from audiocore.pitch import midi_to_hz
import soundfile as sf
import librosa

def synthesize_continuous_pitch_stem(curve_data, sr=22050, duration_sec=None, instrument="acoustic_guitar", transpose_semitones=0):
    """
    Synthesizes audio directly from ACE Studio continuous F0 pitch curve and energy envelopes.
    Preserves continuous micro-intonation, portamento slides, and vibrato.
    """
    frames = curve_data.get("frames", [])
    if not frames:
        dur = duration_sec or 1.0
        return np.zeros(int(dur * sr), dtype=np.float32)
        
    total_duration = duration_sec or curve_data.get("duration_sec", frames[-1]["time"])
    n_samples = int(np.ceil(total_duration * sr))
    t_audio = np.linspace(0, total_duration, n_samples, endpoint=False)
    
    # Extract time series from frames
    frame_times = np.array([f["time"] for f in frames])
    raw_f0 = np.array([f["f0_hz"] for f in frames])
    raw_energy = np.array([f["energy"] for f in frames])
    raw_tension = np.array([f.get("tension", 0.5) for f in frames])
    
    # Apply transposition in frequency space: f' = f * 2^(st/12)
    if transpose_semitones != 0:
        pitch_factor = 2.0 ** (transpose_semitones / 12.0)
        raw_f0 = raw_f0 * pitch_factor
        
    # Interpolate continuous F0 and Energy onto audio sample grid
    # For unvoiced regions (f0 == 0), keep 0
    voiced_indices = np.where(raw_f0 > 20.0)[0]
    if len(voiced_indices) == 0:
        return np.zeros(n_samples, dtype=np.float32)
        
    interp_f0 = np.interp(t_audio, frame_times, raw_f0)
    interp_energy = np.interp(t_audio, frame_times, raw_energy)
    interp_tension = np.interp(t_audio, frame_times, raw_tension)
    
    # Voicing mask: mute when energy is below threshold or f0 was zero
    voiced_mask = np.interp(t_audio, frame_times, (raw_f0 > 20.0).astype(float)) > 0.5
    interp_f0[~voiced_mask] = 0.0
    
    # Instantaneous phase calculation: phi(t) = 2*pi * cumsum(f0(t) * dt)
    dt = 1.0 / sr
    phase = 2.0 * np.pi * np.cumsum(interp_f0 * dt)
    
    # Harmonic series generation tailored to instrument timbre
    # Acoustic guitar / piano / voice harmonics
    if instrument in ["acoustic_guitar", "guitar"]:
        # Warm string timbre: prominent fundamental, rich 2nd/3rd, decaying higher
        harmonic_weights = [1.0, 0.75, 0.45, 0.30, 0.18, 0.10, 0.05]
    elif instrument in ["bass", "sub_bass"]:
        # Heavy fundamental, warm 2nd harmonic, filtered highs
        harmonic_weights = [1.0, 0.50, 0.15, 0.05]
    elif instrument in ["vocals", "lead"]:
        # Vocal formant-like harmonic spectrum
        harmonic_weights = [1.0, 0.85, 0.65, 0.45, 0.35, 0.25, 0.15]
    else:
        harmonic_weights = [1.0, 0.60, 0.35, 0.20, 0.10]
        
    audio = np.zeros(n_samples, dtype=np.float32)
    for k, w in enumerate(harmonic_weights, start=1):
        # Tension parameter adds brightness by boosting higher harmonics
        tension_boost = 1.0 + (interp_tension * (k - 1) * 0.4)
        audio += (w * tension_boost * np.sin(k * phase)).astype(np.float32)
        
    # Shape amplitude with continuous energy envelope
    audio *= interp_energy
    
    # Soft knee limiting & normalization
    audio = limit_peak(audio)
        
    return audio

def synthesize_polyphonic_notes(notes, sr=22050, duration_sec=None, instrument="acoustic_guitar", transpose_semitones=0):
    """
    Synthesizes discrete musical notes with realistic per-note ADSR envelopes,
    pluck attack transients, and natural string damping.
    """
    if not notes:
        dur = duration_sec or 1.0
        return np.zeros(int(dur * sr), dtype=np.float32)
        
    max_end = max(n["end"] for n in notes)
    total_dur = max(duration_sec or 0.0, max_end + 1.0)
    n_samples = int(np.ceil(total_dur * sr))
    audio = np.zeros(n_samples, dtype=np.float32)
    
    for n in notes:
        pitch = n["pitch"] + transpose_semitones
        f0 = midi_to_hz(pitch)
        start_sample = int(round(n["start"] * sr))
        dur_samples = int(round((n["end"] - n["start"]) * sr))
        
        if start_sample >= n_samples or dur_samples <= 0:
            continue
            
        vel = n.get("velocity", 80) / 127.0
        
        # Note duration with natural decay tail
        tail_samples = int(0.15 * sr)
        total_note_samples = min(dur_samples + tail_samples, n_samples - start_sample)
        t_note = np.arange(total_note_samples) / sr
        
        # ADSR Envelope
        attack_sec = 0.015 if instrument in ["acoustic_guitar", "guitar", "bass"] else 0.04
        decay_sec = 0.15
        sustain_level = 0.65
        
        env = np.ones(total_note_samples, dtype=np.float32)
        attack_samples = min(int(attack_sec * sr), total_note_samples)
        if attack_samples > 0:
            env[:attack_samples] = np.linspace(0, 1.0, attack_samples)
            
        # Exponential decay towards sustain
        decay_start = attack_samples
        if total_note_samples > decay_start:
            rem_samples = total_note_samples - decay_start
            decay_curve = sustain_level + (1.0 - sustain_level) * np.exp(-t_note[:rem_samples] / max(decay_sec, 0.01))
            env[decay_start:] = decay_curve
            
        # Release tail at the end
        if total_note_samples > dur_samples:
            rel_len = total_note_samples - dur_samples
            env[dur_samples:] *= np.linspace(1.0, 0.0, rel_len)
            
        # Harmonic synthesis of note
        if instrument in ["bass", "sub_bass"]:
            harmonics = [1.0, 0.55, 0.20, 0.05]
        elif instrument in ["acoustic_guitar", "guitar"]:
            harmonics = [1.0, 0.70, 0.40, 0.25, 0.15, 0.08]
        elif instrument in ["piano", "keys"]:
            harmonics = [1.0, 0.80, 0.50, 0.30, 0.20, 0.10, 0.05]
        else:
            harmonics = [1.0, 0.60, 0.30, 0.15]
            
        note_wave = np.zeros(total_note_samples, dtype=np.float32)
        for k, h_weight in enumerate(harmonics, start=1):
            note_wave += h_weight * np.sin(2.0 * np.pi * (k * f0) * t_note).astype(np.float32)
            
        note_audio = note_wave * env * vel * 0.4
        end_sample = start_sample + total_note_samples
        audio[start_sample:end_sample] += note_audio
        
    # Soft knee limiting
    audio = limit_peak(audio)
        
    return audio

def recreate_synthetic_layer(layer_name, audio_dir, out_wav_path, transpose_semitones=0, voice="lt-LT-LeonasNeural", sr=22050):
    """
    Recreates a high-fidelity synthetic layer using both continuous ACE curves and clean notes.
    Combines continuous harmonic expressivity with polyphonic attack transients.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_wav_path)), exist_ok=True)
    
    notes_file = os.path.join(audio_dir, f"{layer_name}_notes.json")
    curve_file = os.path.join(audio_dir, f"{layer_name}_pitch_curve.json")
    
    notes = []
    if os.path.exists(notes_file):
        with open(notes_file, 'r', encoding='utf-8') as f:
            notes = json.load(f)
            
    curve_data = {}
    if os.path.exists(curve_file):
        with open(curve_file, 'r', encoding='utf-8') as f:
            curve_data = json.load(f)
            
    # If notes or curve are missing, attempt fallback to generic layer file
    if not notes and not curve_data:
        fallback_notes = os.path.join(audio_dir, "vocal_notes.json")
        if os.path.exists(fallback_notes):
            with open(fallback_notes, 'r', encoding='utf-8') as f:
                notes = json.load(f)
                
    dur = 90.0
    if notes:
        dur = max(n["end"] for n in notes) + 1.0
    elif curve_data:
        dur = curve_data.get("duration_sec", 90.0)

    # If vocal layer, render via Music-Aligned Singing TTS Engine
    if layer_name in ["vocals", "vocal"]:
        lyrics_file = os.path.join(audio_dir, "lyrics.json")
        if os.path.exists(lyrics_file):
            try:
                from singing_tts_engine import synthesize_aligned_singing_track
                return synthesize_aligned_singing_track(lyrics_file, notes_file, out_wav_path, total_duration_sec=dur, voice=voice, transpose_semitones=transpose_semitones, sr=sr)
            except Exception as e:
                print(f"Singing TTS error, falling back to acoustic timbre: {e}")
        
    # Generate authentic acoustic physical model audio
    from acoustic_timbre_engine import render_instrument_notes
    audio_notes = render_instrument_notes(notes, instrument_type=layer_name, sr=sr, duration_sec=dur, transpose_semitones=transpose_semitones)
    
    # Generate continuous curve audio if available (ambient layer blend)
    if curve_data and curve_data.get("frames"):
        audio_curve = synthesize_continuous_pitch_stem(curve_data, sr=sr, duration_sec=dur, instrument=layer_name, transpose_semitones=transpose_semitones)
        min_len = min(len(audio_notes), len(audio_curve))
        blended = (0.75 * audio_notes[:min_len]) + (0.25 * audio_curve[:min_len])
        if len(audio_notes) > min_len:
            blended = np.concatenate([blended, 0.75 * audio_notes[min_len:]])
    else:
        blended = audio_notes
        
    # Enforce zero-clipping rule (linear amplitude <= 0.92 / -0.7 dBFS)
    peak = np.max(np.abs(blended))
    if peak > 0.92:
        blended = (blended / peak) * 0.92
    elif peak < 0.1 and peak > 0:
        blended = (blended / peak) * 0.70
        
    sf.write(out_wav_path, blended, sr)
    return out_wav_path, blended

def recreate_full_synthetic_song(manifest_path, audio_dir, out_master_path, transpose_semitones=0, voice="lt-LT-LeonasNeural", sr=22050):
    """
    Recreates the entire song synthetically across all active layers:
    Summed together and peak-limited to <= -0.7 dBFS.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_master_path)), exist_ok=True)
    
    manifest_data = {"layers": []}
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
            
    layers = manifest_data.get("layers", [])
    active_layers = [l for l in layers if l.get("is_active", True)]
    if not active_layers:
        active_layers = layers
        
    max_len = 0
    layer_audios = []
    
    for l in active_layers:
        lid = l["id"]
        temp_layer_out = os.path.join(audio_dir, "synthetic", f"synth_{lid}_{transpose_semitones:+d}.wav")
        _, audio = recreate_synthetic_layer(lid, audio_dir, temp_layer_out, transpose_semitones=transpose_semitones, voice=voice, sr=sr)
        if len(audio) > max_len:
            max_len = len(audio)
        layer_audios.append((lid, audio))
        
    # Master sum
    master_mix = np.zeros(max_len, dtype=np.float32)
    for lid, audio in layer_audios:
        # Layer balancing: bass and guitar given solid headroom
        gain = 0.85 if "bass" in lid else 1.0
        master_mix[:len(audio)] += (audio * gain)
        
    # Master soft peak limiting (ECC Zero-Clipping Rule <= -0.7 dBFS)
    master_mix = limit_peak(master_mix)
        
    sf.write(out_master_path, master_mix, sr)
    return out_master_path, len(layer_audios)
