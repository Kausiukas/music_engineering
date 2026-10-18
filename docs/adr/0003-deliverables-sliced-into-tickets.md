# ADR 0003: Deliverables are sliced into tickets late; decisions run on a wayfinder map

- Status: accepted
- Date: 2026-10-18

Deliverable issues (`[FR-12] …`) stay the unit of acceptance and scoring, but are never implemented directly: when work starts, `/to-tickets` slices one into tracer-bullet sub-issues sized for a single agent session, and `/implement` builds one ticket per session. Open questions live as decision tickets under one `wayfinder:map` issue instead of flat decision issues. We chose this over one-issue-per-requirement execution because a requirement does not fit one session, and over slicing everything up front because early tickets change what later ones should be. Terms come from `GLOSSARY.md` and reviews check `CODING_STANDARDS.md`, which the skills read by convention.
