# Remix Studio

Prototype pipeline: ingest (yt-dlp) → Demucs 6-stem separation → pitch/chord/lyric transcription → MIDI + Grand Staff score → synthetic recreation and genre remixes. Stdlib `http.server` on 127.0.0.1:8790 (`server.py`), frontend in `static/`.

## Layout

- Product modules sit at the top level and import each other by bare name (`pythonpath = ["."]` in `pyproject.toml`).
- `experiments/` holds one-off runners and engine tournaments. Nothing in the product imports them. Promote a finding by moving the code into a product module with a test.
- All data lives under `studio_paths.DATA_DIR` (`data/remix/`) with the same relative layout the API serves at `/audio/<rel>`. `studio_paths.resolve_data_path` confines those requests to the data root.
- `gold_standards/*.json` is tracked ground truth parsed from score PDFs (`gold_standard_parser.py`); the reference stems are in `data/remix/gold_standards/`.
- SQLite catalog: `data/remix/db/remix_studio.db` (`database/db.py`).

## Tests

- `pytest -m "not artifact and not slow"` is the hermetic tier.
- `artifact` tests assert on pipeline outputs already in `data/remix` (recreations, DB, manifest). Rerun the pipeline before trusting them after an engine change.
- `tests/test_render_fingerprints.py` renders seeded audio through every engine. It must stay green across refactors.

## Audio rules

`.agents/rules/audio-daw-standards.md` covers headroom, non-blocking DSP, Grand Staff notation and layer-surgery invariants. Use `audiocore.dsp.limit_peak`/`normalize_peak` for levels. They act on sample peak; use `true_peak_dbfs` when the −0.7 dBFS rule must hold for inter-sample peaks.
