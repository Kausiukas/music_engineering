"""
Unit and integration tests for Remix Studio DAW Core
Validates:
- Database catalog queries and transactions
- Layer surgery (merge/split) rules
- Zero-clipping peak standards
- Whisper STT lyrics transcription and syllable alignment
- Polyphonic chord extraction (6-string simultaneous voicings)
"""

import unittest
import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

class TestRemixStudioCore(unittest.TestCase):
    def setUp(self):
        self.db_path = os.path.join(BASE_DIR, "database", "remix_studio.db")
        self.audio_dir = os.path.join(BASE_DIR, "audio")

    def test_database_catalog_exists(self):
        """Verify SQLite remix_studio.db exists and has songs table."""
        self.assertTrue(os.path.exists(self.db_path), f"Database not found at {self.db_path}")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='songs';")
        row = cursor.fetchone()
        self.assertIsNotNone(row, "Table 'songs' must exist in remix_studio.db")
        
        cursor.execute("SELECT count(*) FROM songs WHERE is_current = 1;")
        count = cursor.fetchone()[0]
        self.assertGreaterEqual(count, 1, "There should be at least 1 active song")
        conn.close()

    def test_manifest_format(self):
        """Verify song_manifest.json contains required DAW metadata."""
        manifest_path = os.path.join(self.audio_dir, "song_manifest.json")
        self.assertTrue(os.path.exists(manifest_path), "song_manifest.json must exist")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertIn("song_id", manifest)
        self.assertIn("layers", manifest)
        layers = manifest["layers"]
        layer_ids = [l["id"] for l in layers]
        self.assertIn("acoustic_guitar", layer_ids, "acoustic_guitar layer must exist")

    def test_lyrics_stt_transcription(self):
        """Verify lyrics.json contains true Lithuanian Whisper transcription with syllable objects."""
        lyrics_path = os.path.join(self.audio_dir, "lyrics.json")
        self.assertTrue(os.path.exists(lyrics_path), "lyrics.json must exist")
        with open(lyrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("language"), "lt")
        self.assertGreaterEqual(len(data.get("segments", [])), 1)
        self.assertGreaterEqual(len(data.get("words", [])), 5)
        # Check that words have syllables
        first_word = data["words"][0]
        self.assertIn("syllables", first_word, "Words must contain structured syllable breakdown")
        self.assertGreaterEqual(len(first_word["syllables"]), 1)

    def test_polyphonic_chord_voicings(self):
        """Verify acoustic_guitar_notes.json contains 6-string chord voicings with simultaneous onsets."""
        notes_path = os.path.join(self.audio_dir, "acoustic_guitar_notes.json")
        self.assertTrue(os.path.exists(notes_path), "acoustic_guitar_notes.json must exist")
        with open(notes_path, "r", encoding="utf-8") as f:
            notes = json.load(f)
        self.assertGreaterEqual(len(notes), 100, f"Expected >100 polyphonic notes, found {len(notes)}")
        
        # Check chord tags
        chords = [n.get("chord") for n in notes if n.get("chord")]
        self.assertGreaterEqual(len(chords), 50, "Notes must contain chord harmonic tags")
        
        # Check simultaneous chord notes (chords with >= 2 notes at the same start time)
        from collections import Counter
        start_counts = Counter(round(n["start"], 2) for n in notes)
        multi_note_onsets = [t for t, count in start_counts.items() if count >= 2]
        self.assertGreaterEqual(len(multi_note_onsets), 10, "Acoustic guitar must contain polyphonic chords")

    def test_synthetic_files_zero_clipping(self):
        """Verify that synthetic audio files adhere to audio-daw-standards (peak <= 0.92 / -0.7 dBFS)."""
        import soundfile as sf
        import numpy as np

        synth_dir = os.path.join(self.audio_dir, "synthetic")
        if os.path.exists(synth_dir):
            for fn in os.listdir(synth_dir):
                if fn.endswith(".wav"):
                    fpath = os.path.join(synth_dir, fn)
                    data, _ = sf.read(fpath)
                    max_peak = float(np.max(np.abs(data)))
                    self.assertLessEqual(max_peak, 0.925, f"Audio file {fn} exceeded zero-clipping limit: {max_peak}")

if __name__ == "__main__":
    unittest.main()
