# The plan

| Document | What it decides |
| --- | --- |
| [PRD](prd.md) | Problem, goals, requirements FR-1 to FR-19, architecture, milestones, risks and decisions |
| [Definition of Done](dod.md) | User actions U1–U18 and V1–V11, instrument families, voice pipeline, per-change, per-requirement, per-gate and v1 criteria |
| [Deliverable Scorecard](scorecard.md) | How every deliverable is scored 0–100 per language (quality × approved evidence), and the registry of what is scored |
| [Gold Data Sourcing](sourcing.md) | How test songs and sheet music are found, validity-scored and approved by musicians (FR-16, R1–R10) |
| [Units and Batch Alignment](alignment.md) | The unit ladder L0–L10, batch alignment, improvisation, timing truth, loops and mixes (FR-17–FR-19, M1–M8) |
| [Original brief](brief/audio-reverse-engineering-project-brief.pdf) | The input this plan was built from |
| [PDF snapshots](pdf/) | The plan as exported on 2026-10-18 |

## How the plan is tracked on GitHub

```mermaid
flowchart LR
    PLAN["docs/plan/*.md<br/>criteria, agreement"] --> BL["backlog.yaml<br/>IDs, gates, labels"]
    BL -- "tools/plan_sync.py" --> GH["Issues · Milestones · Labels"]
    GH --> BOARD["Project: Music Engineering<br/>Status, Score EN/LT, Q, E"]
    SC["scorecard run<br/>(nightly)"] -- "scorecard publish" --> BOARD
    PR["Pull requests<br/>Closes #issue"] --> GH
```

| GitHub feature | Used for |
| --- | --- |
| **Milestones** | One per gate: Gate 0 Foundation and spike → Gate 3 Synth matching, editing and UI. A gate closes when its DoD checklist is ticked |
| **Issues** | One per deliverable, titled `[ID] …`: requirements (FR), instrument families (F-…), user actions (U, V, R, M), enabling tasks (T0-…) and open decisions (D-…). The body carries the done-when criteria copied from the plan |
| **Labels** | `type:*`, `area:*`, `lang:en` / `lang:lt`, `priority:must/should/could`, `agreement:proposed/agreed/changed` |
| **Project board** | *Music Engineering*: work status (Todo, In progress, Done) plus number fields Score EN, Score LT, Score (any), Quality Q, Evidence E, filled by the scorecard |
| **Pull requests** | Every change; the template carries the DoD every-change checklist. Use `Closes #N` only when the deliverable's evidence is committed |
| **Actions** | CI runs the hermetic tiers of `audiocore` and `remix_studio` on every PR |

**Agreement vs status.** Whether a row is *agreed* is decided in the plan (edit the Status column in a PR, then update the issue's `agreement:` label). Whether it is *being worked on or done* is tracked on the board.

**Adding or changing a deliverable.**

1. Edit the plan doc (criteria) and `backlog.yaml` (ID, gate, area) in one PR.
2. After merge, run `uv run --no-project --with pyyaml python tools/plan_sync.py --project "Music Engineering"`. It creates whatever is missing and leaves existing issues alone. Use `--dry-run` to preview.
3. If an existing criterion changed, update that issue's body in the same PR description.

`issues.json` maps each deliverable ID to its issue number; the scorecard registry uses it to publish scores.
