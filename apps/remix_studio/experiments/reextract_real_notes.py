import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # apps/remix_studio
import studio_paths
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = studio_paths.AUDIO_DIR
sys.path.insert(0, BASE_DIR)

from layer_discovery import extract_instrument_notes
from audio_to_midi import extract_melody_notes

print("Re-extracting notes using REAL AUDIO analysis...")

# 1. Acoustic guitar
guitar_path = os.path.join(AUDIO_DIR, "acoustic_guitar.wav")
if os.path.exists(guitar_path):
    g_notes = extract_instrument_notes(guitar_path, "acoustic_guitar", bpm=117.5)
    with open(os.path.join(AUDIO_DIR, "acoustic_guitar_notes.json"), "w", encoding="utf-8") as f:
        json.dump(g_notes, f, indent=2)
    print(f"✔ Extracted {len(g_notes)} real audio notes for acoustic_guitar (Sample chord: {g_notes[0]['chord'] if g_notes else 'none'})")

# 2. Bass
bass_path = os.path.join(AUDIO_DIR, "bass.wav")
if os.path.exists(bass_path):
    b_notes = extract_instrument_notes(bass_path, "bass", bpm=117.5)
    with open(os.path.join(AUDIO_DIR, "bass_notes.json"), "w", encoding="utf-8") as f:
        json.dump(b_notes, f, indent=2)
    print(f"✔ Extracted {len(b_notes)} real audio notes for bass")

# 3. Vocals
vox_path = os.path.join(AUDIO_DIR, "vocals.wav")
if os.path.exists(vox_path):
    v_notes = extract_melody_notes(vox_path)
    with open(os.path.join(AUDIO_DIR, "vocal_notes.json"), "w", encoding="utf-8") as f:
        json.dump(v_notes, f, indent=2)
    print(f"✔ Extracted {len(v_notes)} clean onset-gated notes for vocals")

print("Done!")
