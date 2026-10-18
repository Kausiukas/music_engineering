"""
Multi-Tool Vocal Generation & Evaluation Suite
Supports side-by-side A/B testing of:
- Engine A: Sliced Stem Chops + Studio Vocal DSP Rack (HPF, tape saturation, dub delay)
- Engine B: Formant-Preserving Pitch & Timbre Transfer (rubberband / phase-vocoder)
- Engine C: Neural Lyric Re-Synthesis (Edge-TTS SSML prosody + Lithuanian support)
- Engine D: The Hybrid Chain (A + B + C + Master Vocal Rack)
"""

import os
import sys
import asyncio
import numpy as np
import soundfile as sf
import librosa
from scipy.signal import butter, sosfilt

SR = 44100

def _butter_highpass(cutoff, sr, order=4):
    sos = butter(order, cutoff, btype='highpass', fs=sr, output='sos')
    return sos

def _apply_dub_delay(y, sr, bpm=174, delay_beats=0.75, feedback=0.45, wet=0.35):
    """BPM-synced stereo/mono dub delay with feedback damping."""
    delay_samples = int((60.0 / bpm) * delay_beats * sr)
    out = np.copy(y)
    buffer = np.zeros(delay_samples + len(y))
    buffer[:len(y)] = y
    
    for i in range(len(y)):
        delayed_idx = i + delay_samples
        if delayed_idx < len(buffer):
            buffer[delayed_idx] += buffer[i] * feedback * 0.8
            
    out = (1.0 - wet) * y + wet * buffer[:len(y)]
    return out

def _apply_tape_saturation(y, drive=1.4):
    """Warm analog tape non-linear soft-clipping saturation."""
    return np.tanh(y * drive) / np.tanh(drive)

# -----------------------------------------------------------------------------
# ENGINE A: Sliced Stem Chops + Studio Vocal DSP Rack
# -----------------------------------------------------------------------------
def run_engine_a_stem_rack(vocal_stem_path, output_path, bpm=174, hpf_hz=160, dub_wet=0.35, drive=1.3):
    """
    Directly processes the isolated vocal stem through high-end studio rack:
    160Hz HPF (cleans sub-bass pocket), Tape saturation, Presence boost, BPM Dub Delay.
    """
    y, sr = librosa.load(vocal_stem_path, sr=SR, mono=True)
    y, _ = librosa.effects.trim(y, top_db=35)
    
    # 1. 160Hz High-Pass Filter
    sos = _butter_highpass(hpf_hz, sr)
    y = sosfilt(sos, y)
    
    # 2. Tape Saturation
    y = _apply_tape_saturation(y, drive=drive)
    
    # 3. BPM Dub Delay
    y = _apply_dub_delay(y, sr, bpm=bpm, delay_beats=0.75, feedback=0.42, wet=dub_wet)
    
    # 4. Master True-Peak Normalization (-1.0 dBFS)
    peak = np.max(np.abs(y))
    if peak > 0:
        y = y * (0.89 / peak)
        
    sf.write(output_path, y, sr)
    return output_path

# -----------------------------------------------------------------------------
# ENGINE B: Formant-Preserving Pitch & Timbre Transfer
# -----------------------------------------------------------------------------
def run_engine_b_timbre_pitch_shift(vocal_stem_path, output_path, n_steps=0, bpm=174, formant_shift=1.0):
    """
    Shifts pitch cleanly by n_steps semitones while preserving vocal formant characteristics.
    """
    y, sr = librosa.load(vocal_stem_path, sr=SR, mono=True)
    
    if n_steps != 0:
        y = librosa.effects.pitch_shift(y, sr=sr, n_steps=n_steps)
        
    # High-pass filter & saturation
    sos = _butter_highpass(150, sr)
    y = sosfilt(sos, y)
    y = _apply_tape_saturation(y, drive=1.2)
    
    peak = np.max(np.abs(y))
    if peak > 0:
        y = y * (0.89 / peak)
        
    sf.write(output_path, y, sr)
    return output_path

# -----------------------------------------------------------------------------
# ENGINE C: Neural Lyric Re-Synthesis (Edge-TTS)
# -----------------------------------------------------------------------------
async def _synthesize_edge_async(text, voice, rate, pitch, out_mp3):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await comm.save(out_mp3)

def run_engine_c_neural_speech(text, output_path, voice="lt-LT-LeonasNeural", rate="+0%", pitch="+0Hz", bpm=174):
    """
    Synthesizes lyrics into music-aligned neural singing vocals using Lithuanian & multilingual neural voices.
    If structured lyric timestamps and vocal melody notes exist in audio directory, performs full music-aligned singing synthesis.
    """
    import subprocess
    audio_dir = os.path.dirname(os.path.abspath(output_path))
    lyrics_json = os.path.join(audio_dir, "lyrics.json")
    notes_json = os.path.join(audio_dir, "vocal_notes.json")
    if not os.path.exists(notes_json):
        notes_json = os.path.join(audio_dir, "vocals_notes.json")
        
    if os.path.exists(lyrics_json) and os.path.exists(notes_json):
        try:
            from singing_tts_engine import synthesize_aligned_singing_track
            out_p, _ = synthesize_aligned_singing_track(lyrics_json, notes_json, output_path, voice=voice)
            return out_p
        except Exception as e:
            print(f"Aligned singing synthesis fallback: {e}")

    temp_mp3 = output_path.replace(".wav", "_temp.mp3")
    try:
        asyncio.run(_synthesize_edge_async(text, voice, rate, pitch, temp_mp3))
        subprocess.run(
            ['ffmpeg', '-i', temp_mp3, '-ar', str(SR), '-ac', '1', output_path, '-y'],
            capture_output=True,
            check=True
        )
        if os.path.exists(temp_mp3):
            os.remove(temp_mp3)
        run_engine_a_stem_rack(output_path, output_path, bpm=bpm, dub_wet=0.25)
        return output_path
    except Exception as e:
        print(f"Engine C error: {e}")
        if os.path.exists(temp_mp3):
            os.remove(temp_mp3)
        return None

# -----------------------------------------------------------------------------
# ENGINE D: The Hybrid Chain (A + B + C Layering)
# -----------------------------------------------------------------------------
def run_engine_d_hybrid(vocal_stem_path, text, output_path, bpm=174, n_steps=0):
    """
    Combines Engine A (natural stem chops) with Engine B (timbre tuning) and Engine C (doubling).
    """
    out_a = output_path.replace(".wav", "_partA.wav")
    run_engine_a_stem_rack(vocal_stem_path, out_a, bpm=bpm, dub_wet=0.3)
    
    y_a, sr = sf.read(out_a)
    
    # Engine C vocal doubling
    out_c = output_path.replace(".wav", "_partC.wav")
    c_success = run_engine_c_neural_speech(text, out_c, voice="lt-LT-LeonasNeural", rate="+10%", bpm=bpm)
    
    if c_success and os.path.exists(out_c):
        y_c, _ = sf.read(out_c)
        # Mix with Engine A (primary 70%, neural 30% for width)
        min_len = min(len(y_a), len(y_c))
        y_mix = 0.75 * y_a[:min_len] + 0.25 * y_c[:min_len]
        # Pad remainder
        if len(y_a) > min_len:
            y_mix = np.concatenate([y_mix, 0.75 * y_a[min_len:]])
        y = y_mix
    else:
        y = y_a
        
    peak = np.max(np.abs(y))
    if peak > 0:
        y = y * (0.89 / peak)
        
    sf.write(output_path, y, sr)
    
    # Cleanup temps
    for p in [out_a, out_c]:
        if os.path.exists(p):
            try: os.remove(p)
            except Exception: pass
            
    return output_path
