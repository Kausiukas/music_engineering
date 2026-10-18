import whisper
import os
import studio_paths
import json

print("Loading whisper...")
model = whisper.load_model("tiny")
print("Transcribing full track to find Kolorado vabalai chorus...")
res = model.transcribe(os.path.join(studio_paths.AUDIO_DIR, "kolorado_vabalai.wav"), language="lt")

with open(os.path.join(studio_paths.AUDIO_DIR, "full_lyrics.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)

print("--- FULL SEGMENTS ---")
for s in res.get("segments", []):
    txt = s['text'].strip()
    print(f"{s['start']:.1f}s - {s['end']:.1f}s: {txt}")
