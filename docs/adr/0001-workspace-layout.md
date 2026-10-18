# ADR 0001: One workspace, two apps, one shared audio package

- Status: accepted
- Date: 2026-10-18

## Context

`D:\radio` held the live radio station at the repository root and the Remix Studio prototype in an
untracked `remix_studio/` folder. An audit found:

- Code and ~5 GB of runtime data were interleaved. Outputs were written into the code tree.
- Coupling ran through hardcoded absolute paths, including to a third, unversioned project
  (`D:\memes`). Locally the radio read its 920-sample library from `D:\memes`, and could import
  diverged module copies from `D:\memes\scripts` via `sys.path`.
- The same helpers were reimplemented across both projects: pitch conversion ×6, peak handling ×59
  inline sites, Edge-TTS wrappers ×6.
- Remix had no dependency manifest. The radio had none for its venv-less local runs. Tests leaked
  through user site-packages.

Both projects are audio-design work and should keep a common technical base.

## Decision

A single repository with:

- `apps/radio`, `apps/remix_studio`: independent apps, each with its own `pyproject.toml`,
  `uv.lock` and `.venv`. The radio env stays small for a 512 MB VPS; remix carries torch/demucs/whisper.
- `packages/audiocore`: shared code, consumed as an editable path dependency (vendored into radio
  releases). Code moves here only when a second app needs it, with tests.
- `data/`: all runtime data, gitignored, relocatable via `AUDIO_LAB_DATA`. `data/shared` holds
  samples and sfx used by both apps.
- One paths module per app (`prn_paths.py`, `studio_paths.py`). No absolute paths in code.
- `D:\memes` is external: reached only through `PRN_MEMES_MIRROR_DIR`. Its sample library was
  copied into `data/shared/classic_samples`.

## Consequences

- Refactors are verified by golden render fingerprints. The radio composer and all remix engines
  rendered bit-identically before and after this change.
- Apps cannot import each other. Shared logic has one home and one test suite.
- Two virtualenvs to maintain. `uv sync` per app.
- A full monorepo tool (uv workspace with one lock) was rejected: one resolution would force the
  radio's production stack and the remix ML stack onto the same versions.
