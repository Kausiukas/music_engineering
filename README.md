# Music Engineering

Audio reverse engineering: drop in a mixed track and get back editable stems, MIDI, per-instrument sheet music, word-timed lyrics and matched synth patches, then loop, recreate and remix them. English and Lithuanian are developed in parallel.

| | |
| --- | --- |
| [`docs/plan/`](docs/plan/README.md) | **The plan**: PRD, Definition of Done, scorecard, gold data sourcing, batch alignment, and the backlog that drives GitHub issues |
| [`apps/remix_studio/`](apps/remix_studio/README.md) | The studio and ML sidecar: ingest → separation → pitch/transcription → recreation and remixes (Python, torch) |
| `packages/audiocore/` | Light shared audio helpers: pitch conversion, peak/level handling, Edge-TTS, synth, data locator (numpy/scipy/soundfile only) |
| [`data/`](data/README.md) | Runtime data (gitignored): stems, recreations, gold reference audio, catalog |
| [`docs/adr/`](docs/adr/) | Architecture decisions |

## Setup

Requires [uv](https://docs.astral.sh/uv/) and `ffmpeg` on PATH (`yt-dlp` for ingest).

```powershell
cd apps\remix_studio;  uv sync --extra pdf; uv run pytest -m "not slow and not artifact"
cd packages\audiocore; uv run --extra tts pytest
apps\remix_studio\run_remix_studio.bat      # http://localhost:8790
```

Data lives in `data/` at the repo root. To reuse an existing data tree elsewhere, set `AUDIO_LAB_DATA` to its path.

## How we work

- **Plan first.** Scope and acceptance live in [`docs/plan/`](docs/plan/README.md) and change by pull request. Work is tracked as GitHub issues (one per deliverable), milestones (one per gate) and the *Music Engineering* Project board.
- **Done means 100.** Every deliverable is scored 0–100 per language by the [scorecard](docs/plan/scorecard.md): quality × approved evidence.
- **Sound is a test.** Golden render fingerprints must stay green; an intended sound change regenerates them after a listening check.
- **Commits:** scoped (`remix:`, `core:`, `docs:`, `plan:`, `ci:`), small, tests green. Every PR follows the DoD's every-change checklist.
- **Agents:** [`AGENTS.md`](AGENTS.md) is the single instruction file; `CLAUDE.md` points to it.
