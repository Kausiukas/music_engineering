import whisper
import json

print("Loading whisper...")
model = whisper.load_model("tiny")
print("Transcribing full track to find Kolorado vabalai chorus...")
res = model.transcribe(r"d:\radio\remix_studio\audio\kolorado_vabalai.wav", language="lt")

with open(r"d:\radio\remix_studio\audio\full_lyrics.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)

print("--- FULL SEGMENTS ---")
for s in res.get("segments", []):
    txt = s['text'].strip()
    print(f"{s['start']:.1f}s - {s['end']:.1f}s: {txt}")
