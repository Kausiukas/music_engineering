import os
import sys
import time

BASE_DIR = r"d:\radio\remix_studio"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from layer_discovery import run_6s_separation, compute_stem_metrics, INSTRUMENT_PROFILES

in_wav = os.path.join(BASE_DIR, "audio", "grikiai_30s.wav")
out_dir = os.path.join(BASE_DIR, "audio", "stems", "grikiai")
os.makedirs(out_dir, exist_ok=True)

t0 = time.time()
print("Starting 6s separation on 30s audio...")
stem_paths = run_6s_separation(in_wav, output_dir=out_dir)
print(f"Separation completed in {time.time()-t0:.1f}s!\n")

print("Evaluating Presence Metrics:")
for s, p in stem_paths.items():
    m = compute_stem_metrics(p)
    prof = INSTRUMENT_PROFILES.get(s, {})
    tag = "[ACTIVE]" if m["verdict"] == "active" else "[PRUNED]"
    icon = prof.get("icon", "🎵")
    print(f"{icon} {s.upper():<8} -> RMS: {m['rms_db']:>5} dBFS | Duty: {m['active_duty_cycle']*100:>5.1f}% | Onsets: {m['onsets']:>3} => {tag}")
