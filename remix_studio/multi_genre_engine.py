"""
Multi-Genre Generative Remix Engine (Jungle, Techno & House)
Vocal-First Architecture for Lithuanian Folk-Rock Classic 'Kolorado vabalai' by Vytautas Kernagis:
1. Techno Re-creation (134 BPM Peak-Time / Industrial Berlin):
   - 909 Rumble Kick + 16th Driving Hats
   - Acid 303 Bassline following authentic F -> G -> C -> Am progression
   - 152 to 134 BPM Time-Stretched Vocal with sidechain ducking & stereo ping-pong delay
2. House Re-creation (126 BPM French Touch / Classic 909 & Organ):
   - 909 Punch Kick + Offbeat Open Hat + Snare/Clap on 2 and 4
   - Funky Organ Chord Stabs on the upbeats (F -> G -> C -> Am)
   - Funky Bouncy Bassline locked to root notes
   - 152 to 126 BPM Time-Stretched Vocal with warm baritone presence
"""

import os
import sys
import numpy as np
import soundfile as sf
import librosa
from scipy.signal import butter, sosfilt

SR = 44100
CLASSIC_SAMPLES_DIR = r"d:\memes\assets\classic_samples"

def _load_sample(filename, sr=SR):
    path = os.path.join(CLASSIC_SAMPLES_DIR, filename)
    if not os.path.exists(path):
        return None
    data, orig_sr = sf.read(path)
    if orig_sr != sr:
        data = librosa.resample(data.T, orig_sr=orig_sr, target_sr=sr).T
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)
    return data

def _synthesize_303_acid(freq, duration_sec, cutoff=1200, resonance=0.7, sr=SR):
    """Synthesizes a classic TB-303 acid saw line with fast lowpass filter decay."""
    t = np.linspace(0, duration_sec, int(duration_sec * sr), endpoint=False)
    # Sawtooth wave
    saw = 2.0 * (t * freq - np.floor(0.5 + t * freq))
    # Filter envelope
    fc = np.clip(cutoff * np.exp(-t * 12.0) + 120, 80, sr * 0.45)
    # 2-pole resonant LPF simulation
    b, a = butter(2, 600 / (sr / 2), btype='low')
    acid = sosfilt(butter(2, 800, btype='lowpass', fs=sr, output='sos'), saw)
    acid = np.tanh(acid * 2.2) # Drive/Distortion
    peak = np.max(np.abs(acid))
    if peak > 0:
        acid = acid / peak
    return acid

def _synthesize_organ_chord(chord_name, duration_sec, sr=SR):
    """Synthesizes a classic 90s House organ stab (M1 style)."""
    chord_map = {
        'F': [174.61, 220.00, 261.63], # F3, A3, C4
        'G': [196.00, 246.94, 293.66], # G3, B3, D4
        'C': [130.81, 164.81, 196.00], # C3, E3, G3
        'Am': [110.00, 130.81, 164.81], # A2, C3, E3
        'Dm': [146.83, 174.61, 220.00]  # D3, F3, A3
    }
    freqs = chord_map.get(chord_name, [174.61, 220.00, 261.63])
    t = np.linspace(0, duration_sec, int(duration_sec * sr), endpoint=False)
    chord_sig = np.zeros(len(t), dtype=np.float32)
    for f in freqs:
        sine = np.sin(2.0 * np.pi * f * t)
        perc = np.sin(2.0 * np.pi * (f * 2.0) * t) * 0.5
        chord_sig += sine + perc
    # Fast percussive decay
    env = np.exp(-t * 6.5)
    chord_sig = chord_sig * env
    peak = np.max(np.abs(chord_sig))
    if peak > 0:
        chord_sig = chord_sig / peak
    return chord_sig

def render_techno_remix(
    vocal_stem_path,
    output_path,
    bpm=134,
    bars=24,
    transpose_semitones=0
):
    """
    Renders a driving 134 BPM Peak-Time Berlin Techno Remix.
    """
    sec_per_beat = 60.0 / bpm
    sec_per_bar = sec_per_beat * 4.0
    total_duration = bars * sec_per_bar
    total_samples = int(total_duration * SR)

    master_mix = np.zeros((total_samples, 2), dtype=np.float32)
    drum_layer = np.zeros((total_samples, 2), dtype=np.float32)
    bass_layer = np.zeros((total_samples, 2), dtype=np.float32)
    vocal_layer = np.zeros((total_samples, 2), dtype=np.float32)

    # 1. TIME-STRETCH VOCALS (152 BPM -> 134 BPM)
    singing_path = os.path.join(os.path.dirname(vocal_stem_path), "vocal_singing.wav")
    target_voc = singing_path if os.path.exists(singing_path) else vocal_stem_path
    voc_raw, _ = librosa.load(target_voc, sr=SR, mono=False)
    if voc_raw.ndim == 1:
        voc_raw = np.stack([voc_raw, voc_raw], axis=0)

    rate = bpm / 152.0 # 134 / 152 = 0.8815
    voc_l = librosa.effects.time_stretch(voc_raw[0], rate=rate)
    voc_r = librosa.effects.time_stretch(voc_raw[1], rate=rate)
    voc_stretched = np.stack([voc_l, voc_r], axis=1)

    if transpose_semitones != 0:
        vl = librosa.effects.pitch_shift(voc_stretched[:, 0], sr=SR, n_steps=transpose_semitones)
        vr = librosa.effects.pitch_shift(voc_stretched[:, 1], sr=SR, n_steps=transpose_semitones)
        voc_stretched = np.stack([vl, vr], axis=1)

    # Vocal filtering & presence boost
    sos_hpf = butter(4, 130, btype='highpass', fs=SR, output='sos')
    voc_stretched[:, 0] = sosfilt(sos_hpf, voc_stretched[:, 0])
    voc_stretched[:, 1] = sosfilt(sos_hpf, voc_stretched[:, 1])
    sos_shelf = butter(2, 3000, btype='highpass', fs=SR, output='sos')
    voc_stretched += sosfilt(sos_shelf, voc_stretched) * 0.40

    # Vocal drop at Bar 5
    vocal_start_idx = int(4 * sec_per_bar * SR)
    vocal_end_idx = min(total_samples, vocal_start_idx + len(voc_stretched))
    actual_voc_len = vocal_end_idx - vocal_start_idx
    vocal_layer[vocal_start_idx:vocal_end_idx] = voc_stretched[:actual_voc_len] * 1.30

    # 2. DRUMS: 909 Rumble Kick & Industrial Hats
    kick = _load_sample("techno_techno_909_kick_rumble_705.flac")
    closed_hat = _load_sample("drum_cymbal_closed.flac")
    open_hat = _load_sample("drum_cymbal_open.flac")

    for b in range(bars):
        b_idx = int(b * sec_per_bar * SR)
        for beat in range(4):
            beat_idx = b_idx + int(beat * sec_per_beat * SR)
            # 4-on-the-floor kick
            if kick is not None:
                k_end = min(total_samples, beat_idx + len(kick))
                drum_layer[beat_idx:k_end] += kick[:k_end - beat_idx] * 0.70
            
            # Offbeat open hat (beat + 0.5)
            if open_hat is not None:
                o_idx = beat_idx + int(0.5 * sec_per_beat * SR)
                o_end = min(total_samples, o_idx + len(open_hat))
                drum_layer[o_idx:o_end] += open_hat[:o_end - o_idx] * 0.35

            # 16th note closed hats
            if closed_hat is not None and b >= 2:
                for sub in [0.25, 0.75]:
                    c_idx = beat_idx + int(sub * sec_per_beat * SR)
                    c_end = min(total_samples, c_idx + len(closed_hat))
                    drum_layer[c_idx:c_end] += closed_hat[:c_end - c_idx] * 0.22

    # 3. ACID 303 BASSLINE (Authentic progression: F -> G -> C -> Am)
    progression = ['F', 'F', 'G', 'G', 'C', 'Am', 'F', 'F', 'C', 'C', 'C', 'C', 'F', 'Dm', 'Dm', 'C', 'F', 'F', 'C', 'C', 'F', 'G', 'C', 'F']
    freq_map = {'F': 87.31, 'G': 98.00, 'C': 65.41, 'Am': 55.00, 'Dm': 73.42}

    for b in range(bars):
        if b < 2 or b == 11:
            continue
        chord = progression[b % len(progression)]
        freq = freq_map.get(chord, 87.31)
        if transpose_semitones != 0:
            freq = freq * (2.0 ** (transpose_semitones / 12.0))
        b_idx = int(b * sec_per_bar * SR)
        # 16th rolling acid pulses
        for s in range(16):
            if s in [0, 2, 3, 6, 8, 10, 11, 14]:
                s_idx = b_idx + int(s * (sec_per_bar / 16.0) * SR)
                note_len = sec_per_bar / 16.0 * 0.85
                acid = _synthesize_303_acid(freq, note_len, cutoff=900 + (s * 60), sr=SR)
                s_end = min(total_samples, s_idx + len(acid))
                l_len = s_end - s_idx
                bass_layer[s_idx:s_end, 0] += acid[:l_len] * 0.40
                bass_layer[s_idx:s_end, 1] += acid[:l_len] * 0.40

    # 4. VOCAL-FIRST DUCKING
    voc_mono = np.mean(vocal_layer, axis=1)
    hop = 512
    voc_rms = librosa.feature.rms(y=voc_mono, frame_length=2048, hop_length=hop)[0]
    env = np.interp(np.arange(total_samples), np.arange(len(voc_rms)) * hop, voc_rms)
    ducking = 1.0 - 0.38 * np.clip((env - 0.02) / 0.08, 0.0, 1.0)
    ducking = ducking[:, np.newaxis]
    drum_layer = drum_layer * ducking
    bass_layer = bass_layer * ducking

    # 5. MASTER SUM
    master_mix += drum_layer
    master_mix += bass_layer
    master_mix += vocal_layer

    peak = np.max(np.abs(master_mix))
    if peak > 0:
        master_mix = master_mix * (0.88 / peak)

    sf.write(output_path, master_mix, SR)

    # Extract 4-bar seamless loop
    loop_path = output_path.replace(".wav", "_loop.wav")
    from quality_checker import extract_seamless_loop
    extract_seamless_loop(output_path, loop_path, start_bar=5, num_bars=4, bpm=bpm)
    return output_path

def render_house_remix(
    vocal_stem_path,
    output_path,
    bpm=126,
    bars=24,
    transpose_semitones=0
):
    """
    Renders a warm 126 BPM French Touch / Classic 909 & Organ House Remix.
    """
    sec_per_beat = 60.0 / bpm
    sec_per_bar = sec_per_beat * 4.0
    total_duration = bars * sec_per_bar
    total_samples = int(total_duration * SR)

    master_mix = np.zeros((total_samples, 2), dtype=np.float32)
    drum_layer = np.zeros((total_samples, 2), dtype=np.float32)
    bass_layer = np.zeros((total_samples, 2), dtype=np.float32)
    chord_layer = np.zeros((total_samples, 2), dtype=np.float32)
    vocal_layer = np.zeros((total_samples, 2), dtype=np.float32)

    # 1. TIME-STRETCH VOCALS (152 BPM -> 126 BPM)
    singing_path = os.path.join(os.path.dirname(vocal_stem_path), "vocal_singing.wav")
    target_voc = singing_path if os.path.exists(singing_path) else vocal_stem_path
    voc_raw, _ = librosa.load(target_voc, sr=SR, mono=False)
    if voc_raw.ndim == 1:
        voc_raw = np.stack([voc_raw, voc_raw], axis=0)

    rate = bpm / 152.0 # 126 / 152 = 0.8289
    voc_l = librosa.effects.time_stretch(voc_raw[0], rate=rate)
    voc_r = librosa.effects.time_stretch(voc_raw[1], rate=rate)
    voc_stretched = np.stack([voc_l, voc_r], axis=1)

    if transpose_semitones != 0:
        vl = librosa.effects.pitch_shift(voc_stretched[:, 0], sr=SR, n_steps=transpose_semitones)
        vr = librosa.effects.pitch_shift(voc_stretched[:, 1], sr=SR, n_steps=transpose_semitones)
        voc_stretched = np.stack([vl, vr], axis=1)

    # Vocal filtering
    sos_hpf = butter(4, 110, btype='highpass', fs=SR, output='sos')
    voc_stretched[:, 0] = sosfilt(sos_hpf, voc_stretched[:, 0])
    voc_stretched[:, 1] = sosfilt(sos_hpf, voc_stretched[:, 1])
    sos_shelf = butter(2, 3400, btype='highpass', fs=SR, output='sos')
    voc_stretched += sosfilt(sos_shelf, voc_stretched) * 0.42

    vocal_start_idx = int(4 * sec_per_bar * SR)
    vocal_end_idx = min(total_samples, vocal_start_idx + len(voc_stretched))
    actual_voc_len = vocal_end_idx - vocal_start_idx
    vocal_layer[vocal_start_idx:vocal_end_idx] = voc_stretched[:actual_voc_len] * 1.32

    # 2. DRUMS: 909 Punch Kick + Clap on 2 & 4 + Offbeat Open Hat
    kick = _load_sample("house_house_909_punch_kick_694.flac")
    snare = _load_sample("drum_snare_hard.flac")
    open_hat = _load_sample("drum_cymbal_open.flac")
    closed_hat = _load_sample("drum_cymbal_closed.flac")

    for b in range(bars):
        b_idx = int(b * sec_per_bar * SR)
        for beat in range(4):
            beat_idx = b_idx + int(beat * sec_per_beat * SR)
            # Kick
            if kick is not None:
                k_end = min(total_samples, beat_idx + len(kick))
                drum_layer[beat_idx:k_end] += kick[:k_end - beat_idx] * 0.75

            # Snare/Clap on 2 and 4 (beat 1 and 3 in 0-indexed)
            if snare is not None and beat in [1, 3]:
                s_end = min(total_samples, beat_idx + len(snare))
                drum_layer[beat_idx:s_end] += snare[:s_end - beat_idx] * 0.50

            # Offbeat open hat (beat + 0.5)
            if open_hat is not None:
                o_idx = beat_idx + int(0.5 * sec_per_beat * SR)
                o_end = min(total_samples, o_idx + len(open_hat))
                drum_layer[o_idx:o_end] += open_hat[:o_end - o_idx] * 0.40

    # 3. HARMONY: Organ Stabs on Upbeats & Funky Bassline
    progression = ['F', 'F', 'G', 'G', 'C', 'Am', 'F', 'F', 'C', 'C', 'C', 'C', 'F', 'Dm', 'Dm', 'C', 'F', 'F', 'C', 'C', 'F', 'G', 'C', 'F']
    bass_freq_map = {'F': 43.65, 'G': 49.00, 'C': 65.41, 'Am': 55.00, 'Dm': 73.42}

    for b in range(bars):
        if b < 2 or b == 11:
            continue
        chord = progression[b % len(progression)]
        b_idx = int(b * sec_per_bar * SR)
        
        # Upbeat organ stabs (beats 0.5, 1.5, 2.5, 3.5)
        for ub in [0.5, 1.5, 2.5, 3.5]:
            u_idx = b_idx + int(ub * sec_per_beat * SR)
            stab = _synthesize_organ_chord(chord, sec_per_beat * 0.45, sr=SR)
            u_end = min(total_samples, u_idx + len(stab))
            s_len = u_end - u_idx
            chord_layer[u_idx:u_end, 0] += stab[:s_len] * 0.38
            chord_layer[u_idx:u_end, 1] += stab[:s_len] * 0.38

        # Funky bass rhythm (beat 0.0, 1.75, 2.5)
        freq = bass_freq_map.get(chord, 43.65)
        if transpose_semitones != 0:
            freq = freq * (2.0 ** (transpose_semitones / 12.0))
            
        for bo in [0.0, 1.75, 2.5]:
            bo_idx = b_idx + int(bo * sec_per_beat * SR)
            t_bass = np.linspace(0, sec_per_beat * 0.8, int(sec_per_beat * 0.8 * SR), endpoint=False)
            b_sig = np.sin(2.0 * np.pi * freq * t_bass) * np.exp(-t_bass * 3.5)
            bo_end = min(total_samples, bo_idx + len(b_sig))
            b_len = bo_end - bo_idx
            bass_layer[bo_idx:bo_end, 0] += b_sig[:b_len] * 0.55
            bass_layer[bo_idx:bo_end, 1] += b_sig[:b_len] * 0.55

    # 4. VOCAL DUCKING
    voc_mono = np.mean(vocal_layer, axis=1)
    hop = 512
    voc_rms = librosa.feature.rms(y=voc_mono, frame_length=2048, hop_length=hop)[0]
    env = np.interp(np.arange(total_samples), np.arange(len(voc_rms)) * hop, voc_rms)
    ducking = 1.0 - 0.35 * np.clip((env - 0.02) / 0.08, 0.0, 1.0)
    ducking = ducking[:, np.newaxis]
    drum_layer = drum_layer * ducking
    chord_layer = chord_layer * ducking
    bass_layer = bass_layer * ducking

    # 5. MASTER SUM
    master_mix += drum_layer
    master_mix += bass_layer
    master_mix += chord_layer
    master_mix += vocal_layer

    peak = np.max(np.abs(master_mix))
    if peak > 0:
        master_mix = master_mix * (0.88 / peak)

    sf.write(output_path, master_mix, SR)

    # Extract 4-bar loop
    loop_path = output_path.replace(".wav", "_loop.wav")
    from quality_checker import extract_seamless_loop
    extract_seamless_loop(output_path, loop_path, start_bar=5, num_bars=4, bpm=bpm)
    return output_path
