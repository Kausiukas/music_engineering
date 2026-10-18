# Coding standards

Judgement rules that `code-review` checks every change against. Rules a machine can check belong in CI or tests instead; the ones marked **(CI)** already are, or must become so. Terms follow `GLOSSARY.md`.

## Sound

- A refactor never changes sound. `tests/test_render_fingerprints.py` stays green; an intended sound change regenerates the goldens in the same commit, after a listening check, and the commit message says so. **(CI once fixtures are frozen)**
- Every rendered file has true peak ≤ −0.7 dBFS. Limit with `audiocore.dsp.limit_peak` / `normalize_peak`; verify inter-sample peaks with `audiocore.dsp.true_peak_dbfs`.
- Renders are seeded and deterministic. Cloud results are cached per job so a rerun gives the same output.

## Inputs and errors

- Every number that comes from a file, CLI flag, HTTP/MCP payload or model output is hostile until checked: reject missing, NaN, infinite and out-of-range values with a typed error.
- A stage fails with a typed error carrying a code and a plain message, never a stack trace to the user and never silent output.
- Heavy work (separation, pitch, STT, alignment) never runs inside a request handler or an audio callback; it runs in a worker and reports progress.

## Paths, data and dependencies

- Every filesystem location comes from `apps/remix_studio/studio_paths.py`. No absolute paths, no paths built from `__file__` outside that module. **(CI: grep check)**
- `packages/audiocore` stays numpy/scipy/soundfile (+ optional edge-tts). torch, demucs, whisper and other ML packages live in `apps/remix_studio` only. **(CI: dependency check)**
- A new dependency or model checkpoint records its licence; only MIT, BSD and Apache-2.0 are allowed in what we distribute. No AGPL code.
- Secrets and API keys come from the environment, never the repo.

## Truth and evidence

- Gold items are never used to train or tune a model, and gold timings are never produced with the app's own aligner.
- An improvised or comping unit is never scored at note level; note F-measure covers written and embellished units only.
- Accuracy code compares against the layer it is about: score-level checks against the score layer, timing checks against the performance layer.

## Tests

- New behaviour gets a hermetic test (stub models, tiny fixtures, no network) that fails on bad output. Assertions check observable audio, notes or files, not internal variables, and are never tautological.
- Tests that need models are marked `slow`; tests that read generated data under `data/` are marked `artifact`.
- Each instrument family and each language pack has its own tests.

## Traceability

- A change names the deliverable it serves (FR-…, U…, V…, F-…, T0-…) in the commit message or PR, and links its ticket.
- Behaviour that changes acceptance changes the plan in the same PR (`docs/plan/`), and a hard-to-reverse decision gets an ADR in `docs/adr/`.
- Terms in code, tests and docs follow `GLOSSARY.md`; a new domain term is added there first.
