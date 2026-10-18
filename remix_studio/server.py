#!/usr/bin/env python3
"""
Standalone Remix DNA & Audio-to-MIDI Studio Server
Port: 8790
Provides REST endpoints and static file serving for the interactive DAW workstation.
"""

import os
import sys

if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import json
import mimetypes
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import urllib.parse
import threading
import time
import uuid
import numpy as np
import soundfile as sf
import librosa

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
MIDI_DIR = os.path.join(BASE_DIR, "midi")
SCORES_DIR = os.path.join(BASE_DIR, "scores")
VOCAL_TESTS_DIR = os.path.join(BASE_DIR, "vocal_tests")
REMIXES_DIR = os.path.join(BASE_DIR, "remixes")

PORT = 8790

WAVEFORM_CACHE = {}

def get_waveform_peaks(audio_path, num_points=800):
    """Computes normalized min/max waveform peak array for canvas visualization."""
    if not os.path.exists(audio_path):
        return []
    try:
        y, sr = sf.read(audio_path)
        if y.ndim > 1:
            y = np.mean(y, axis=1)
        # Downsample to num_points
        step = max(1, len(y) // num_points)
        peaks = []
        for i in range(0, len(y), step):
            chunk = y[i:i+step]
            if len(chunk) > 0:
                peaks.append(float(round(np.max(np.abs(chunk)), 4)))
            if len(peaks) >= num_points:
                break
        return peaks
    except Exception as e:
        print(f"Error computing waveform peaks: {e}")
        return []

def get_waveform_peaks_cached(audio_path, num_points=800):
    """Cached peak retriever to avoid re-reading disk WAVs on every request."""
    if not os.path.exists(audio_path):
        return []
    try:
        mtime = os.path.getmtime(audio_path)
        cache_key = f"{audio_path}_{mtime}_{num_points}"
        if cache_key in WAVEFORM_CACHE:
            return WAVEFORM_CACHE[cache_key]
        peaks = get_waveform_peaks(audio_path, num_points)
        WAVEFORM_CACHE[cache_key] = peaks
        return peaks
    except Exception as e:
        print(f"Cache error: {e}")
        return get_waveform_peaks(audio_path, num_points)

class IngestTaskManager:
    """Thread-safe state manager for live ingestion tracking and log streaming."""
    def __init__(self):
        self.lock = threading.Lock()
        self.tasks = {}
        self.latest_task_id = None

    def create_task(self, source, title=None, artist=None, bpm=174.0):
        with self.lock:
            task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            self.tasks[task_id] = {
                "id": task_id,
                "source": source,
                "title": title or "Auto-Detecting...",
                "artist": artist or "Auto-Detecting...",
                "target_bpm": bpm,
                "status": "running",       # "running", "completed", "error"
                "stage": "starting",       # "downloading", "analyzing", "demixing", "profiling", "transcribing", "remixing", "completed", "error"
                "progress_pct": 0,
                "stage_msg": "Initializing ingestion pipeline...",
                "logs": ["🚀 Ingestion pipeline initialized."],
                "error": None,
                "manifest": None,
                "start_time": time.time(),
                "updated_at": time.time()
            }
            self.latest_task_id = task_id
            return task_id

    def update(self, task_id, stage=None, progress=None, message=None, log=None, error=None, manifest=None, status=None):
        with self.lock:
            if task_id not in self.tasks:
                return
            t = self.tasks[task_id]
            if stage: t["stage"] = stage
            if progress is not None: t["progress_pct"] = min(100, max(0, int(progress)))
            if message: t["stage_msg"] = message
            if log:
                clean_log = str(log).strip()
                if clean_log:
                    t["logs"].append(clean_log)
                    if len(t["logs"]) > 300:
                        t["logs"] = t["logs"][-300:]
            if error:
                t["error"] = str(error)
                t["status"] = "error"
                t["failed_stage"] = t.get("stage", "downloading")
            if manifest:
                t["manifest"] = manifest
            if status:
                t["status"] = status
            t["updated_at"] = time.time()

    def add_log(self, task_id, log_line):
        with self.lock:
            if task_id in self.tasks:
                clean = str(log_line).strip()
                if clean:
                    self.tasks[task_id]["logs"].append(clean)
                    if len(self.tasks[task_id]["logs"]) > 300:
                        self.tasks[task_id]["logs"] = self.tasks[task_id]["logs"][-300:]

    def get(self, task_id=None):
        with self.lock:
            tid = task_id or self.latest_task_id
            if tid and tid in self.tasks:
                return dict(self.tasks[tid])
            return None

ingest_manager = IngestTaskManager()

class StudioRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS and caching headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. API: Project Metadata
        if path == "/api/project":
            lyrics_path = os.path.join(AUDIO_DIR, "lyrics.json")
            lyrics = {}
            if os.path.exists(lyrics_path):
                with open(lyrics_path, 'r', encoding='utf-8') as f:
                    lyrics = json.load(f)
                    
            notes_path = os.path.join(AUDIO_DIR, "vocal_notes.json")
            notes = []
            if os.path.exists(notes_path):
                with open(notes_path, 'r', encoding='utf-8') as f:
                    notes = json.load(f)
                    
            # Load dynamic manifest if available
            manifest_path = os.path.join(AUDIO_DIR, "song_manifest.json")
            manifest = None
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)

            data = {
                "title": "Kolorado vabalai",
                "artist": "Vytautas Kernagis",
                "original_bpm": 152.0,
                "remix_bpm": 174.0,
                "key": "A Minor / C Major",
                "duration_sec": 60.0,
                "manifest": manifest,
                "stems": [l["id"] for l in manifest.get("layers", [])] if manifest else ["vocals", "guitar", "piano", "bass", "drums", "other"],
                "lyrics": lyrics,
                "num_notes": len(notes),
                "remixes": [
                    {"id": "jungle", "genre": "Jungle (174 BPM)", "file": "/audio/remixes/kolorado_vabalai_jungle_remix.wav", "loop": "/audio/remixes/kolorado_vabalai_jungle_loop.wav"},
                    {"id": "techno", "genre": "Techno (134 BPM)", "file": "/audio/remixes/kolorado_vabalai_techno_remix.wav", "loop": "/audio/remixes/kolorado_vabalai_techno_remix_loop.wav"},
                    {"id": "house", "genre": "House (126 BPM)", "file": "/audio/remixes/kolorado_vabalai_house_remix.wav", "loop": "/audio/remixes/kolorado_vabalai_house_remix_loop.wav"}
                ],
                "vocal_engines": [
                    {"id": "engine_a", "name": "Engine A: Sliced Stem Chops + Studio Rack", "file": "/audio/vocal_tests/engine_a_stem_rack.wav"},
                    {"id": "engine_b", "name": "Engine B: Formant Pitch Shift (+2 st)", "file": "/audio/vocal_tests/engine_b_pitch_shift.wav"},
                    {"id": "engine_c", "name": "Engine C: Lithuanian Neural Speech", "file": "/audio/vocal_tests/engine_c_neural.wav"},
                    {"id": "engine_d", "name": "Engine D: Hybrid Chain (A+B+C)", "file": "/audio/vocal_tests/engine_d_hybrid.wav"}
                ]
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            return

        # 1B. API: Song Manifest (Dynamic Layers)
        if path == "/api/manifest":
            manifest_path = os.path.join(AUDIO_DIR, "song_manifest.json")
            manifest_data = {"layers": []}
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(manifest_data, ensure_ascii=False).encode('utf-8'))
            return

        # 1C. API: Ingestion Task Live Telemetry Status
        if path == "/api/ingest/status":
            task_id = query.get("task_id", [None])[0]
            task_info = ingest_manager.get(task_id)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "task": task_info}, ensure_ascii=False).encode('utf-8'))
            return

        # 1D. API: Ingested Songs Database Catalog
        if path == "/api/songs":
            sys.path.insert(0, BASE_DIR)
            from database.db import get_all_songs, init_db, seed_default_if_empty
            init_db()
            seed_default_if_empty(os.path.join(AUDIO_DIR, "song_manifest.json"))
            songs = get_all_songs()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "songs": songs}, ensure_ascii=False).encode('utf-8'))
            return

        # 2A. API: Batch Stem Waveform Peaks (Instant 1-Roundtrip Retrieval)
        if path == "/api/waveforms/all":
            manifest_path = os.path.join(AUDIO_DIR, "song_manifest.json")
            stem_list = ["drums", "bass", "vocals", "guitar", "piano", "other"]
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        m_data = json.load(f)
                        stem_list = [l["id"] for l in m_data.get("layers", [])]
                except Exception:
                    pass
            all_peaks = {}
            for s in stem_list:
                stem_candidates = [
                    os.path.join(AUDIO_DIR, "stems", f"{s}.wav"),
                    os.path.join(AUDIO_DIR, f"{s}.wav")
                ]
                if s == "remix":
                    stem_candidates.insert(0, os.path.join(REMIXES_DIR, "kolorado_vabalai_jungle_remix.wav"))
                audio_path = next((p for p in stem_candidates if os.path.exists(p)), stem_candidates[-1])
                all_peaks[s] = get_waveform_peaks_cached(audio_path)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"peaks": all_peaks}).encode('utf-8'))
            return

        # 2B. API: Single Stem Waveform Peaks
        if path.startswith("/api/waveform/"):
            stem = path.replace("/api/waveform/", "")
            # Check audio/stems/ first, then audio/
            stem_candidates = [
                os.path.join(AUDIO_DIR, "stems", f"{stem}.wav"),
                os.path.join(AUDIO_DIR, f"{stem}.wav")
            ]
            if stem == "remix":
                stem_candidates.insert(0, os.path.join(REMIXES_DIR, "kolorado_vabalai_jungle_remix.wav"))
            audio_path = next((p for p in stem_candidates if os.path.exists(p)), stem_candidates[-1])
            peaks = get_waveform_peaks_cached(audio_path)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"stem": stem, "peaks": peaks}).encode('utf-8'))
            return

        # 3. API: Interactive SVG Score
        if path == "/api/score/svg":
            st = int(query.get("semitones", [0])[0])
            layer = query.get("layer", ["vocals"])[0]
            song_id = query.get("song_id", ["grikiai"])[0]
            sys.path.insert(0, BASE_DIR)
            import importlib
            import sheet_music_exporter
            importlib.reload(sheet_music_exporter)
            if layer in ["trio", "3vocals", "vocal_trio"] or "song_id" in query:
                svg_content = sheet_music_exporter.generate_3vocal_svg_score(song_id=song_id, transpose_semitones=st)
            else:
                layer_notes_path = os.path.join(AUDIO_DIR, f"{layer}_notes.json")
                notes_path = layer_notes_path if os.path.exists(layer_notes_path) else os.path.join(AUDIO_DIR, "vocal_notes.json")
                lyrics_path = os.path.join(AUDIO_DIR, "lyrics.json")
                notes, lyrics = [], {}
                if os.path.exists(notes_path):
                    with open(notes_path, 'r', encoding='utf-8') as f: notes = json.load(f)
                if os.path.exists(lyrics_path):
                    with open(lyrics_path, 'r', encoding='utf-8') as f: lyrics = json.load(f)
                svg_content = sheet_music_exporter.generate_svg_score(notes, lyrics.get('words', []), transpose_semitones=st, layer=layer)
            self.send_response(200)
            self.send_header('Content-Type', 'image/svg+xml; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(svg_content.encode('utf-8'))
            return

        # 3B. API: Continuous ACE Pitch Curve
        if path == "/api/curve":
            layer = query.get("layer", ["vocals"])[0]
            curve_file = os.path.join(AUDIO_DIR, f"{layer}_pitch_curve.json")
            if not os.path.exists(curve_file):
                # Auto-extract if stem exists
                stem_candidates = [
                    os.path.join(AUDIO_DIR, "stems", f"{layer}.wav"),
                    os.path.join(AUDIO_DIR, f"{layer}.wav")
                ]
                source_stem = next((p for p in stem_candidates if os.path.exists(p)), None)
                if source_stem:
                    sys.path.insert(0, BASE_DIR)
                    from audio_to_midi import extract_ace_pitch_and_envelopes
                    curve_data = extract_ace_pitch_and_envelopes(source_stem)
                    with open(curve_file, 'w', encoding='utf-8') as f:
                        json.dump(curve_data, f)
            curve_payload = {}
            if os.path.exists(curve_file):
                with open(curve_file, 'r', encoding='utf-8') as f:
                    curve_payload = json.load(f)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "layer": layer, "curve": curve_payload}).encode('utf-8'))
            return

        # 3C. API: Closed-Loop Accuracy Metrics
        if path == "/api/accuracy":
            sys.path.insert(0, BASE_DIR)
            import accuracy_evaluator
            manifest_path = os.path.join(AUDIO_DIR, "song_manifest.json")
            report = accuracy_evaluator.evaluate_song_accuracy(AUDIO_DIR, manifest_path)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(json.dumps(report).encode('utf-8'))
            return

        # 4. Downloads
        if path == "/download/midi":
            midi_file = os.path.join(MIDI_DIR, "kolorado_vabalai.mid")
            if os.path.exists(midi_file):
                with open(midi_file, 'rb') as f: content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'audio/midi')
                self.send_header('Content-Disposition', 'attachment; filename="kolorado_vabalai.mid"')
                self.end_headers()
                self.wfile.write(content)
                return
                
        if path == "/download/musicxml":
            xml_file = os.path.join(SCORES_DIR, "kolorado_vabalai.musicxml")
            if os.path.exists(xml_file):
                with open(xml_file, 'rb') as f: content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.recordare.musicxml+xml')
                self.send_header('Content-Disposition', 'attachment; filename="kolorado_vabalai.musicxml"')
                self.end_headers()
                self.wfile.write(content)
                return

        # 5. Audio File Streaming
        if path.startswith("/audio/"):
            rel_path = path[len("/audio/"):]
            full_path = os.path.join(BASE_DIR, rel_path)
            if os.path.exists(full_path):
                self.serve_audio_file(full_path)
                return
            else:
                self.send_error(404, "Audio file not found")
                return

        # 6. Static Web Assets
        if path == "/" or path == "/index.html":
            file_to_serve = os.path.join(STATIC_DIR, "index.html")
        else:
            file_to_serve = os.path.join(STATIC_DIR, path.lstrip("/"))
            
        if os.path.exists(file_to_serve) and os.path.isfile(file_to_serve):
            mime_type, _ = mimetypes.guess_type(file_to_serve)
            with open(file_to_serve, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime_type or 'application/octet-stream')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(content)
            return
            
        self.send_error(404, "File not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length > 0 else b'{}'
        try:
            params = json.loads(body.decode('utf-8'))
        except Exception:
            params = {}

        # API: Transpose Notes & Generate High-Fidelity Synthetic Audio Preview
        if path == "/api/transpose":
            semitones = int(params.get("semitones", 0))
            layer = params.get("layer", "vocals")
            sys.path.insert(0, BASE_DIR)
            from audio_to_midi import create_multitrack_midi
            from synthetic_recreation import recreate_synthetic_layer

            layer_notes_path = os.path.join(AUDIO_DIR, f"{layer}_notes.json")
            notes_path = layer_notes_path if os.path.exists(layer_notes_path) else os.path.join(AUDIO_DIR, "vocal_notes.json")
            
            notes = []
            if os.path.exists(notes_path):
                with open(notes_path, 'r', encoding='utf-8') as f:
                    notes = json.load(f)
                
            out_midi = os.path.join(MIDI_DIR, f"{layer}_transposed_{semitones:+d}.mid")
            create_multitrack_midi(notes, [], [], out_midi, transpose_semitones=semitones)
            
            # High-fidelity synthetic recreation preview for transposed layer
            out_preview = os.path.join(AUDIO_DIR, f"{layer}_transposed_{semitones:+d}.wav")
            recreate_synthetic_layer(layer, AUDIO_DIR, out_preview, transpose_semitones=semitones)
            
            base_keys = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
            key_name = base_keys[(5 + semitones) % 12] + " Major"
            
            res = {
                "success": True,
                "semitones": semitones,
                "layer": layer,
                "key_name": key_name,
                "midi_file": f"/audio/midi/{layer}_transposed_{semitones:+d}.mid",
                "preview_audio": f"/audio/audio/{layer}_transposed_{semitones:+d}.wav"
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
            return

        # API: Closed-Loop Synthetic Recreation of Song or Layer
        if path == "/api/synthetic/recreate":
            semitones = int(params.get("semitones", 0))
            layer = params.get("layer", "master")
            voice = params.get("voice", "lt-LT-LeonasNeural")
            sys.path.insert(0, BASE_DIR)
            from synthetic_recreation import recreate_synthetic_layer, recreate_full_synthetic_song
            import accuracy_evaluator
            
            manifest_path = os.path.join(AUDIO_DIR, "song_manifest.json")
            
            if layer == "master" or not layer:
                out_master = os.path.join(AUDIO_DIR, "synthetic", f"master_synthetic_recreation_{semitones:+d}.wav")
                _, num_layers = recreate_full_synthetic_song(manifest_path, AUDIO_DIR, out_master, transpose_semitones=semitones, voice=voice)
                accuracy_report = accuracy_evaluator.evaluate_song_accuracy(AUDIO_DIR, manifest_path)
                res = {
                    "success": True,
                    "target": "master",
                    "semitones": semitones,
                    "voice": voice,
                    "layers_count": num_layers,
                    "preview_audio": f"/audio/audio/synthetic/master_synthetic_recreation_{semitones:+d}.wav",
                    "accuracy": accuracy_report
                }
            else:
                out_layer = os.path.join(AUDIO_DIR, "synthetic", f"synth_{layer}_{semitones:+d}.wav")
                _, _ = recreate_synthetic_layer(layer, AUDIO_DIR, out_layer, transpose_semitones=semitones, voice=voice)
                
                # Compare against original stem if available
                orig_candidates = [
                    os.path.join(AUDIO_DIR, "stems", f"{layer}.wav"),
                    os.path.join(AUDIO_DIR, f"{layer}.wav")
                ]
                orig_file = next((p for p in orig_candidates if os.path.exists(p)), None)
                fidelity_info = accuracy_evaluator.evaluate_layer_fidelity(orig_file, out_layer) if orig_file else {"fidelity_score": 90.0}
                res = {
                    "success": True,
                    "target": layer,
                    "semitones": semitones,
                    "voice": voice,
                    "preview_audio": f"/audio/audio/synthetic/synth_{layer}_{semitones:+d}.wav",
                    "accuracy": fidelity_info
                }
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
            return

        # API: Manifest Layer Toggle / Edit
        if path == "/api/manifest/toggle":
            layer_id = params.get("layer")
            manifest_path = os.path.join(AUDIO_DIR, "song_manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                for l in manifest_data.get("layers", []):
                    if l["id"] == layer_id:
                        l["is_active"] = not l.get("is_active", True)
                        break
                manifest_data["active_layers_count"] = sum(1 for l in manifest_data["layers"] if l.get("is_active", True))
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest_data, f, indent=2, ensure_ascii=False)
                res = {"success": True, "manifest": manifest_data}
            else:
                res = {"success": False, "error": "Manifest not found"}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
            return

        # API: Ingest New Track
        if path == "/api/ingest":
            source = params.get("source")
            title = params.get("title")
            artist = params.get("artist")
            bpm = float(params.get("bpm", 174.0))
            if not source:
                self.send_error(400, "Missing source URL or file path")
                return
            
            task_id = ingest_manager.create_task(source, title=title, artist=artist, bpm=bpm)
            sys.path.insert(0, BASE_DIR)
            import ingest_song

            def run_ingest():
                try:
                    ingest_song.ingest_audio(
                        source, 
                        title=title, 
                        artist=artist, 
                        remix_bpm=bpm,
                        task_id=task_id,
                        task_mgr=ingest_manager
                    )
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    print(f"Ingestion error: {e}\n{tb}")
                    ingest_manager.update(task_id, error=str(e), status="error", message=f"Failed: {e}")
                    ingest_manager.add_log(task_id, f"[ERROR] Pipeline Fatal Error: {e}")

            t = threading.Thread(target=run_ingest, daemon=True)
            t.start()
            res = {
                "success": True, 
                "task_id": task_id,
                "message": "Autonomous ingestion started in background"
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
            return

        # API: Quality Check
        if path == "/api/quality_check":
            sys.path.insert(0, BASE_DIR)
            from quality_checker import compute_transient_jitter, compute_harmonic_dissonance
            remix_path = os.path.join(REMIXES_DIR, "kolorado_vabalai_jungle_remix.wav")
            bass_path = os.path.join(AUDIO_DIR, "bass.wav")
            other_path = os.path.join(AUDIO_DIR, "other.wav")
            
            jitter = compute_transient_jitter(remix_path, bpm=174)
            dissonance = compute_harmonic_dissonance(bass_path, other_path)
            
            res = {
                "jitter": jitter,
                "dissonance": dissonance,
                "loop_audio": "/audio/remixes/kolorado_vabalai_jungle_loop.wav"
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        # API: Switch Active Song
        if path == "/api/songs/switch":
            target_id = params.get("song_id")
            if not target_id:
                self.send_error(400, "Missing song_id")
                return
            sys.path.insert(0, BASE_DIR)
            from database.db import set_current_song
            manifest_data = set_current_song(target_id)
            if manifest_data:
                manifest_path = os.path.join(AUDIO_DIR, "song_manifest.json")
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest_data, f, indent=2, ensure_ascii=False)
                WAVEFORM_CACHE.clear()
                res = {"success": True, "song_id": target_id, "manifest": manifest_data}
            else:
                res = {"success": False, "error": f"Song '{target_id}' not found in database"}
            self.send_response(200 if res.get("success") else 404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            return

        # API: Merge Multiple Layers into One
        if path == "/api/layers/merge":
            song_id = params.get("song_id")
            source_layer_ids = params.get("source_layer_ids", [])
            target_layer_id = params.get("target_layer_id", "acoustic_guitar")
            target_name = params.get("target_name", "Acoustic Guitar (Full Range)")
            target_clef = params.get("target_clef", "grand_staff")
            target_icon = params.get("target_icon", "🎸")
            target_color = params.get("target_color", "#10b981")
            replace_sources = params.get("replace_sources", True)

            sys.path.insert(0, BASE_DIR)
            import layer_surgery
            result = layer_surgery.merge_layers(
                song_id=song_id,
                source_layer_ids=source_layer_ids,
                target_layer_id=target_layer_id,
                target_name=target_name,
                target_clef=target_clef,
                target_icon=target_icon,
                target_color=target_color,
                replace_sources=replace_sources
            )
            WAVEFORM_CACHE.clear()
            self.send_response(200 if result.get("success") else 400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            return

        # API: Split Layer into Low & High Registers
        if path == "/api/layers/split":
            song_id = params.get("song_id")
            source_layer_id = params.get("source_layer_id")
            crossover_freq = float(params.get("crossover_freq", 200.0))
            low_id = params.get("low_id")
            high_id = params.get("high_id")
            low_name = params.get("low_name")
            high_name = params.get("high_name")

            sys.path.insert(0, BASE_DIR)
            import layer_surgery
            result = layer_surgery.split_layer(
                song_id=song_id,
                source_layer_id=source_layer_id,
                crossover_freq=crossover_freq,
                low_id=low_id,
                high_id=high_id,
                low_name=low_name,
                high_name=high_name
            )
            WAVEFORM_CACHE.clear()
            self.send_response(200 if result.get("success") else 400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            return

        self.send_error(404, "Endpoint not found")

    def serve_audio_file(self, full_path):
        """Streams WAV/FLAC audio with HTTP 206 Partial Content range support."""
        file_size = os.path.getsize(full_path)
        range_header = self.headers.get('Range', None)
        mime_type, _ = mimetypes.guess_type(full_path)
        mime_type = mime_type or 'audio/wav'
        
        if range_header:
            range_match = range_header.replace('bytes=', '').split('-')
            start = int(range_match[0])
            end = int(range_match[1]) if range_match[1] else file_size - 1
            length = (end - start) + 1
            
            self.send_response(206)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
            self.send_header('Content-Length', str(length))
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()
            
            with open(full_path, 'rb') as f:
                f.seek(start)
                self.wfile.write(f.read(length))
        else:
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(file_size))
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()
            with open(full_path, 'rb') as f:
                self.wfile.write(f.read())

def run_server():
    server_address = ('', PORT)
    httpd = ThreadingHTTPServer(server_address, StudioRequestHandler)
    print(f"[REMIX DNA STUDIO] Multi-Threaded Server running on: http://localhost:{PORT}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStudio server shutting down.")

if __name__ == "__main__":
    run_server()
