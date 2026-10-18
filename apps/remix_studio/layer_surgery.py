"""
Layer Surgery Engine
Performs precision audio DSP and symbolic musical operations to merge or split stems/layers.

Capabilities:
1. Merge Layers: Combines 2+ audio stems (with soft-limiting/normalization),
   merges their note transcription events (chronological sort & overlap resolution),
   updates MIDI tracks, database records, and manifest.
2. Split Layer: Decomposes a wideband layer into Low (Bass) and High (Treble/Chord) stems
   via Linkwitz-Riley / Butterworth crossover filters and pitch-based note partitioning.
"""

import os
import studio_paths
import sys
import json
import numpy as np
import soundfile as sf
import librosa
from scipy import signal
import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = studio_paths.AUDIO_DIR
STEMS_DIR = studio_paths.STEMS_DIR
MIDI_DIR = studio_paths.MIDI_DIR

# Import DB
try:
    from database.db import (
        get_connection,
        load_manifest_from_db,
        save_manifest_to_db,
        get_current_song_id
    )
except ImportError:
    sys.path.insert(0, BASE_DIR)
    from database.db import (
        get_connection,
        load_manifest_from_db,
        save_manifest_to_db,
        get_current_song_id
    )

def find_stem_file(layer_id):
    """Finds stem audio file on disk, checking stems/ then audio/."""
    candidates = [
        os.path.join(STEMS_DIR, f"{layer_id}.wav"),
        os.path.join(AUDIO_DIR, f"{layer_id}.wav"),
        os.path.join(STEMS_DIR, f"{layer_id}.mp3"),
        os.path.join(AUDIO_DIR, f"{layer_id}.mp3")
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def find_notes_file(layer_id):
    """Finds note transcription JSON file on disk."""
    candidates = [
        os.path.join(AUDIO_DIR, f"{layer_id}_notes.json"),
        os.path.join(AUDIO_DIR, f"{layer_id[:-1] if layer_id.endswith('s') else layer_id}_notes.json"),
        os.path.join(AUDIO_DIR, "audio", f"{layer_id}_notes.json")
    ]
    if layer_id == "vocals":
        candidates.insert(0, os.path.join(AUDIO_DIR, "vocal_notes.json"))
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def compute_layer_metrics(audio_path):
    """Computes RMS dB, active duty cycle, and onset count for a stem."""
    if not os.path.exists(audio_path):
        return {"rms_db": -90.0, "active_duty_cycle": 0.0, "onsets": 0, "verdict": "inactive"}
    try:
        y, sr = sf.read(audio_path)
        if y.ndim > 1:
            y = np.mean(y, axis=1)
        if len(y) == 0:
            return {"rms_db": -90.0, "active_duty_cycle": 0.0, "onsets": 0, "verdict": "inactive"}
            
        frame_len = 2048
        hop_len = 512
        rms = librosa.feature.rms(y=y, frame_length=frame_len, hop_length=hop_len)[0]
        mean_rms = float(np.mean(rms))
        rms_db = float(round(20.0 * np.log10(max(mean_rms, 1e-5)), 1))
        
        # Duty cycle: fraction of frames exceeding -45 dB threshold
        thresh = 10.0 ** (-45.0 / 20.0)
        duty_cycle = float(round(np.sum(rms > thresh) / max(len(rms), 1), 3))
        
        # Onsets
        onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_len)
        num_onsets = int(len(onsets))
        
        verdict = "active" if (rms_db > -42.0 and duty_cycle > 0.05) else "inactive"
        return {
            "rms_db": rms_db,
            "active_duty_cycle": duty_cycle,
            "onsets": num_onsets,
            "verdict": verdict
        }
    except Exception as e:
        print(f"[Surgery] Error computing metrics for {audio_path}: {e}")
        return {"rms_db": -90.0, "active_duty_cycle": 0.0, "onsets": 0, "verdict": "inactive"}

def write_midi_file(notes, output_midi_path, bpm=174, track_name="Merged Track"):
    """Generates standard Type 1 MIDI file from a list of note events."""
    os.makedirs(os.path.dirname(output_midi_path), exist_ok=True)
    mid = MidiFile(type=1, ticks_per_beat=480)
    tempo_us = int(mido.bpm2tempo(bpm))
    
    # Tempo track
    tempo_track = MidiTrack()
    mid.tracks.append(tempo_track)
    tempo_track.append(MetaMessage('track_name', name='Tempo Grid', time=0))
    tempo_track.append(MetaMessage('set_tempo', tempo=tempo_us, time=0))
    tempo_track.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    tempo_track.append(MetaMessage('end_of_track', time=0))
    
    # Notes track
    notes_track = MidiTrack()
    mid.tracks.append(notes_track)
    notes_track.append(MetaMessage('track_name', name=track_name, time=0))
    
    events = []
    for n in notes:
        pitch = int(np.clip(n['pitch'], 21, 108))
        vel = int(n.get('velocity', 90))
        events.append({'time': float(n['start']), 'type': 'on', 'pitch': pitch, 'vel': vel})
        events.append({'time': float(n['end']), 'type': 'off', 'pitch': pitch, 'vel': 0})
        
    events.sort(key=lambda x: (x['time'], 0 if x['type'] == 'off' else 1))
    
    ticks_per_sec = (480 * bpm) / 60.0
    last_ticks = 0
    for e in events:
        current_ticks = int(round(e['time'] * ticks_per_sec))
        delta = max(0, current_ticks - last_ticks)
        last_ticks = current_ticks
        if e['type'] == 'on':
            notes_track.append(Message('note_on', note=e['pitch'], velocity=e['vel'], time=delta))
        else:
            notes_track.append(Message('note_off', note=e['pitch'], velocity=0, time=delta))
            
    notes_track.append(MetaMessage('end_of_track', time=0))
    mid.save(output_midi_path)
    return output_midi_path

def merge_layers(
    song_id=None,
    source_layer_ids=None,
    target_layer_id="acoustic_guitar",
    target_name="Acoustic Guitar (Full Range)",
    target_clef="grand_staff",
    target_icon="🎸",
    target_color="#10b981",
    replace_sources=True
):
    """
    Merges multiple source layers into a single cohesive layer.
    Perfect for combining mistakenly split acoustic guitar (bass + strumming) or multitrack piano.
    """
    if not source_layer_ids or len(source_layer_ids) < 2:
        return {"success": False, "error": "At least two source layers are required to merge"}
        
    song_id = song_id or get_current_song_id()
    manifest_path = os.path.join(AUDIO_DIR, "song_manifest.json")
    
    # 1. Load active manifest
    manifest_data = None
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
    elif song_id:
        manifest_data = load_manifest_from_db(song_id)
        
    if not manifest_data:
        return {"success": False, "error": "No manifest or song found"}

    bpm = float(manifest_data.get("original_bpm", 120.0))

    # 2. Audio Stem Summation & Peak Normalization
    loaded_audios = []
    target_sr = None
    max_len = 0
    
    for lid in source_layer_ids:
        stem_path = find_stem_file(lid)
        if stem_path and os.path.exists(stem_path):
            y, sr = sf.read(stem_path)
            if target_sr is None:
                target_sr = sr
            elif sr != target_sr:
                y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
            loaded_audios.append(y)
            if len(y) > max_len:
                max_len = len(y)
        else:
            print(f"[Surgery] Warning: stem file for layer '{lid}' not found.")

    if not loaded_audios:
        return {"success": False, "error": "None of the source audio stems could be found"}

    # Pad and sum
    is_stereo = any(a.ndim > 1 for a in loaded_audios)
    if is_stereo:
        summed = np.zeros((max_len, 2), dtype=np.float32)
        for a in loaded_audios:
            if a.ndim == 1:
                a_stereo = np.column_stack([a, a])
            else:
                a_stereo = a
            curr_len = len(a_stereo)
            summed[:curr_len] += a_stereo.astype(np.float32)
    else:
        summed = np.zeros(max_len, dtype=np.float32)
        for a in loaded_audios:
            curr_len = len(a)
            summed[:curr_len] += a.astype(np.float32)

    # Headroom management / Soft Peak Limiting
    peak = float(np.max(np.abs(summed)))
    if peak > 0.95:
        # Scale down to -0.7 dBFS (0.92) to prevent clipping
        scale = 0.92 / peak
        summed *= scale
        print(f"[Surgery] Peak {peak:.3f} exceeded 0.95. Soft limited by factor {scale:.3f}")

    # Write merged audio stems
    os.makedirs(STEMS_DIR, exist_ok=True)
    out_stem_path = os.path.join(STEMS_DIR, f"{target_layer_id}.wav")
    out_audio_path = os.path.join(AUDIO_DIR, f"{target_layer_id}.wav")
    sf.write(out_stem_path, summed, target_sr or 44100, subtype='PCM_16')
    sf.write(out_audio_path, summed, target_sr or 44100, subtype='PCM_16')

    # 3. Notes Merging & Deduplication
    merged_notes = []
    for lid in source_layer_ids:
        n_path = find_notes_file(lid)
        if n_path and os.path.exists(n_path):
            try:
                with open(n_path, 'r', encoding='utf-8') as f:
                    notes_list = json.load(f)
                    for n in notes_list:
                        n_copy = dict(n)
                        n_copy["source_layer"] = lid
                        n_copy["instrument"] = target_layer_id
                        merged_notes.append(n_copy)
            except Exception as e:
                print(f"[Surgery] Error reading notes for {lid}: {e}")

    # Sort chronologically by start time, then pitch
    merged_notes.sort(key=lambda x: (x.get('start', 0.0), x.get('pitch', 60)))

    # Deduplicate notes starting within 40ms with same pitch
    deduped_notes = []
    for n in merged_notes:
        if not deduped_notes:
            deduped_notes.append(n)
            continue
        prev = deduped_notes[-1]
        if abs(n.get('start', 0) - prev.get('start', 0)) < 0.04 and n.get('pitch') == prev.get('pitch'):
            # Merge duration
            prev['end'] = max(prev.get('end', 0), n.get('end', 0))
        else:
            deduped_notes.append(n)

    out_notes_path = os.path.join(AUDIO_DIR, f"{target_layer_id}_notes.json")
    with open(out_notes_path, 'w', encoding='utf-8') as f:
        json.dump(deduped_notes, f, indent=2)

    # 4. Generate Merged MIDI
    out_midi_path = os.path.join(MIDI_DIR, f"{target_layer_id}.mid")
    write_midi_file(deduped_notes, out_midi_path, bpm=int(round(bpm)), track_name=target_name)

    # 5. Compute Metrics
    metrics = compute_layer_metrics(out_stem_path)

    # 6. Update Manifest & Database
    new_layer = {
        "id": target_layer_id,
        "name": target_name,
        "icon": target_icon,
        "type": "harmonic_chords",
        "color": target_color,
        "clef": target_clef,
        "has_lyrics": False,
        "pitch_locked": False,
        "default_instrument": "guitar" if "guitar" in target_layer_id else "synth",
        "is_active": True,
        "metrics": metrics,
        "audio_file": f"/audio/audio/stems/{target_layer_id}.wav",
        "waveform_endpoint": f"/api/waveform/{target_layer_id}",
        "notes_file": f"/audio/audio/{target_layer_id}_notes.json",
        "midi_file": f"/audio/midi/{target_layer_id}.mid",
        "num_notes": len(deduped_notes),
        "parent_layers": source_layer_ids
    }

    # Update layers list in manifest
    updated_layers = []
    replaced = False
    for l in manifest_data.get("layers", []):
        if l["id"] in source_layer_ids:
            if replace_sources:
                # Deactivate source layers
                l["is_active"] = False
                l["merged_into"] = target_layer_id
            updated_layers.append(l)
        elif l["id"] == target_layer_id:
            # Overwrite existing layer with new merged config
            updated_layers.append(new_layer)
            replaced = True
        else:
            updated_layers.append(l)

    if not replaced:
        updated_layers.append(new_layer)

    manifest_data["layers"] = updated_layers
    manifest_data["active_layers_count"] = sum(1 for l in updated_layers if l.get("is_active", True))

    # Save manifest file
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    # Save to SQLite
    save_manifest_to_db(manifest_data, set_current=True)

    print(f"[Surgery] Successfully merged {source_layer_ids} -> '{target_layer_id}' ({target_name}) with {len(deduped_notes)} notes.")
    return {
        "success": True,
        "merged_layer": new_layer,
        "manifest": manifest_data,
        "num_notes": len(deduped_notes),
        "audio_stem": out_stem_path
    }

def split_layer(
    song_id=None,
    source_layer_id="guitar",
    crossover_freq=200.0,
    low_id=None,
    high_id=None,
    low_name=None,
    high_name=None
):
    """
    Splits a single layer into Low and High frequency/pitch components.
    Uses 4th-order Linkwitz-Riley equivalent crossover filter for perfect audio reconstruction
    and splits note transcriptions at MIDI pitch 60 (C4).
    """
    song_id = song_id or get_current_song_id()
    manifest_path = os.path.join(AUDIO_DIR, "song_manifest.json")
    
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
    else:
        manifest_data = load_manifest_from_db(song_id)

    if not manifest_data:
        return {"success": False, "error": "No manifest or song found"}

    source_stem = find_stem_file(source_layer_id)
    if not source_stem or not os.path.exists(source_stem):
        return {"success": False, "error": f"Audio stem for '{source_layer_id}' not found"}

    low_id = low_id or f"{source_layer_id}_low"
    high_id = high_id or f"{source_layer_id}_high"
    low_name = low_name or f"{source_layer_id.capitalize()} (Low Register / Bass)"
    high_name = high_name or f"{source_layer_id.capitalize()} (Upper Register / Chords)"

    # 1. Load Audio
    y, sr = sf.read(source_stem)
    nyquist = sr / 2.0
    cutoff_norm = min(0.99, max(0.01, crossover_freq / nyquist))

    # 2. Linkwitz-Riley Crossover (cascaded 2nd-order Butterworth = 4th order, zero-phase via filtfilt)
    b_low, a_low = signal.butter(2, cutoff_norm, btype='low')
    b_high, a_high = signal.butter(2, cutoff_norm, btype='high')

    if y.ndim > 1:
        y_low = np.zeros_like(y)
        y_high = np.zeros_like(y)
        for ch in range(y.shape[1]):
            # First pass
            l_pass = signal.filtfilt(b_low, a_low, y[:, ch])
            h_pass = signal.filtfilt(b_high, a_high, y[:, ch])
            y_low[:, ch] = l_pass
            y_high[:, ch] = h_pass
    else:
        y_low = signal.filtfilt(b_low, a_low, y)
        y_high = signal.filtfilt(b_high, a_high, y)

    # Write split stems
    low_stem_path = os.path.join(STEMS_DIR, f"{low_id}.wav")
    high_stem_path = os.path.join(STEMS_DIR, f"{high_id}.wav")
    sf.write(low_stem_path, y_low.astype(np.float32), sr, subtype='PCM_16')
    sf.write(high_stem_path, y_high.astype(np.float32), sr, subtype='PCM_16')
    sf.write(os.path.join(AUDIO_DIR, f"{low_id}.wav"), y_low.astype(np.float32), sr, subtype='PCM_16')
    sf.write(os.path.join(AUDIO_DIR, f"{high_id}.wav"), y_high.astype(np.float32), sr, subtype='PCM_16')

    # 3. Partition Notes
    notes_file = find_notes_file(source_layer_id)
    low_notes, high_notes = [], []
    if notes_file and os.path.exists(notes_file):
        try:
            with open(notes_file, 'r', encoding='utf-8') as f:
                all_notes = json.load(f)
            for n in all_notes:
                p = n.get('pitch', 60)
                if p < 60: # Below C4 -> Low
                    nl = dict(n)
                    nl['instrument'] = low_id
                    low_notes.append(nl)
                else:      # C4 and above -> High
                    nh = dict(n)
                    nh['instrument'] = high_id
                    high_notes.append(nh)
        except Exception as e:
            print(f"[Surgery] Error partitioning notes: {e}")

    with open(os.path.join(AUDIO_DIR, f"{low_id}_notes.json"), 'w', encoding='utf-8') as f:
        json.dump(low_notes, f, indent=2)
    with open(os.path.join(AUDIO_DIR, f"{high_id}_notes.json"), 'w', encoding='utf-8') as f:
        json.dump(high_notes, f, indent=2)

    bpm = float(manifest_data.get("original_bpm", 120.0))
    write_midi_file(low_notes, os.path.join(MIDI_DIR, f"{low_id}.mid"), bpm=int(round(bpm)), track_name=low_name)
    write_midi_file(high_notes, os.path.join(MIDI_DIR, f"{high_id}.mid"), bpm=int(round(bpm)), track_name=high_name)

    # 4. Metrics & Manifest Update
    low_layer = {
        "id": low_id,
        "name": low_name,
        "icon": "🎸",
        "type": "bass",
        "color": "#ffaa00",
        "clef": "bass",
        "has_lyrics": False,
        "pitch_locked": False,
        "default_instrument": "bass",
        "is_active": True,
        "metrics": compute_layer_metrics(low_stem_path),
        "audio_file": f"/audio/audio/stems/{low_id}.wav",
        "waveform_endpoint": f"/api/waveform/{low_id}",
        "notes_file": f"/audio/audio/{low_id}_notes.json",
        "midi_file": f"/audio/midi/{low_id}.mid",
        "num_notes": len(low_notes),
        "parent_layers": [source_layer_id]
    }

    high_layer = {
        "id": high_id,
        "name": high_name,
        "icon": "🎸",
        "type": "harmonic_chords",
        "color": "#10b981",
        "clef": "treble",
        "has_lyrics": False,
        "pitch_locked": False,
        "default_instrument": "guitar",
        "is_active": True,
        "metrics": compute_layer_metrics(high_stem_path),
        "audio_file": f"/audio/audio/stems/{high_id}.wav",
        "waveform_endpoint": f"/api/waveform/{high_id}",
        "notes_file": f"/audio/audio/{high_id}_notes.json",
        "midi_file": f"/audio/midi/{high_id}.mid",
        "num_notes": len(high_notes),
        "parent_layers": [source_layer_id]
    }

    # Update manifest
    updated_layers = []
    for l in manifest_data.get("layers", []):
        if l["id"] == source_layer_id:
            l["is_active"] = False
            l["split_into"] = [low_id, high_id]
            updated_layers.append(l)
        else:
            updated_layers.append(l)
    updated_layers.extend([low_layer, high_layer])

    manifest_data["layers"] = updated_layers
    manifest_data["active_layers_count"] = sum(1 for l in updated_layers if l.get("is_active", True))

    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    save_manifest_to_db(manifest_data, set_current=True)

    print(f"[Surgery] Successfully split '{source_layer_id}' at {crossover_freq} Hz into '{low_id}' and '{high_id}'.")
    return {
        "success": True,
        "low_layer": low_layer,
        "high_layer": high_layer,
        "manifest": manifest_data
    }
