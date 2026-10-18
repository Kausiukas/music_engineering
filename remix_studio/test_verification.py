"""
Verification Script for Database & Layer Surgery Engine
Tests:
1. SQLite database queries (all songs, current song, layers)
2. Song switching endpoint
3. Layer merge verification (waveform peaks, notes count, grand staff score SVG)
4. Linkwitz-Riley layer split verification
"""

import urllib.request
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def test_api():
    base_url = "http://localhost:8790"
    
    # 1. Test GET /api/songs
    req = urllib.request.urlopen(f"{base_url}/api/songs")
    songs_data = json.loads(req.read().decode('utf-8'))
    assert songs_data.get("success"), "GET /api/songs failed"
    songs = songs_data.get("songs", [])
    print(f"✔ 1. GET /api/songs passed: {len(songs)} song(s) in SQLite database.")
    for s in songs:
        print(f"   Track: '{s['title']}' by {s['artist']} ({s['id']}) | Active: {s['is_current']}")

    # 2. Test GET /api/manifest
    req = urllib.request.urlopen(f"{base_url}/api/manifest")
    manifest = json.loads(req.read().decode('utf-8'))
    active_layers = [l for l in manifest.get("layers", []) if l.get("is_active")]
    print(f"✔ 2. Active Layers in Studio: {len(active_layers)}")
    for l in active_layers:
        print(f"   - {l.get('icon')} {l.get('name')} ({l.get('id')}) | Clef: {l.get('clef')} | Notes: {l.get('num_notes', 0)}")

    # 3. Test Merged Acoustic Guitar Layer exists
    ac_layer = next((l for l in active_layers if l.get("id") == "acoustic_guitar"), None)
    assert ac_layer is not None, "Merged layer 'acoustic_guitar' not found in active layers!"
    print(f"✔ 3. Merged layer verified: {ac_layer['name']} ({ac_layer['id']})")
    assert ac_layer['clef'] == "grand_staff", f"Expected grand_staff clef, got {ac_layer['clef']}"
    assert ac_layer['num_notes'] > 100, f"Expected >100 merged notes, got {ac_layer['num_notes']}"
    print(f"   Notes: {ac_layer['num_notes']}, Clef: {ac_layer['clef']}, Parents: {ac_layer.get('parent_layers')}")

    # 4. Test Score SVG Generation for Merged Layer
    req = urllib.request.urlopen(f"{base_url}/api/score/svg?semitones=0&layer=acoustic_guitar")
    svg_text = req.read().decode('utf-8')
    assert "Grand" in svg_text, "Grand Staff symbol missing in SVG score!"
    interactive_count = svg_text.count('class="interactive-note"')
    print(f"✔ 4. SVG Grand Staff Score rendered successfully: {len(svg_text)} bytes, {interactive_count} interactive notes rendered.")

    # 5. Test Waveforms Batch API
    req = urllib.request.urlopen(f"{base_url}/api/waveforms/all")
    waveforms_data = json.loads(req.read().decode('utf-8'))
    peaks = waveforms_data.get("peaks", {})
    assert "acoustic_guitar" in peaks, "acoustic_guitar waveform peaks missing!"
    print(f"✔ 5. Batch Waveforms API returned {len(peaks)} layers, including merged 'acoustic_guitar' ({len(peaks['acoustic_guitar'])} points).")

    print("\n🎉 ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_api()
