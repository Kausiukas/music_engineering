# Which of the brief's SoundCraft claims hold?

Date: 2026-10-18. Resolves issue #8.
Sources: the upstream repo [storytold/soundcraft](https://github.com/storytold/soundcraft) (`main`, which is now at workspace version 0.9.0), its [releases](https://github.com/storytold/soundcraft/releases), and the PR and issue pages linked below. Every link in this note was opened for this check. Claims come from the [project brief](../plan/brief/audio-reverse-engineering-project-brief.pdf) and the [PRD](../plan/prd.md).

## Summary verdict

**The brief is mostly accurate on the repo and its CLI and MCP surface, and less reliable on PR and issue status.** Every crate, app, CLI invocation, MCP flag, test file and doc it names exists. Most PR and issue numbers point at the change the brief describes. But:

- Six of the PRs it cites as established work are **still open** and not in any release: #683, #705, #670, #671, #676 and #687. So are the defensive-input PRs #695 and #703.
- **PR #195 is about save safety, not import.**
- **The "export stalls at 95%" issues, #624 and #665, are reports about ArtCraft's AI generation queue relayed from Discord, not about SoundCraft's bounce.**
- **The brand licence covers ArtCraft marks only.** The brief says SoundCraft marks must be removed too.
- **v0.7.0 is no longer current.** v0.8.0 shipped on 17 Oct and `main` is at 0.9.0.

The brief is reliable enough to plan a Phase 0 spike, provided we pin a released tag and don't count on any open PR.

## Claims

| Claim | Status | Evidence |
|---|---|---|
| Rust edition 2024, rust-version 1.90 | confirmed (the README adds that the desktop and web UI need Rust 1.95 or later) | [Cargo.toml](https://raw.githubusercontent.com/storytold/soundcraft/main/Cargo.toml), [README](https://raw.githubusercontent.com/storytold/soundcraft/main/README.md) |
| v0.7.0 released Oct 2026 | confirmed, 14 Oct 2026. Superseded by v0.8.0 (17 Oct); `main` is version 0.9.0 | [releases](https://github.com/storytold/soundcraft/releases), [v0.7.0](https://github.com/storytold/soundcraft/releases/tag/v0.7.0) |
| MIT OR Apache-2.0 | confirmed | [Cargo.toml](https://raw.githubusercontent.com/storytold/soundcraft/main/Cargo.toml), [README](https://raw.githubusercontent.com/storytold/soundcraft/main/README.md) |
| `docs/brand/LICENSE-brand.txt`; forks must remove ArtCraft **and SoundCraft** marks | different: the file exists but covers only the ArtCraft name, wordmark and mark. Forks must remove or replace those marks and may say the work is "based on SoundCraft by the ArtCraft team". SoundCraft's own name is not claimed as a mark | [LICENSE-brand.txt](https://raw.githubusercontent.com/storytold/soundcraft/main/docs/brand/LICENSE-brand.txt) |
| About 40% Pro Tools parity, tracked in ROADMAP.md, target-app-parity.md, gaps.md and parity-checklist.md | confirmed. About 40% is "ready for real work" (an estimate dated 2026-10-10). Menu coverage is 94.1% (measured) and features about 70%. All four docs exist | [ROADMAP.md](https://raw.githubusercontent.com/storytold/soundcraft/main/ROADMAP.md), [docs/](https://github.com/storytold/soundcraft/tree/main/docs) |
| AGENTS.md and CLAUDE.md | confirmed | [repo root](https://github.com/storytold/soundcraft), [AGENTS.md](https://raw.githubusercontent.com/storytold/soundcraft/main/AGENTS.md) |
| Crates time, audio-io, midi, video, dsp, mix, engine, playback, automation (MCP), ui-egui | confirmed. There is also a `model` crate the brief doesn't mention | [crates/](https://github.com/storytold/soundcraft/tree/main/crates), [README](https://raw.githubusercontent.com/storytold/soundcraft/main/README.md) |
| Separate clap, vst3 and au host crates | confirmed (`clap-host`, `vst3-host`, `au-host`). AGENTS.md says `unsafe` is allowed only in three FFI helper crates | [crates/](https://github.com/storytold/soundcraft/tree/main/crates), [AGENTS.md](https://raw.githubusercontent.com/storytold/soundcraft/main/AGENTS.md) |
| Apps soundcraft, soundcraft-cli and soundcraft-web (WASM built with trunk) | confirmed | [apps/](https://github.com/storytold/soundcraft/tree/main/apps), [README](https://raw.githubusercontent.com/storytold/soundcraft/main/README.md) |
| `soundcraft-cli commands` | confirmed | [README](https://raw.githubusercontent.com/storytold/soundcraft/main/README.md) |
| `SOUNDCRAFT_NO_PREFS=1 soundcraft-cli run --demo --cmd 'session.audio_health={}'` | confirmed in parts. `run --demo --cmd` is documented and `session.audio_health` is registered in `health.rs`. The page I opened only says not to use `SOUNDCRAFT_NO_PREFS` when testing preference persistence, so what the variable actually does is unverified | [control-protocol.md](https://raw.githubusercontent.com/storytold/soundcraft/main/docs/control-protocol.md), [health.rs](https://raw.githubusercontent.com/storytold/soundcraft/main/crates/engine/src/cmd/health.rs) |
| `soundcraft-cli mcp --demo --automation-read-root ./in --automation-write-root ./out` | confirmed. The sandbox flags came in v0.7.0 (#309) | [docs/mcp.md](https://raw.githubusercontent.com/storytold/soundcraft/main/docs/mcp.md), [v0.7.0](https://github.com/storytold/soundcraft/releases/tag/v0.7.0) |
| `soundcraft-cli mcp --connect PORT` | confirmed (used with `soundcraft --control 7801`) | [docs/mcp.md](https://raw.githubusercontent.com/storytold/soundcraft/main/docs/mcp.md) |
| `cargo xtask ci` | confirmed. It runs fmt, clippy, tests, asset and layering checks, and the WASM build | [README](https://raw.githubusercontent.com/storytold/soundcraft/main/README.md) |
| `crates/automation/tests/agent_tasks.rs` | confirmed. It covers MCP-only tasks: the `markers.add` command, plus the `batch` tool with `keep_going` | [agent_tasks.rs](https://github.com/storytold/soundcraft/blob/main/crates/automation/tests/agent_tasks.rs) |
| `markers.add` exists | confirmed (the agent test uses it) | [agent_tasks.rs](https://github.com/storytold/soundcraft/blob/main/crates/automation/tests/agent_tasks.rs) |
| PR #683, `markers.add` with a single start or end bound | different: the PR exists but is **open**. In released builds, a lone `start` is ignored and the marker goes at the edit selection | [#683](https://github.com/storytold/soundcraft/pull/683) |
| PR #146, MCP batch with `keep_going` | confirmed, merged 12 Oct | [#146](https://github.com/storytold/soundcraft/pull/146) |
| PR #128, new track matches the imported file's channel width | confirmed, merged 11 Oct | [#128](https://github.com/storytold/soundcraft/pull/128) |
| PR #195, import without overwriting session media | different: #195 is "Save safety: never overwrite audio or sessions…" (merged 12 Oct). It covers saves, not import | [#195](https://github.com/storytold/soundcraft/pull/195) |
| PR #181, stored instrument params pushed before render | confirmed, merged 12 Oct | [#181](https://github.com/storytold/soundcraft/pull/181) |
| `event.extract_chords` | confirmed. It exists and writes a chord marker per bar on Markers 2 | [event_more.rs](https://raw.githubusercontent.com/storytold/soundcraft/main/crates/engine/src/cmd/event_more.rs) |
| PR #705, saturating tick addition in `extract_chords` | different: **open**, not merged | [#705](https://github.com/storytold/soundcraft/pull/705) |
| PR #670 and #671, track preset slots | different: both **open**. #670 is whole-track presets; #671 is slot recall | [#670](https://github.com/storytold/soundcraft/pull/670), [#671](https://github.com/storytold/soundcraft/pull/671) |
| PR #676, VO Cut pipeline as the pattern to copy | different: **open**, and a reviewer asks for a generic configurable script runner instead of a built-in menu item | [#676](https://github.com/storytold/soundcraft/pull/676) |
| #167, docking manager | confirmed: it is a merged **PR** (11 Oct), "Add shared docking…" | [#167](https://github.com/storytold/soundcraft/issues/167) |
| PR #695 and #703, defensive input as established practice | different: both **open**. The pattern is real but not yet merged | [#695](https://github.com/storytold/soundcraft/pull/695), [#703](https://github.com/storytold/soundcraft/pull/703) |
| MusicXML export | confirmed (`file.export_sibelius` and `file.send_to_sibelius` write MusicXML) | [file.rs](https://raw.githubusercontent.com/storytold/soundcraft/main/crates/engine/src/cmd/file.rs), [README](https://raw.githubusercontent.com/storytold/soundcraft/main/README.md) |
| Built-in synth, drum synth and sampler | confirmed (`subtractive_synth`, `drum_synth`, Sampler since v0.6.1) | [instrument.rs](https://raw.githubusercontent.com/storytold/soundcraft/main/crates/engine/src/cmd/instrument.rs), [README](https://raw.githubusercontent.com/storytold/soundcraft/main/README.md), [releases](https://github.com/storytold/soundcraft/releases) |
| #599, VST3 params shown as 0–1 | confirmed, open | [#599](https://github.com/storytold/soundcraft/issues/599) |
| #600, VST3 automation | confirmed, open | [#600](https://github.com/storytold/soundcraft/issues/600) |
| #598, VST3 redraw | confirmed, open | [#598](https://github.com/storytold/soundcraft/issues/598) |
| #640, AU Cocoa view, targeted by PR #687 | different: #640 is "Audio Unit Plugins not working" (AU does nothing and VST3 isn't found). PR #687 (open) closes **#501** and doesn't mention #640 | [#640](https://github.com/storytold/soundcraft/issues/640), [#687](https://github.com/storytold/soundcraft/pull/687) |
| #648, no MP3 export | confirmed. Bounce writes only WAV, AIFF or FLAC | [#648](https://github.com/storytold/soundcraft/issues/648), [file.rs](https://raw.githubusercontent.com/storytold/soundcraft/main/crates/engine/src/cmd/file.rs) |
| #624 and #665, export stalls at 95% | different: both are Discord-relayed reports of AI generation stuck at 95%. #624 mentions Suno, and a commenter on #665 asks whether it is ArtCraft rather than SoundCraft. Both are flagged as duplicates of #221. Not evidence of a SoundCraft bounce bug | [#624](https://github.com/storytold/soundcraft/issues/624), [#665](https://github.com/storytold/soundcraft/issues/665) |
| #658, video track import | confirmed, open (needs info) | [#658](https://github.com/storytold/soundcraft/issues/658) |
| #651 | confirmed in substance. It is an accessibility issue: track and group rows expose no a11y nodes. Fix PR #657 is open | [#651](https://github.com/storytold/soundcraft/issues/651) |

## Notes for our use

We need headless stem import, MIDI clips, markers and an instrument patch, driven through the CLI or MCP on Windows.

- **Commands we need exist in code:**
  - `file.import_audio {path|paths, track?, new_tracks?=true, at?}` takes the channel count from the file.
  - `midi.new_clip {track, start?, end?|length?}` and `midi.note_add {clip, pitch, start_ticks, length_ticks?, velocity?, channel?}`.
  - `file.import_midi`, `markers.add`, and `mix.instrument {track, plugin, params?}`.
  - `session.save*`, `file.bounce_mix`, and `file.bounce_stems`.

  Sources: [file.rs](https://raw.githubusercontent.com/storytold/soundcraft/main/crates/engine/src/cmd/file.rs), [midi.rs](https://raw.githubusercontent.com/storytold/soundcraft/main/crates/engine/src/cmd/midi.rs), [instrument.rs](https://raw.githubusercontent.com/storytold/soundcraft/main/crates/engine/src/cmd/instrument.rs). The MCP doc covers only a few of these by name and says to discover the rest with `list_commands`.
- **Patch values are not normalized.** `mix.instrument` takes `params` by the plugin's own parameter ids. It clamps values into range and errors on unknown ids or non-numbers. The brief has the sidecar emit normalized [0, 1] values. We must map them to each built-in's real parameter ranges, or confirm in the spike that the ranges are 0–1.
- **No copy-on-import.** `file.import_audio` has no copy option, and I couldn't confirm from code whether sources are copied into the session folder. Stems should be written where the session can keep them, inside the MCP read root, and the session's source paths checked in the spike.
- **Markers from the CLI:** pass `at`, or both `start` and `end`. Until #683 merges, a lone `start` is silently ignored.
- **Windows:**
  - Signed x64, x86 and Arm builds ship, and `cargo xtask ci` passes on Windows (v0.7.0, #324).
  - The MCP sandbox ignores case on Windows, resolves UNC paths and refuses device names like `CON` ([mcp.md](https://raw.githubusercontent.com/storytold/soundcraft/main/docs/mcp.md)).
  - ROADMAP says only macOS is actually exercised; Windows is built but less tested.
- **There is no MIDI device layer,** so MIDI can't be recorded from a keyboard (ROADMAP). This doesn't affect us, because we write MIDI by command.
- **Release cadence is very fast:** v0.3.0 to v0.8.0 in nine days. Pin a tag (v0.8.0 or later, not v0.7.0) and rerun our spike checks on each bump.
- **The sidecar pattern is not settled upstream.** The reviewer on #676 prefers a generic "run script" command over hard-coded menu items. The other reading is that we shouldn't need upstream changes at all and can drive everything over MCP from outside.
