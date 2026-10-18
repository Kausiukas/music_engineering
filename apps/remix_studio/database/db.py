"""
Remix Studio SQLite Database Module
Manages persistent catalog of songs, dynamic stems/layers, and remixes.
Supports multi-song switching and layer surgery (merging/splitting).
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import studio_paths
import sqlite3
import json
import time

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = studio_paths.DB_PATH

def get_connection(db_path=None):
    path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(db_path=None):
    """Initializes tables and indices."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Songs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                artist TEXT,
                original_bpm REAL DEFAULT 120.0,
                remix_bpm REAL DEFAULT 174.0,
                key_signature TEXT DEFAULT 'C Major',
                duration_sec REAL DEFAULT 0.0,
                total_sources INTEGER DEFAULT 6,
                active_layers_count INTEGER DEFAULT 0,
                original_audio_path TEXT,
                manifest_path TEXT,
                is_current INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Layers Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS layers (
                song_id TEXT NOT NULL,
                id TEXT NOT NULL,
                name TEXT NOT NULL,
                icon TEXT DEFAULT '🎸',
                layer_type TEXT DEFAULT 'harmonic_chords',
                color TEXT DEFAULT '#10b981',
                clef TEXT DEFAULT 'treble',
                has_lyrics INTEGER DEFAULT 0,
                pitch_locked INTEGER DEFAULT 0,
                default_instrument TEXT DEFAULT 'synth',
                is_active INTEGER DEFAULT 1,
                audio_file TEXT,
                waveform_endpoint TEXT,
                notes_file TEXT,
                midi_file TEXT,
                num_notes INTEGER DEFAULT 0,
                rms_db REAL,
                active_duty_cycle REAL,
                onsets INTEGER,
                verdict TEXT,
                parent_layers TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (song_id, id),
                FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
            )
        """)
        
        # 3. Remixes Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS remixes (
                id TEXT PRIMARY KEY,
                song_id TEXT NOT NULL,
                genre TEXT NOT NULL,
                bpm REAL DEFAULT 174.0,
                audio_file TEXT NOT NULL,
                loop_file TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()

def save_manifest_to_db(manifest_data, db_path=None, set_current=True):
    """
    Persists a full song manifest dictionary into SQLite.
    Creates or updates the song record and its layer records.
    """
    init_db(db_path)
    song_id = manifest_data.get("song_id")
    if not song_id:
        song_id = f"song_{int(time.time())}"
        manifest_data["song_id"] = song_id
        
    title = manifest_data.get("title", "Untitled Project")
    artist = manifest_data.get("artist", "Unknown Artist")
    original_bpm = float(manifest_data.get("original_bpm", 120.0))
    remix_bpm = float(manifest_data.get("remix_bpm", 174.0))
    key_sig = manifest_data.get("key", "C Major")
    duration = float(manifest_data.get("duration_sec", 0.0))
    total_sources = int(manifest_data.get("total_sources_scanned", len(manifest_data.get("layers", []))))
    active_layers_count = int(manifest_data.get("active_layers_count", sum(1 for l in manifest_data.get("layers", []) if l.get("is_active", True))))
    orig_audio = manifest_data.get("original_audio_path", "")
    manifest_path = manifest_data.get("manifest_path", "")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        if set_current:
            cursor.execute("UPDATE songs SET is_current = 0")
            
        cursor.execute("""
            INSERT INTO songs (
                id, title, artist, original_bpm, remix_bpm, key_signature,
                duration_sec, total_sources, active_layers_count,
                original_audio_path, manifest_path, is_current, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                artist=excluded.artist,
                original_bpm=excluded.original_bpm,
                remix_bpm=excluded.remix_bpm,
                key_signature=excluded.key_signature,
                duration_sec=excluded.duration_sec,
                total_sources=excluded.total_sources,
                active_layers_count=excluded.active_layers_count,
                original_audio_path=excluded.original_audio_path,
                manifest_path=excluded.manifest_path,
                is_current=CASE WHEN ? = 1 THEN 1 ELSE is_current END,
                updated_at=CURRENT_TIMESTAMP
        """, (
            song_id, title, artist, original_bpm, remix_bpm, key_sig,
            duration, total_sources, active_layers_count, orig_audio,
            manifest_path, 1 if set_current else 0, 1 if set_current else 0
        ))
        
        # Save layers
        layers = manifest_data.get("layers", [])
        for layer in layers:
            lid = layer.get("id")
            lname = layer.get("name", lid)
            licon = layer.get("icon", "🎸")
            ltype = layer.get("type", "harmonic_chords")
            lcolor = layer.get("color", "#10b981")
            lclef = layer.get("clef", "treble")
            has_lyrics = 1 if layer.get("has_lyrics") else 0
            pitch_locked = 1 if layer.get("pitch_locked") else 0
            default_inst = layer.get("default_instrument", "synth")
            is_active = 1 if layer.get("is_active", True) else 0
            audio_file = layer.get("audio_file")
            wf_ep = layer.get("waveform_endpoint")
            notes_file = layer.get("notes_file")
            midi_file = layer.get("midi_file")
            num_notes = layer.get("num_notes", 0)
            
            metrics = layer.get("metrics") or {}
            rms_db = metrics.get("rms_db")
            active_duty_cycle = metrics.get("active_duty_cycle")
            onsets = metrics.get("onsets")
            verdict = metrics.get("verdict")
            parent_layers = json.dumps(layer.get("parent_layers", []))

            cursor.execute("""
                INSERT INTO layers (
                    song_id, id, name, icon, layer_type, color, clef,
                    has_lyrics, pitch_locked, default_instrument, is_active,
                    audio_file, waveform_endpoint, notes_file, midi_file,
                    num_notes, rms_db, active_duty_cycle, onsets, verdict,
                    parent_layers, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(song_id, id) DO UPDATE SET
                    name=excluded.name,
                    icon=excluded.icon,
                    layer_type=excluded.layer_type,
                    color=excluded.color,
                    clef=excluded.clef,
                    has_lyrics=excluded.has_lyrics,
                    pitch_locked=excluded.pitch_locked,
                    default_instrument=excluded.default_instrument,
                    is_active=excluded.is_active,
                    audio_file=excluded.audio_file,
                    waveform_endpoint=excluded.waveform_endpoint,
                    notes_file=excluded.notes_file,
                    midi_file=excluded.midi_file,
                    num_notes=excluded.num_notes,
                    rms_db=excluded.rms_db,
                    active_duty_cycle=excluded.active_duty_cycle,
                    onsets=excluded.onsets,
                    verdict=excluded.verdict,
                    parent_layers=excluded.parent_layers,
                    updated_at=CURRENT_TIMESTAMP
            """, (
                song_id, lid, lname, licon, ltype, lcolor, lclef,
                has_lyrics, pitch_locked, default_inst, is_active,
                audio_file, wf_ep, notes_file, midi_file, num_notes,
                rms_db, active_duty_cycle, onsets, verdict, parent_layers
            ))
            
        conn.commit()
    return song_id

def load_manifest_from_db(song_id, db_path=None):
    """Reconstructs the full manifest dictionary from SQLite for a given song."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM songs WHERE id = ?", (song_id,))
        song_row = cursor.fetchone()
        if not song_row:
            return None
            
        cursor.execute("SELECT * FROM layers WHERE song_id = ? ORDER BY rowid ASC", (song_id,))
        layer_rows = cursor.fetchall()
        
        layers = []
        for lr in layer_rows:
            try:
                parents = json.loads(lr["parent_layers"]) if lr["parent_layers"] else []
            except Exception:
                parents = []
                
            layer_dict = {
                "id": lr["id"],
                "name": lr["name"],
                "icon": lr["icon"],
                "type": lr["layer_type"],
                "color": lr["color"],
                "clef": lr["clef"],
                "has_lyrics": bool(lr["has_lyrics"]),
                "pitch_locked": bool(lr["pitch_locked"]),
                "default_instrument": lr["default_instrument"],
                "is_active": bool(lr["is_active"]),
                "metrics": {
                    "rms_db": lr["rms_db"],
                    "active_duty_cycle": lr["active_duty_cycle"],
                    "onsets": lr["onsets"],
                    "verdict": lr["verdict"]
                },
                "audio_file": lr["audio_file"],
                "waveform_endpoint": lr["waveform_endpoint"],
                "notes_file": lr["notes_file"],
                "midi_file": lr["midi_file"],
                "num_notes": lr["num_notes"],
                "parent_layers": parents
            }
            layers.append(layer_dict)
            
        manifest = {
            "song_id": song_row["id"],
            "title": song_row["title"],
            "artist": song_row["artist"],
            "original_bpm": song_row["original_bpm"],
            "remix_bpm": song_row["remix_bpm"],
            "key": song_row["key_signature"],
            "duration_sec": song_row["duration_sec"],
            "total_sources_scanned": song_row["total_sources"],
            "active_layers_count": song_row["active_layers_count"],
            "layers": layers
        }
        return manifest

def get_all_songs(db_path=None):
    """Returns list of all songs cataloged in the database with their metadata and layer count."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, 
                   COUNT(l.id) as total_layers,
                   SUM(CASE WHEN l.is_active = 1 THEN 1 ELSE 0 END) as active_layers
            FROM songs s
            LEFT JOIN layers l ON s.id = l.song_id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
        """)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "title": r["title"],
                "artist": r["artist"],
                "original_bpm": r["original_bpm"],
                "remix_bpm": r["remix_bpm"],
                "key": r["key_signature"],
                "duration_sec": r["duration_sec"],
                "total_layers": r["total_layers"],
                "active_layers": r["active_layers"] or 0,
                "is_current": bool(r["is_current"]),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"]
            })
        return result

def get_current_song_id(db_path=None):
    """Returns the currently active song_id."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM songs WHERE is_current = 1 LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row["id"]
        # Fallback to the latest updated song
        cursor.execute("SELECT id FROM songs ORDER BY updated_at DESC LIMIT 1")
        row = cursor.fetchone()
        return row["id"] if row else None

def set_current_song(song_id, db_path=None):
    """Sets the active song in the database and updates manifest.json on disk."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE songs SET is_current = 0")
        cursor.execute("UPDATE songs SET is_current = 1 WHERE id = ?", (song_id,))
        conn.commit()
    return load_manifest_from_db(song_id, db_path)

def seed_default_if_empty(manifest_json_path, db_path=None):
    """
    Seeds database from existing song_manifest.json if the database is currently empty.
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM songs")
        count = cursor.fetchone()["cnt"]
        if count == 0 and os.path.exists(manifest_json_path):
            try:
                with open(manifest_json_path, 'r', encoding='utf-8') as f:
                    m_data = json.load(f)
                save_manifest_to_db(m_data, db_path, set_current=True)
                print(f"[DB] Seeded database with {m_data.get('title')} ({m_data.get('song_id')})")
            except Exception as e:
                print(f"[DB] Error seeding database: {e}")

if __name__ == "__main__":
    init_db()
    manifest_p = os.path.join(studio_paths.AUDIO_DIR, "song_manifest.json")
    seed_default_if_empty(manifest_p)
    songs = get_all_songs()
    print(f"Total songs in DB: {len(songs)}")
    for s in songs:
        print(f" - {s['title']} by {s['artist']} ({s['id']}): {s['active_layers']} active layers")
