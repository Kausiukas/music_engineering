# Music Engineering

Audio reverse-engineering workstation. One app plus a light shared package:

- `apps/remix_studio/`: the studio and ML sidecar. Read `apps/remix_studio/AGENTS.md` before changing it.
- `packages/audiocore/`: shared audio helpers. Keep it light (numpy/scipy/soundfile); torch, demucs and whisper belong in `apps/remix_studio` only.
- `data/`: machine-local runtime data, gitignored. Layout in `data/README.md`.

## The plan is the contract

- Scope, acceptance criteria and scoring live in `docs/plan/` (PRD, DoD, scorecard, sourcing, alignment). Read the relevant section before starting an issue; cite the deliverable ID (FR-12, U5, V11…) in commits and PRs.
- Work items are GitHub issues titled `[ID] …`, generated from `docs/plan/backlog.yaml` by `tools/plan_sync.py`. A new deliverable goes into the plan and the backlog first, then the script creates its issue.
- A deliverable is done when it scores 100 in each of its languages (`docs/plan/scorecard.md`). Don't close an issue on code alone; its done-when evidence must be committed.
- Decisions go into `docs/adr/` and close their `type:decision` issue.

## Working loop

1. `cd apps/remix_studio && uv sync`, then `uv run pytest -m "not slow and not artifact"` (fast) or `uv run pytest` (full, needs `data/remix`).
2. Before changing audio-producing code, run `tests/test_render_fingerprints.py`. A refactor that changes a fingerprint changed the sound. Regenerate goldens only for intended sound changes, after listening.
3. Every location comes from `apps/remix_studio/studio_paths.py`; never hardcode paths.
4. Commit scoped (`remix:`, `core:`, `docs:`, `plan:`, `ci:`) and follow the DoD every-change checklist (the PR template repeats it).

## Rules that keep scores honest

- Gold standards come only from approved professional musicians and are never used for training or tuning.
- Gold timings are never produced with the app's own aligner.
- Improvised units are judged at chord level, not note level (`docs/plan/alignment.md`).
