## What and why

<!-- One or two sentences. Name the deliverable(s): FR-…, U…, V…, F-…, T0-… -->

Closes #

## Evidence

<!-- Test names, metric output, scorecard Q/E/score before → after, screenshots or recordings for walkthroughs. -->

## Every-change checklist ([DoD](../blob/main/docs/plan/dod.md#every-change))

- [ ] Scoped commit messages (`remix:`, `core:`, `docs:`, `plan:`, `ci:`), nothing outside the change's scope
- [ ] `uv run pytest -m "not slow and not artifact"` green in every package touched
- [ ] `tests/test_render_fingerprints.py` green, or the sound change is intended, listened to, and stated here
- [ ] New behaviour has a hermetic test that fails on bad output
- [ ] No absolute paths; new locations added to `studio_paths.py`
- [ ] No ML dependency in `audiocore`
- [ ] Bad input returns a typed error, never a crash or silent output
- [ ] Every rendered file has true peak ≤ −0.7 dBFS
- [ ] New dependencies or checkpoints have their licence recorded (MIT, BSD, Apache-2.0)
- [ ] Docs updated where behaviour changed (`AGENTS.md`, README, plan, or an ADR)
