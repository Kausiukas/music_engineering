# data/

Machine-local runtime data. Everything here is gitignored except this file, which also marks the
workspace root for `audiocore.paths.workspace_data_dir()`. Relocate the whole tree with the
`AUDIO_LAB_DATA` environment variable (for example, point it at an existing `D:\radio\data`).

| Path | Contents |
|---|---|
| `remix/audio/` | Ingested songs, stems, note/pitch JSON, `song_manifest.json` |
| `remix/db/remix_studio.db` | SQLite catalog (songs, layers, remixes; later scores and candidates) |
| `remix/recreations/`, `remix/remixes/` | Synthetic recreations and genre remixes |
| `remix/midi/`, `remix/scores/` | Exported MIDI and MusicXML/SVG |
| `remix/gold_standards/` | Gold-standard reference audio (the JSON ground truth is tracked in `apps/remix_studio/gold_standards/`) |
| `remix/fixtures/` | Source songs + score PDFs the gold standards were parsed from |
| `remix/sourcing/` | Gold data sourcing candidates (FR-16) |
| `remix/downloads/` | Raw yt-dlp downloads |
| `shared/` | Optional sample packs and SFX (`sample_packs/`, `classic_samples/`, `sfx/`) |
