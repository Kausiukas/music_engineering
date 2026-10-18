# Remix DNA studio

Audio → stems → MIDI/score → synthetic recreation and genre remixes.

```powershell
uv sync --extra pdf
uv run python server.py              # http://localhost:8790 (REMIX_STUDIO_PORT / _HOST to change)
uv run python ingest_song.py <url-or-file>
uv run pytest -m "not artifact and not slow"   # hermetic tier
uv run pytest                                  # everything (needs data/remix populated)
```

| Stage | Modules |
|---|---|
| Ingest | `ingest_song.py` (yt-dlp, trim, separation, transcription, manifest, DB) |
| Separation & layers | `layer_discovery.py` (Demucs 6s), `layer_surgery.py` (merge/split) |
| Transcription | `audio_to_midi.py`, `polyphonic_transcriber.py`, `vocal_transcriber.py` (Whisper) |
| Notation | `sheet_music_exporter.py` (MusicXML, Grand Staff SVG) |
| Recreation | `synthetic_recreation.py` + `acoustic_timbre_engine.py` + `singing_tts_engine.py` (v1), `trio_synthetic_recreator.py`, `neural_singing_synthesizer.py`, `unflattened_layer_recreator.py` (current, see `docs/remix/spec_unflattened_recreation.md`) |
| Remixes | `multi_genre_engine.py` (techno/house), `jungle_remix_engine.py` |
| Evaluation | `quality_checker.py`, `accuracy_evaluator.py`, `gold_standard_parser.py`, `gold_standard_benchmark.py` |
| Catalog | `database/db.py` |
| Paths | `studio_paths.py` (data under `data/remix/`) |
| Prototyping | `experiments/`: runners and engine tournaments, not used by the studio |
