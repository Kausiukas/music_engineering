#!/usr/bin/env python3
"""
Autonomous Multi-Song Ingestion Pipeline for REMIX DNA STUDIO
Equipped with Real-Time Telemetry, Line-by-Line Log Streaming & Stage Progress Reporting.

Usage:
    python ingest_song.py <youtube_url_or_filepath> [--title "Song Title"] [--artist "Artist"] [--remix_bpm 174]
"""

import os
import studio_paths
import sys
import argparse
import subprocess
import json
import shutil
import re
import time

if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import numpy as np
import soundfile as sf
import librosa

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = studio_paths.AUDIO_DIR
STEMS_DIR = studio_paths.STEMS_DIR
REMIXES_DIR = studio_paths.REMIXES_DIR
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(STEMS_DIR, exist_ok=True)
os.makedirs(REMIXES_DIR, exist_ok=True)

def sanitize_id(text):
    text = re.sub(r'[^a-zA-Z0-9_-]', '_', text.lower())
    return re.sub(r'_+', '_', text).strip('_')

def run_command_streaming(cmd, task_id=None, task_mgr=None, prefix=""):
    """Runs a subprocess command and streams its output line-by-line to both stdout and task_mgr."""
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1
    )
    for line in iter(proc.stdout.readline, ''):
        stripped = line.strip()
        if stripped:
            print(f"{prefix}{stripped}")
            if task_mgr and task_id:
                task_mgr.add_log(task_id, f"{prefix}{stripped}")
    proc.stdout.close()
    returncode = proc.wait()
    if returncode != 0:
        raise RuntimeError(f"Command failed with exit code {returncode}: {' '.join(cmd)}")
    return returncode

def ingest_audio(source_input, title=None, artist=None, remix_bpm=174.0, max_duration=90.0, task_id=None, task_mgr=None, on_manifest_saved=None):
    def notify(stage, pct, msg, log_line=None):
        print(f"[{pct:>3}%] [{stage.upper()}] {msg}")
        if task_mgr and task_id:
            task_mgr.update(task_id, stage=stage, progress=pct, message=msg, log=log_line or msg)

    notify("starting", 5, "Initializing ingestion pipeline...")
    
    # Step 1: Ingest Audio
    is_url = source_input.startswith("http://") or source_input.startswith("https://") or "youtube.com" in source_input or "youtu.be" in source_input
    
    if is_url:
        notify("downloading", 10, f"Querying YouTube metadata: {source_input}...")
        meta_cmd = ["yt-dlp", "--dump-json", "--extractor-args", "youtube:player_client=android,web", "--no-check-certificates", source_input]
        meta_res = subprocess.run(meta_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
        detected_title = "Unknown Track"
        detected_artist = "Unknown Artist"
        if meta_res.returncode == 0 and meta_res.stdout:
            try:
                meta_json = json.loads(meta_res.stdout)
                detected_title = meta_json.get("title", detected_title)
                detected_artist = meta_json.get("uploader", meta_json.get("channel", detected_artist))
            except Exception:
                pass
        
        final_title = title if title else detected_title
        final_artist = artist if artist else detected_artist
        song_id = sanitize_id(f"{final_artist}_{final_title}")
        raw_wav = os.path.join(AUDIO_DIR, f"{song_id}_raw.wav")
        
        notify("downloading", 15, f"Downloading audio for '{final_title}' by {final_artist}...", log_line=f"Song: {final_title} | Artist: {final_artist}")
        
        dl_cmd = [
            "yt-dlp",
            "-x",
            "--audio-format", "wav",
            "--audio-quality", "0",
            "--extractor-args", "youtube:player_client=android,web",
            "--no-check-certificates",
            "-o", raw_wav,
            source_input
        ]
        try:
            run_command_streaming(dl_cmd, task_id=task_id, task_mgr=task_mgr, prefix="[yt-dlp] ")
        except Exception as e:
            notify("downloading", 18, "Primary format failed; retrying with audio extraction fallback...")
            fallback_cmd = [
                "yt-dlp",
                "-f", "ba/b",
                "-x",
                "--audio-format", "wav",
                "--no-check-certificates",
                "-o", raw_wav,
                source_input
            ]
            run_command_streaming(fallback_cmd, task_id=task_id, task_mgr=task_mgr, prefix="[yt-dlp fallback] ")
            
        if not os.path.exists(raw_wav) and os.path.exists(raw_wav + ".wav"):
            raw_wav = raw_wav + ".wav"
    else:
        notify("downloading", 10, f"Reading local audio file: {source_input}...")
        base_name = os.path.splitext(os.path.basename(source_input))[0]
        final_title = title if title else base_name
        final_artist = artist if artist else "Original Artist"
        song_id = sanitize_id(base_name)
        raw_wav = source_input
        
    notify("downloading", 22, "Standardizing audio format to 44.1kHz stereo WAV...")
    clean_wav = os.path.join(AUDIO_DIR, f"{song_id}.wav")
    y, sr = librosa.load(raw_wav, sr=44100, mono=False)
    if y.ndim == 1:
        y = np.stack([y, y])
    
    total_sec = y.shape[1] / 44100.0
    duration_to_use = min(total_sec, max_duration)
    max_samples = int(duration_to_use * 44100)
    y_trimmed = y[:, :max_samples]
    sf.write(clean_wav, y_trimmed.T, 44100, subtype='PCM_16')
    notify("downloading", 26, f"Audio prepared: {duration_to_use:.1f}s duration.")
    
    # Step 2: Tempo and Key Analysis
    notify("analyzing", 30, "Detecting original tempo and harmonic root key...")
    y_mono = librosa.to_mono(y_trimmed)
    tempo, _ = librosa.beat.beat_track(y=y_mono, sr=44100)
    detected_bpm = float(tempo[0] if isinstance(tempo, (list, np.ndarray)) else tempo)
    
    chroma = librosa.feature.chroma_cqt(y=y_mono, sr=44100)
    chroma_sum = np.sum(chroma, axis=1)
    pitch_names = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
    root_pitch = pitch_names[np.argmax(chroma_sum)]
    detected_key = f"{root_pitch} Major"
    notify("analyzing", 35, f"Analysis complete: {detected_bpm:.1f} BPM | Root Key: {detected_key}")
    
    # Step 3: Neural 6-Source Layer Separation
    notify("demixing", 40, "Running neural 6-source separation (HTDemucs 6s)...", log_line="Demixing: drums, bass, vocals, guitar, piano, other")
    from layer_discovery import run_6source_separation, compute_stem_metrics, INSTRUMENT_PROFILES, extract_instrument_notes
    stem_paths = run_6source_separation(clean_wav, output_dir=STEMS_DIR)
    notify("demixing", 65, "6-source neural separation finished successfully.")
    
    # Step 4: Dynamic Layer Discovery & Metrics
    notify("profiling", 70, "Computing 3-point objective presence metrics (RMS, duty cycle, onsets)...")
    discovered_layers = []
    for stem_id, path in stem_paths.items():
        metrics = compute_stem_metrics(path)
        profile = INSTRUMENT_PROFILES.get(stem_id, {
            "name": stem_id.capitalize(), "icon": "🎵", "type": "harmonic_other",
            "color": "#94a3b8", "clef": "treble", "has_lyrics": False, "pitch_locked": False, "default_instrument": "synth"
        })
        is_active = (metrics["verdict"] == "active")
        status_tag = "[ACTIVE]" if is_active else "[PRUNED]"
        notify("profiling", 73, f"Profiled {profile['name']}: {metrics['rms_db']} dBFS | Duty: {(metrics['active_duty_cycle']*100):.1f}% => {status_tag}")
        
        layer_info = {
            "id": stem_id,
            "name": profile["name"],
            "icon": profile["icon"],
            "type": profile["type"],
            "color": profile["color"],
            "clef": profile["clef"],
            "has_lyrics": profile["has_lyrics"],
            "pitch_locked": profile["pitch_locked"],
            "default_instrument": profile["default_instrument"],
            "is_active": is_active,
            "metrics": metrics,
            "audio_file": f"/audio/audio/stems/{stem_id}.wav",
            "waveform_endpoint": f"/api/waveform/{stem_id}"
        }
        
        notes_file = os.path.join(AUDIO_DIR, f"{stem_id}_notes.json")
        if stem_id == "vocals":
            layer_info["notes_file"] = f"/audio/audio/{stem_id}_notes.json"
        elif is_active and not profile["pitch_locked"]:
            notes = extract_instrument_notes(path, stem_id)
            with open(notes_file, 'w', encoding='utf-8') as f:
                json.dump(notes, f, indent=2, ensure_ascii=False)
            layer_info["notes_file"] = f"/audio/audio/{stem_id}_notes.json"
            layer_info["num_notes"] = len(notes)
        else:
            layer_info["notes_file"] = None
            
        discovered_layers.append(layer_info)
        
    active_count = sum(1 for l in discovered_layers if l["is_active"])
    manifest = {
        "song_id": song_id,
        "title": final_title,
        "artist": final_artist,
        "original_bpm": round(detected_bpm, 1),
        "remix_bpm": remix_bpm,
        "key": detected_key,
        "duration_sec": duration_to_use,
        "total_sources_scanned": len(discovered_layers),
        "active_layers_count": active_count,
        "layers": discovered_layers
    }
    
    manifest_path = os.path.join(AUDIO_DIR, "song_manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        
    # Persist in SQLite database
    try:
        from database.db import save_manifest_to_db
        save_manifest_to_db(manifest, set_current=True)
    except Exception as e:
        print(f"[DB] Error saving to db in ingest_song: {e}")
        
    notify("profiling", 78, f"Song manifest saved: {active_count} of {len(discovered_layers)} layers active.")
    
    # Let the caller (the studio server) drop caches that refer to the previous song.
    # (This used to `import server`, which loads a second copy of the module when the server runs
    # as __main__, so the live cache was never cleared.)
    if on_manifest_saved is not None:
        on_manifest_saved()
        
    # Step 5: Vocal & Lyric Transcription (if vocal stem active)
    vocal_stem = stem_paths.get("vocals")
    if vocal_stem and os.path.exists(vocal_stem):
        notify("transcribing", 82, "Transcribing lead vocal notes & phoneme timestamps...")
        try:
            from vocal_transcriber import transcribe_vocals
            transcribe_vocals(vocal_stem, os.path.join(AUDIO_DIR, "vocal_notes.json"), os.path.join(AUDIO_DIR, "lyrics.json"))
            vocal_notes_p = os.path.join(AUDIO_DIR, "vocal_notes.json")
            vocals_notes_p = os.path.join(AUDIO_DIR, "vocals_notes.json")
            if os.path.exists(vocal_notes_p):
                import shutil
                shutil.copyfile(vocal_notes_p, vocals_notes_p)
            notify("transcribing", 87, "Vocal contour & lyric transcription complete.")
        except Exception as e:
            notify("transcribing", 87, f"Vocal transcription note: {e}")
            
    # Step 6: Multi-Genre Generative Remix Engines
    notify("remixing", 90, f"Rendering generative dancefloor recreations (Jungle @ {remix_bpm} BPM, Techno, House)...")
    try:
        from multi_genre_engine import render_all_remixes
        render_all_remixes(clean_wav, stem_paths, detected_bpm)
        notify("remixing", 96, "Jungle, Techno, and House remixes rendered with vocal-forward ducking.")
    except Exception as e:
        notify("remixing", 96, f"Remix render note: {e}")
        
    notify("completed", 100, f"Ingestion complete! '{final_title}' by {final_artist} is live in studio.", log_line="🎉 MISSION COMPLETE: Studio ready.")
    if task_mgr and task_id:
        task_mgr.update(task_id, status="completed", manifest=manifest)
        
    return manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Multi-Song Ingestion Pipeline for REMIX DNA STUDIO")
    parser.add_argument("source", help="YouTube URL or local audio file path")
    parser.add_argument("--title", help="Song Title override")
    parser.add_argument("--artist", help="Artist Name override")
    parser.add_argument("--remix_bpm", type=float, default=174.0, help="Target remix BPM (default: 174.0 for Jungle)")
    parser.add_argument("--max_duration", type=float, default=60.0, help="Max duration in seconds to ingest (default: 60s)")
    args = parser.parse_args()
    
    ingest_audio(args.source, title=args.title, artist=args.artist, remix_bpm=args.remix_bpm, max_duration=args.max_duration)
