# ADR 0002: Music Engineering gets its own repository, plan and GitHub tracking

- Status: accepted
- Date: 2026-10-18

## Context

The audio reverse-engineering work grew out of the remix studio prototype in the audio-lab workspace
(ADR 0001), next to a live production radio app. The project now has its own plan (PRD, Definition of
Done, scorecard, sourcing, alignment), its own release gates, and needs tracking that outlives chat
sessions and shared documents.

## Decision

- `Kausiukas/music_engineering` (private) holds `apps/remix_studio`, `packages/audiocore`, the plan and
  this project's docs. History was filtered from the workspace so earlier commits on these paths are kept.
  The radio app stays in its own repository and is not part of this project.
- `audiocore` is copied, not shared: from now on the two copies evolve independently. A fix needed by
  both is ported by hand, with tests in each.
- The plan lives as Markdown in `docs/plan/` and changes by pull request. Earlier Claude Docs and PDFs
  are snapshots (`docs/plan/pdf/`, dated 2026-10-18).
- Tracking uses GitHub natively: one issue per deliverable (requirements, instrument families, user,
  voice, review and loop actions, tasks, decisions), one milestone per gate, labels for type, area,
  language, priority and agreement, and a Project board with score fields. `docs/plan/backlog.yaml` is
  the source for issues, applied by `tools/plan_sync.py`.

## Consequences

- One place for scope, criteria and status; PR review covers plan changes as well as code.
- Issue criteria are copied from the plan at creation. When a criterion changes later, edit the plan
  in a PR and update the issue body in the same change.
- Two `audiocore` copies can drift; the radio's copy is not tested here.
