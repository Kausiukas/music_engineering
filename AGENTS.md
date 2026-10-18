# Music Engineering

Audio reverse-engineering workstation. Read these before working:

- `GLOSSARY.md`: the project's terms. Use them in code, tests, issues and docs.
- `CODING_STANDARDS.md`: the rules every change is reviewed against.
- `docs/plan/`: scope, acceptance criteria and scoring (start at `docs/plan/README.md`). Deliverable IDs (FR-12, U5, V11…) come from here.
- `docs/adr/`: decisions already made.
- `apps/remix_studio/AGENTS.md`: the app's layout and test tiers. `packages/audiocore/` is the light shared package.

## Working loop

1. Work comes from GitHub issues. A deliverable issue (`[ID] …`) is sliced into tickets with `/to-tickets`; each ticket is implemented in its own session with `/implement`. Decisions are tickets on the `wayfinder:map` issue, resolved one per session with `/wayfinder`.
2. Setup and test: `cd apps/remix_studio && uv sync`, then `uv run pytest -m "not slow and not artifact"`. Run `tests/test_render_fingerprints.py` before and after touching audio-producing code (set `AUDIO_LAB_DATA` to a populated data tree).
3. Commit scoped (`remix:`, `core:`, `docs:`, `plan:`, `ci:`), naming the deliverable. Never close a deliverable issue on code alone: it is done when its score reaches 100.
