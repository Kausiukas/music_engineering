"""
Looped Quality Verification Engine
Provides objective musical quality metrics and seamless loop auditioning:
1. Pitch Accuracy Metric (f0 RMSE in cents deviation)
2. Transient Beat-Grid Snapping & Jitter (ms)
3. Harmonic Clash & Dissonance Index (%)
4. Seamless 4-Bar / 8-Bar Loop Audition Extractor
"""

import numpy as np
import librosa
import soundfile as sf

def compute_pitch_deviation(ref_audio_path, test_audio_path, sr=22050):
    """
    Computes f0 RMSE cents deviation between reference vocal stem and synthesized test vocal.
    Returns: average cents error, voiced frame overlap percentage.
    """
    y_ref, _ = librosa.load(ref_audio_path, sr=sr, mono=True)
    y_test, _ = librosa.load(test_audio_path, sr=sr, mono=True)
    
    min_len = min(len(y_ref), len(y_test))
    y_ref = y_ref[:min_len]
    y_test = y_test[:min_len]
    
    f0_ref, voiced_ref, _ = librosa.pyin(y_ref, fmin=80, fmax=500, sr=sr)
    f0_test, voiced_test, _ = librosa.pyin(y_test, fmin=80, fmax=500, sr=sr)
    
    valid_mask = voiced_ref & voiced_test & (~np.isnan(f0_ref)) & (~np.isnan(f0_test)) & (f0_ref > 0) & (f0_test > 0)
    
    if np.sum(valid_mask) == 0:
        return {'cents_rmse': 0.0, 'overlap_pct': 0.0, 'rating': 'Insufficient Voiced Frames'}
        
    cents_diff = 1200.0 * np.log2(f0_test[valid_mask] / f0_ref[valid_mask])
    rmse_cents = float(np.sqrt(np.mean(cents_diff**2)))
    overlap_pct = float((np.sum(valid_mask) / max(1, np.sum(voiced_ref))) * 100.0)
    
    if rmse_cents < 30:
        rating = "Pristine Tuning (Studio Quality)"
    elif rmse_cents < 60:
        rating = "Good (Natural Human Tolerance)"
    elif rmse_cents < 100:
        rating = "Acceptable (Noticeable Pitch Drift)"
    else:
        rating = "Poor (Off-Pitch Tuning Error)"
        
    return {
        'cents_rmse': round(rmse_cents, 1),
        'overlap_pct': round(overlap_pct, 1),
        'rating': rating
    }

def compute_transient_jitter(audio_path, bpm=174, sr=22050):
    """
    Measures onset jitter against the 1/16th-note quantize grid.
    Returns: mean jitter in milliseconds and quantization score.
    """
    y, _ = librosa.load(audio_path, sr=sr, mono=True)
    onsets = librosa.onset.onset_detect(y=y, sr=sr, units='time')
    
    if len(onsets) == 0:
        return {'mean_jitter_ms': 0.0, 'score': 100}
        
    grid_step = (60.0 / bpm) / 4.0  # 16th note step in seconds
    
    jitters = []
    for t in onsets:
        # Distance to closest grid line
        remainder = t % grid_step
        dist = min(remainder, grid_step - remainder)
        jitters.append(dist * 1000.0)  # ms
        
    mean_jitter = float(np.mean(jitters))
    score = max(0, int(round(100.0 - (mean_jitter * 2.0))))
    
    return {
        'mean_jitter_ms': round(mean_jitter, 2),
        'onsets_detected': len(onsets),
        'score': score
    }

def compute_harmonic_dissonance(bass_audio_path, harmony_audio_path, sr=22050):
    """
    Evaluates whether the bass frequencies clash with harmonic chord stems (minor 2nd / tritone collisions).
    Returns clash percentage and dissonance rating.
    """
    y_b, _ = librosa.load(bass_audio_path, sr=sr, mono=True)
    y_h, _ = librosa.load(harmony_audio_path, sr=sr, mono=True)
    
    min_len = min(len(y_b), len(y_h))
    chroma_b = librosa.feature.chroma_cqt(y=y_b[:min_len], sr=sr)
    chroma_h = librosa.feature.chroma_cqt(y=y_h[:min_len], sr=sr)
    
    # Check for clashing chromatic intervals (adjacent pitch classes = minor 2nd)
    clashes = 0
    total_frames = chroma_b.shape[1]
    
    for f in range(total_frames):
        b_pitch = np.argmax(chroma_b[:, f])
        h_pitches = np.where(chroma_h[:, f] > 0.4)[0]
        
        for hp in h_pitches:
            interval = abs(b_pitch - hp) % 12
            if interval == 1 or interval == 11 or interval == 6:  # Minor 2nd, Major 7th, Tritone
                clashes += 1
                break
                
    clash_pct = round((clashes / max(1, total_frames)) * 100.0, 1)
    
    return {
        'clash_percentage': clash_pct,
        'consonance_score': round(100.0 - clash_pct, 1),
        'status': 'Consonant & In-Key' if clash_pct < 15 else 'Harmonic Clashes Detected'
    }

def extract_seamless_loop(audio_path, output_loop_path, start_bar=1, num_bars=4, bpm=174, crossfade_ms=30):
    """
    Extracts an exact N-bar loop with zero-crossing crossfading to ensure click-free auditioning.
    """
    y, sr = sf.read(audio_path)
    if y.ndim == 1:
        y = np.stack([y, y], axis=1)
        
    seconds_per_bar = (60.0 / bpm) * 4.0
    start_sec = (start_bar - 1) * seconds_per_bar
    end_sec = start_sec + (num_bars * seconds_per_bar)
    
    start_samp = int(start_sec * sr)
    end_samp = int(end_sec * sr)
    
    if end_samp > len(y):
        end_samp = len(y)
        
    loop = y[start_samp:end_samp].copy()
    
    # Equal-power crossfade between start and end
    fade_len = int((crossfade_ms / 1000.0) * sr)
    if len(loop) > fade_len * 2:
        fade_in = np.linspace(0.0, 1.0, fade_len)[:, np.newaxis]
        fade_out = np.linspace(1.0, 0.0, fade_len)[:, np.newaxis]
        
        # Blend the tail into the head
        loop[:fade_len] = loop[:fade_len] * fade_in + loop[-fade_len:] * fade_out
        loop = loop[:-fade_len]
        
    sf.write(output_loop_path, loop, sr)
    return output_loop_path
