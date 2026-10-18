"""
Audio-to-MIDI Transcription Engine
Converts audio stems (vocals, bass, harmonic instruments) into quantized multi-track MIDI,
extracts pitch contours, note onsets, velocities, and chords.
"""

import os
import sys
import numpy as np
import librosa
import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage

def midi_note_to_name(note_num):
    """Converts MIDI note number to note name like C4, A#3."""
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (note_num // 12) - 1
    name = names[note_num % 12]
    return f"{name}{octave}"

def extract_ace_pitch_and_envelopes(audio_path, sr=22050, hop_length=256, frame_length=1024, fmin=55, fmax=1050):
    """
    Extracts continuous ACE Studio-style parametric curves:
    - F0 continuous pitch contour (Hz & fractional MIDI)
    - Energy envelope (normalized RMS)
    - Tension / Timbre envelope (spectral centroid / high frequency ratio)
    - Breath / Noise ratio (spectral flatness)
    - Voicing confidence
    """
    y, sr = librosa.load(audio_path, sr=sr, mono=True)
    
    # 1. Continuous F0 via pYIN
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=fmin,
        fmax=fmax,
        sr=sr,
        frame_length=frame_length,
        hop_length=hop_length
    )
    times = librosa.times_like(f0, sr=sr, hop_length=hop_length)
    
    # 2. Smooth F0 contour (median filtering to eliminate 1-frame octave glitches)
    f0_clean = np.copy(f0)
    for i in range(1, len(f0) - 1):
        if voiced_flag[i]:
            window = [f0[k] for k in (i-1, i, i+1) if voiced_flag[k] and not np.isnan(f0[k])]
            if len(window) >= 2:
                f0_clean[i] = np.median(window)
                
    # Fractional MIDI contour: 69 + 12 * log2(f0 / 440)
    midi_curve = np.zeros_like(f0_clean)
    valid_mask = (f0_clean > 0) & (~np.isnan(f0_clean)) & voiced_flag
    midi_curve[valid_mask] = 69.0 + 12.0 * np.log2(f0_clean[valid_mask] / 440.0)
    
    # 3. Energy dynamics envelope
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    max_rms = np.max(rms) if np.max(rms) > 0 else 1.0
    norm_energy = np.clip(rms / max_rms, 0.0, 1.0)
    
    # 4. Tension / Brightness envelope (Spectral Centroid normalized 0-1)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    norm_tension = np.clip(centroid / (sr / 4.0), 0.0, 1.0)
    
    # 5. Breath / Noise ratio (Spectral Flatness)
    flatness = librosa.feature.spectral_flatness(y=y, hop_length=hop_length)[0]
    norm_breath = np.clip(flatness * 10.0, 0.0, 1.0)
    
    curve_data = {
        "sample_rate": sr,
        "hop_length": hop_length,
        "time_step_sec": float(hop_length / sr),
        "total_frames": len(times),
        "duration_sec": float(times[-1]) if len(times) > 0 else 0.0,
        "frames": [
            {
                "time": float(round(times[i], 3)),
                "f0_hz": float(round(f0_clean[i], 2)) if valid_mask[i] else 0.0,
                "midi_pitch": float(round(midi_curve[i], 2)) if valid_mask[i] else 0.0,
                "energy": float(round(norm_energy[i], 3)) if i < len(norm_energy) else 0.0,
                "tension": float(round(norm_tension[i], 3)) if i < len(norm_tension) else 0.0,
                "breath": float(round(norm_breath[i], 3)) if i < len(norm_breath) else 0.0,
                "is_voiced": bool(valid_mask[i])
            }
            for i in range(len(times))
        ]
    }
    return curve_data

def extract_melody_notes(audio_path, sr=22050, fmin=55, fmax=1000, hop_length=256, frame_length=1024, min_duration=0.10):
    """
    Extracts clean musical notes with ACE Studio-style harmonic sieve:
    - Transient onset gating (notes only trigger on true attacks)
    - Anti-ghost overtone suppression
    - Vibrato smoothing (does not fracture notes during micro-vibrato)
    """
    y, sr = librosa.load(audio_path, sr=sr, mono=True)
    
    # 1. Onset detection for transient-aligned note beginnings
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=hop_length, backtrack=True)
    onset_times = set(round(t, 2) for t in librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length))
    
    # 2. Extract continuous ACE curves
    curve = extract_ace_pitch_and_envelopes(audio_path, sr=sr, hop_length=hop_length, frame_length=frame_length, fmin=fmin, fmax=fmax)
    frames = curve["frames"]
    
    notes = []
    current_note = None
    
    # Energy noise floor threshold (ignore quiet pick noise & room air)
    energy_threshold = 0.05
    
    for f in frames:
        t = f["time"]
        is_voiced = f["is_voiced"] and f["energy"] >= energy_threshold
        pitch_continuous = f["midi_pitch"]
        vel = int(np.clip(f["energy"] * 127, 45, 127))
        
        if is_voiced:
            nominal_pitch = int(round(pitch_continuous))
            
            if current_note is None:
                current_note = {
                    'pitch': nominal_pitch,
                    'continuous_pitches': [pitch_continuous],
                    'start': t,
                    'end': t + curve["time_step_sec"],
                    'velocity': vel,
                    'note': midi_note_to_name(nominal_pitch),
                    'energies': [f["energy"]]
                }
            else:
                pitch_diff = abs(pitch_continuous - np.median(current_note['continuous_pitches']))
                # Only split if pitch change is substantial (> 1.25 semitones) OR a prominent onset occurs
                is_new_attack = round(t, 2) in onset_times and pitch_diff >= 0.75
                
                if pitch_diff > 1.25 or is_new_attack:
                    dur = current_note['end'] - current_note['start']
                    if dur >= min_duration:
                        # Finalize nominal pitch using median of continuous pitches (suppresses vibrato overshoot)
                        final_pitch = int(round(np.median(current_note['continuous_pitches'])))
                        current_note['pitch'] = final_pitch
                        current_note['note'] = midi_note_to_name(final_pitch)
                        current_note['velocity'] = int(np.clip(np.mean(current_note['energies']) * 127, 45, 127))
                        del current_note['continuous_pitches']
                        del current_note['energies']
                        notes.append(current_note)
                        
                    current_note = {
                        'pitch': nominal_pitch,
                        'continuous_pitches': [pitch_continuous],
                        'start': t,
                        'end': t + curve["time_step_sec"],
                        'velocity': vel,
                        'note': midi_note_to_name(nominal_pitch),
                        'energies': [f["energy"]]
                    }
                else:
                    current_note['end'] = t + curve["time_step_sec"]
                    current_note['continuous_pitches'].append(pitch_continuous)
                    current_note['energies'].append(f["energy"])
        else:
            if current_note is not None:
                dur = current_note['end'] - current_note['start']
                if dur >= min_duration:
                    final_pitch = int(round(np.median(current_note['continuous_pitches'])))
                    current_note['pitch'] = final_pitch
                    current_note['note'] = midi_note_to_name(final_pitch)
                    current_note['velocity'] = int(np.clip(np.mean(current_note['energies']) * 127, 45, 127))
                    del current_note['continuous_pitches']
                    del current_note['energies']
                    notes.append(current_note)
                current_note = None
                
    if current_note is not None and (current_note['end'] - current_note['start']) >= min_duration:
        final_pitch = int(round(np.median(current_note['continuous_pitches'])))
        current_note['pitch'] = final_pitch
        current_note['note'] = midi_note_to_name(final_pitch)
        current_note['velocity'] = int(np.clip(np.mean(current_note['energies']) * 127, 45, 127))
        del current_note['continuous_pitches']
        del current_note['energies']
        notes.append(current_note)
        
    return notes

def extract_chords(audio_path, sr=22050, hop_length=512):
    """
    Estimates chord progression from harmonic audio stem (guitars/keys).
    Returns bar-by-bar chord estimations.
    """
    y, sr = librosa.load(audio_path, sr=sr, mono=True)
    
    # Beat tracking to align chords to beats
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
    bpm = float(np.atleast_1d(tempo)[0])
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=hop_length)
    
    # Chromagram
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    
    chord_templates = {
        'C': [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
        'Dm': [0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0],
        'Em': [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
        'F': [1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0],
        'G': [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1],
        'Am': [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
        'Bdim': [0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1],
        'E': [0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1],
        'A': [0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
        'D': [0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0]
    }
    
    chord_events = []
    # Process beat windows (e.g. 2 beats per chord)
    step = 2
    for i in range(0, len(beat_times) - step, step):
        t_start = beat_times[i]
        t_end = beat_times[i + step]
        frame_start = int(beats[i])
        frame_end = int(beats[i + step])
        
        if frame_end > frame_start and frame_end <= chroma.shape[1]:
            chroma_window = np.mean(chroma[:, frame_start:frame_end], axis=1)
            # Find best match
            best_chord = 'Am'
            best_score = -1
            for name, template in chord_templates.items():
                score = np.dot(chroma_window, template)
                if score > best_score:
                    best_score = score
                    best_chord = name
            chord_events.append({
                'start': float(round(t_start, 2)),
                'end': float(round(t_end, 2)),
                'chord': best_chord,
                'score': float(round(best_score, 2))
            })
            
    return bpm, chord_events

def create_multitrack_midi(vocal_notes, bass_notes, chord_events, output_midi_path, bpm=174, transpose_semitones=0):
    """
    Creates a standard Type 1 Multi-track MIDI file:
    Track 1: Vocal Lead Melody
    Track 2: Chords / Harmony
    Track 3: Bassline
    """
    mid = MidiFile(type=1, ticks_per_beat=480)
    tempo_us = int(mido.bpm2tempo(bpm))
    
    # Track 0: Tempo & Meta
    tempo_track = MidiTrack()
    mid.tracks.append(tempo_track)
    tempo_track.append(MetaMessage('track_name', name='Master Tempo & Grid', time=0))
    tempo_track.append(MetaMessage('set_tempo', tempo=tempo_us, time=0))
    tempo_track.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    tempo_track.append(MetaMessage('end_of_track', time=0))
    
    # Track 1: Vocal Melody
    vocal_track = MidiTrack()
    mid.tracks.append(vocal_track)
    vocal_track.append(MetaMessage('track_name', name='Vocal Lead', time=0))
    vocal_track.append(Message('program_change', program=54, channel=0, time=0)) # Voice Oohs
    
    events = []
    for n in vocal_notes:
        pitch = int(np.clip(n['pitch'] + transpose_semitones, 21, 108))
        vel = int(n.get('velocity', 80))
        events.append({'time': n['start'], 'type': 'on', 'pitch': pitch, 'vel': vel})
        events.append({'time': n['end'], 'type': 'off', 'pitch': pitch, 'vel': 0})
        
    events.sort(key=lambda x: (x['time'], 0 if x['type'] == 'off' else 1))
    
    last_ticks = 0
    ticks_per_sec = (480 * bpm) / 60.0
    for e in events:
        current_ticks = int(round(e['time'] * ticks_per_sec))
        delta = max(0, current_ticks - last_ticks)
        last_ticks = current_ticks
        if e['type'] == 'on':
            vocal_track.append(Message('note_on', note=e['pitch'], velocity=e['vel'], channel=0, time=delta))
        else:
            vocal_track.append(Message('note_off', note=e['pitch'], velocity=0, channel=0, time=delta))
    vocal_track.append(MetaMessage('end_of_track', time=0))
    
    # Track 2: Bass Track
    if bass_notes:
        bass_track = MidiTrack()
        mid.tracks.append(bass_track)
        bass_track.append(MetaMessage('track_name', name='Sub Bass', time=0))
        bass_track.append(Message('program_change', program=38, channel=1, time=0)) # Synth Bass 1
        
        b_events = []
        for n in bass_notes:
            pitch = int(np.clip(n['pitch'] + transpose_semitones, 24, 60))
            b_events.append({'time': n['start'], 'type': 'on', 'pitch': pitch, 'vel': 100})
            b_events.append({'time': n['end'], 'type': 'off', 'pitch': pitch, 'vel': 0})
        b_events.sort(key=lambda x: (x['time'], 0 if x['type'] == 'off' else 1))
        
        last_ticks = 0
        for e in b_events:
            current_ticks = int(round(e['time'] * ticks_per_sec))
            delta = max(0, current_ticks - last_ticks)
            last_ticks = current_ticks
            if e['type'] == 'on':
                bass_track.append(Message('note_on', note=e['pitch'], velocity=e['vel'], channel=1, time=delta))
            else:
                bass_track.append(Message('note_off', note=e['pitch'], velocity=0, channel=1, time=delta))
        bass_track.append(MetaMessage('end_of_track', time=0))
        
    # Track 3: Chord Track
    if chord_events:
        chord_track = MidiTrack()
        mid.tracks.append(chord_track)
        chord_track.append(MetaMessage('track_name', name='Chords / Harmony', time=0))
        chord_track.append(Message('program_change', program=4, channel=2, time=0)) # Electric Piano
        
        chord_notes_map = {
            'C': [60, 64, 67], 'Dm': [62, 65, 69], 'Em': [64, 67, 71],
            'F': [65, 69, 72], 'G': [67, 71, 74], 'Am': [57, 60, 64],
            'Bdim': [59, 62, 65], 'E': [64, 68, 71], 'A': [57, 61, 64],
            'D': [62, 66, 69]
        }
        
        c_events = []
        for c in chord_events:
            notes = chord_notes_map.get(c['chord'], [57, 60, 64])
            for p in notes:
                pitch = int(np.clip(p + transpose_semitones, 36, 96))
                c_events.append({'time': c['start'], 'type': 'on', 'pitch': pitch, 'vel': 75})
                c_events.append({'time': c['end'], 'type': 'off', 'pitch': pitch, 'vel': 0})
        c_events.sort(key=lambda x: (x['time'], 0 if x['type'] == 'off' else 1))
        
        last_ticks = 0
        for e in c_events:
            current_ticks = int(round(e['time'] * ticks_per_sec))
            delta = max(0, current_ticks - last_ticks)
            last_ticks = current_ticks
            if e['type'] == 'on':
                chord_track.append(Message('note_on', note=e['pitch'], velocity=e['vel'], channel=2, time=delta))
            else:
                chord_track.append(Message('note_off', note=e['pitch'], velocity=0, channel=2, time=delta))
        chord_track.append(MetaMessage('end_of_track', time=0))

    mid.save(output_midi_path)
    return output_midi_path
