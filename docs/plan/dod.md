# Audio Reverse Engineering: Definition of Done

As of 2026-10-18 · Owner: Antanas · Status: living document. Changes go through pull requests.

A piece of work is done only when its evidence is committed: a test, a metric, or a recorded decision. Saying it works doesn't count. This doc applies the [PRD](prd.md) at five levels: what the user can do, every change, every requirement, every phase gate and the v1 release.

**Scores.** Every deliverable is tracked as a 0–100 score per language in the [Deliverable Scorecard](scorecard.md). A deliverable is done when it scores 100 in each of its languages, which means it meets its criteria below with approved evidence.

**Tracking.** Each user action and requirement below is a GitHub issue; each gate is a milestone. Agreement status lives in the tables here (changed by pull request); work status lives on the GitHub Project board. See [README](README.md).

## What the user can do

The app is complete only when the user can do every agreed action below, start to finish, in the studio, with no developer help. Each row is one acceptance walkthrough: someone follows the *Done when* text on a real song, and it either passes or fails.

Every row starts as **Proposed**. To agree on a row, change its Status to Agreed, Changed (after editing the row) or Cut in a pull request. To argue a row, comment on its issue. Priority and phase are first suggestions.

| ID | The user can… | Done when | Priority | Phase | Status |
| --- | --- | --- | --- | --- | --- |
| U1 | Import a song by dropping a file (WAV, FLAC, MP3) or pasting a URL | The job appears at once and shows progress for each stage; no terminal needed | Must | 1 | Proposed |
| U2 | Reopen any earlier job from a library | The library lists title, date and status. Opening a job restores stems, notes and recreations without reprocessing | Must | 1 | Proposed |
| U3 | Split a song into stems and solo or mute each one against the original | Vocals, bass, drums, synth/other and sfx play in sync with the original; any combination can be soloed or muted | Must | 1 | Proposed |
| U4 | Download any stem | Each stem saves as a 48 kHz WAV that opens in another DAW at the right length and position | Must | 1 | Proposed |
| U5 | See and hear the notes of each melodic stem as a piano roll | Each pitched stem shows a piano roll (drums show a hit grid by drum type); playback follows the original | Must | 1 | Proposed |
| U6 | Read the transcription as sheet music that follows playback | The score uses its family's notation (see Instrument families) and its cursor stays within one beat of the audio | Must | 1 | Proposed |
| U7 | Fix a wrong note and hear the fix | Editing a note in the score or piano roll changes the playback and every export | Should | 3 | Proposed |
| U8 | Export MIDI and MusicXML for any stem | The files open in MuseScore and in another DAW with the same notes and tempo | Must | 1 | Proposed |
| U9 | See the song's sections and chords on the timeline | Sections (intro, verse, chorus…) and chord names appear as markers; clicking one jumps playback there | Should | 2 | Proposed |
| U10 | Get matched synth patches for a stem and audition them against the original | At least 3 candidates per stem, each with a match score, playable side by side with the original | Must | 3 | Proposed |
| U11 | Save a chosen patch as a preset and reuse it | The preset appears in a preset list and loads into any new track in a later session | Should | 3 | Proposed |
| U12 | Render a synthetic recreation of the whole song and A/B it with the original | One action renders the recreation; one control switches between original and recreation at the same playhead position | Must | 2 | Proposed |
| U13 | Swap any layer between the original stem and its recreation, and set its level | Every layer has an original/recreated switch and a fader; changes are heard immediately | Must | 2 | Proposed |
| U14 | Apply a genre remix (jungle, techno, house) to a song | Choosing a genre renders a remix built from the song's own stems and notes, playable and downloadable | Should | 2 | Proposed |
| U15 | Bounce the mix or all stems to a file | WAV or FLAC export completes without stalling; true peak ≤ −0.7 dBFS on every file | Must | 2 | Proposed |
| U16 | See how reliable a job's results are | Each job shows note confidence over time and flags low-confidence regions. Gold songs also show F-measure | Must | 1 | Proposed |
| U17 | Understand and recover from a failed import | A bad or unsupported file gives a plain-language message naming the problem; other jobs and the studio keep working | Must | 1 | Proposed |
| U18 | Run the whole process from one command or an AI agent | The CLI/MCP run of U1–U12 produces the same job the UI shows, and it opens in the studio | Must | 1 | Proposed |

**Walkthrough rules**

- Run it on the release candidate, on the workstation, from a fresh start of the studio.
- Use two songs: one from the gold set and one from outside it, each 2–5 minutes long.
- Record pass or fail per row in the release PR, with screenshots or a short screen recording.
- “The studio” means whichever host the Gate 0 ADR picks, SoundCraft or the web studio. The rows don't change either way.

Further user actions are agreed in their own specs: review actions R1–R10 in [sourcing.md](sourcing.md), loop and mix actions M1–M8 in [alignment.md](alignment.md).

## Instrument families

Each instrument family gets its own transcription logic and its own notation. One generic pitch-to-notes path is not done for any family. Every stem is first labelled with a family, either automatically or by the user, and that label picks the transcriber, the notation and the checks.

| Family | How it's transcribed | What the user sees | Done when (proposed) |
| --- | --- | --- | --- |
| Piano / keys | Polyphonic note model with sustain-pedal detection; notes split into left and right hand | Grand Staff (treble + bass) with chords stacked, a hand-split point and pedal marks | Note F-measure ≥ baseline + 15; ≥ 90% of notes on the right hand |
| Guitar | Polyphonic notes plus strum and chord detection; each note assigned to a string and fret | Standard staff + TAB (6 strings, tuning selectable), chord symbols with diagrams | Every TAB position is playable (≤ 4-fret span per chord in the chosen tuning); chord names match on gold songs |
| Bass | Monophonic tracker tuned down to 30 Hz, with octave-error correction; note lengths kept (staccato vs held) | Bass clef (8vb where needed) + 4-string TAB | Octave errors < 5% of notes; onsets within ±30 ms |
| Drums and kick | No pitch. Onsets classified as kick, snare, hi-hat (open/closed), toms, crash or ride; kick found from low-band onsets and checked against the bass | Percussion staff with a fixed drum map; MIDI on channel 10 with General MIDI notes | Kick, snare and hi-hat onset F-measure each ≥ 0.85 on gold drums; no pitched notes on the drum staff |
| Synth lead / pad | Mono or poly depending on the stem; notes go to synth matching (FR-6) | Treble or Grand Staff by range, linked to the matched patch | Same note bar as piano; the patch plays the transcribed notes |
| Vocals | Its own pipeline: see **Voice** | Melody staff with lyrics under notes, one syllable per note | See Voice |
| SFX / other | Events only, no notes | Labelled markers on an event lane, never a staff | No staff is generated; events can be clicked |

- [ ] The family label can be seen and changed per stem, and changing it re-runs only that stem
- [ ] Each family has its own gold-standard clips (≥ 3 per family, from approved professional musicians) before its bar is frozen
- [ ] MusicXML export keeps family notation (TAB, drum map, Grand Staff) and opens correctly in MuseScore

## Voice

Voice is done when the user can trust what the app says is being sung or spoken, word by word, and see it mapped onto the song's structure. Today one engine (Whisper *base*, Lithuanian forced) produces lyrics, and Edge-TTS with pitch shifting re-sings them. The baseline audit found the re-sung voice reads as speech (F0 spread 23.5 Hz against 150.5 Hz in the original). Voice gets its own pipeline, several STT and TTS engines, and its own checks.

**Pipeline stages**

| Stage | What it does | Candidates (chosen by tournament at Gate 0) | Done when (proposed) |
| --- | --- | --- | --- |
| 1. Isolate | Vocal stem, then lead vs backing split and de-reverb | MSST vocal and karaoke models; Demucs fallback | Lead stem has no audible backing on gold trio songs |
| 2. Detect | Each segment labelled as sung, spoken, rap or no voice; language per line | Silero VAD plus a sung/spoken classifier; Whisper language ID | Segment labels ≥ 90% correct; language per line ≥ 95% |
| 3. Understand (STT) | Several engines transcribe each line, then a consensus with per-word confidence | Cloud STT services, Whisper large-v3 / turbo, faster-whisper, a Lithuanian-tuned model. Later: local-only engines | Word error rate on gold lyrics ≤ baseline − 30% relative, measured per language |
| 4. Align | Words, then syllables, then phonemes, timed to the audio | WhisperX, MMS forced aligner, Montreal Forced Aligner | Median word-boundary error ≤ 80 ms against spot-checked timings |
| 5. Map to music | Each syllable tied to a note (melismas kept), notes tied to bars, bars to sections | In-house, using the F0 notes and beat grid | ≥ 90% of syllables on the right note in gold songs |
| 6. Identify | Which singer sings each line; how many voices | pyannote diarization plus F0 range per voice | Voice per line ≥ 90% correct on trio songs |
| 7. Re-voice | Speech by TTS, singing by a singing-voice synth, optional voice conversion | Cloud TTS and singing services, Edge-TTS (current), singing-voice synth (DiffSinger class), RVC-class conversion | Re-sung line follows the melody: F0 spread within 20% of the original |
| 8. Evaluate | WER, boundary error, syllable-note accuracy and voice ID per job | `accuracy_evaluator.py`, extended | Metrics stored per job; CI fails on regression |

**Voice actions to agree on** (same rules as What the user can do)

| ID | The user can… | Done when | Priority | Status |
| --- | --- | --- | --- | --- |
| V1 | Read the lyrics with each word highlighted as it is sung | Word highlighting stays within 100 ms of the audio across the whole song | Must | Proposed |
| V2 | See which parts are sung, spoken, rapped or instrumental | A voice lane on the timeline shows the four labels, colour-coded | Must | Proposed |
| V3 | See and correct the language of each line | English and Lithuanian are detected and transcribed; other languages are flagged as unsupported. Changing a line's language re-transcribes only that line | Must | Changed |
| V4 | See which singer sings each line | Lines are tagged Voice 1/2/3 (renamable), and harmonies show who joins | Must | Proposed |
| V5 | Fix a misheard word | Editing a word re-aligns that line in seconds, without reprocessing the song | Must | Proposed |
| V6 | See lyrics under the notes in the score | One syllable per note, melisma lines drawn; Lithuanian syllables and diacritics correct | Must | Changed |
| V7 | Compare what different STT engines heard and pick per line | Engine outputs side by side with confidence; the choice is saved | Should | Proposed |
| V8 | Export lyrics | Plain text, timed LRC (word level) and lyrics inside MusicXML and MIDI | Must | Proposed |
| V9 | Re-sing or re-speak a line with a synthetic voice and A/B it | The new line keeps the original melody and timing and switches with the original at the same playhead | Should | Proposed |
| V10 | Search the library by what is sung | Typing a word finds songs and jumps to the moment it is sung | Could | Proposed |
| V11 | Edit word-timed lyrics directly on the sheet | On the score the user can retype a word, drag a word or syllable to another note or time, split or merge syllables, and extend or remove a melisma. Highlighting (V1), playback and every export (V8) follow the edit at once. Undo works, and the edit survives reprocessing of other stems | Must | Agreed |

**Voice decisions (agreed 2026-10-18)**

| Topic | Decision | Effect on this DoD |
| --- | --- | --- |
| Languages | English and Lithuanian as parallel tracks from the start. Other languages later, as language packs | Every voice bar is measured separately for EN and LT, and both must pass for v1 |
| Cloud services | Audio may go to outside STT/TTS services now. A local-only path comes later | Cloud engines can take part in the stage 3 and 7 tournaments. Each job records which service processed it |
| Legal use | The user takes full responsibility for using the tool legally, including voice cloning and copyrighted audio | No in-app consent or rights checks. The terms of use state this |
| Gold standards | Only approved professional musicians provide gold-standard sheet music and lyrics | Every gold file records who wrote it and who approved it. Unapproved files don't count toward any bar |
| Lyric editing | The user must be able to edit word-timed lyrics manually on the sheet | Added as V11 (Must) |

## Every change

Every commit or PR that touches `apps/remix_studio`, `packages/audiocore` or the host must meet all of these. The pull request template repeats this list.

- [ ] Scoped commit message (`remix:`, `core:`, `docs:`, `ci:`) and no files outside the change's scope
- [ ] `uv run pytest -m "not slow and not artifact"` green in every package the change touches
- [ ] `tests/test_render_fingerprints.py` green. If a fingerprint changed, the sound change was intended, someone listened to it, and the commit says so
- [ ] New behaviour has at least one hermetic test that fails on bad output (stub models or tiny fixtures, no network)
- [ ] No absolute paths. New locations are added to `studio_paths.py`
- [ ] No ML dependency in `audiocore`
- [ ] Bad input (NaN, out-of-range values, corrupt or empty audio) returns a typed error, never a crash or silent output
- [ ] Every rendered file has true peak ≤ −0.7 dBFS
- [ ] Any new dependency or model checkpoint has its licence recorded and is on the allowlist (MIT, BSD, Apache-2.0)
- [ ] Docs updated where behaviour changed: `AGENTS.md`, `README.md`, the plan, or an ADR for decisions

## Per requirement

Each FR (numbered as in the PRD) is done when its criterion holds and its evidence is committed. Thresholds marked *baseline* are frozen at Gate 0.

| ID | Done when | Evidence |
| --- | --- | --- |
| FR-1 Ingest | File and URL inputs produce 48 kHz audio plus a manifest with input hash, model names and weight hashes. Re-running the same input reuses the cache | Hermetic test on a 5 s fixture; manifest schema test |
| FR-2 Separation | MSST writes 5 phase-aligned 48 kHz stems. Their sum stays within −40 dB of the input. Vocal SDR is at least the Demucs 6s baseline. If MSST fails, Demucs runs instead | `slow` test on gold reference stems; SDR table in the catalog |
| FR-3 Pitch | RMVPE and torchcrepe return F0 and confidence per 10 ms frame. A synthetic sine sweep is tracked within ±20 cents | Hermetic sweep test with stub weights; `slow` test with real weights |
| FR-4 Transcription | Every melodic stem gets a `.mid` and a `.musicxml` that music21 re-parses into the same notes. The Grand Staff SVG still renders | Round-trip test; gold-standard F-measure ≥ baseline + 15 |
| FR-5 Structure | Sections and chords are written as markers with start ≤ end and in-range times. Chord accuracy is measured on gold songs | Hermetic marker-validation test; accuracy row in catalog |
| FR-6 Synth matching | Returns the top-N patches, every parameter in [0, 1], each with its MR-STFT loss. The best patch beats the hand-modelled timbre on ≥ 80% of held-out clips | Hermetic test with a stub estimator; held-out evaluation report |
| FR-7 Session assembly | One call builds tracks, clips, patches and markers. Partial failures come back listed, existing media is never overwritten, and running it twice is idempotent | Agent-task test against the host (or the session-folder fallback) |
| FR-8 Score view | MusicXML renders and follows the playhead within one beat. Edits round-trip into the MIDI clip | Manual check recorded in the PR with a screenshot; round-trip test |
| FR-9 Evaluation | Every job on a gold song writes F-measure, SDR and timing to SQLite. CI fails on a drop of more than 2 points | CI job log; catalog rows |
| FR-10 Interfaces | Every stage runs from CLI and JSON with the same arguments. Errors have a code and a message, never a stack trace | Contract tests per stage; error-case tests |
| FR-11 Instrument families | Every stem carries a family label that the user can change. Each family meets its bar in Instrument families | Hermetic test per family; per-family metrics in the catalog |
| FR-12 Voice understanding | Stages 1–6 in Voice meet their bars on English and on Lithuanian gold lyrics, each. Each job records the services used | STT tournament report; recorded cloud responses in hermetic tests; voice metrics in the catalog |
| FR-13 Lyric editing | V11 passes its walkthrough; edits persist in the job and survive reprocessing of other stems | Round-trip test (edit, save, reload, export); walkthrough record |
| FR-14 Re-voicing | Stage 7 bar met: a re-sung line's F0 spread is within 20% of the original, with the same timing | Fingerprint test for each local engine; A/B listening note in the PR |
| FR-15 Gold provenance | Every gold file names its author and approving professional musician; files without approval are skipped by evaluation | Schema test on gold files; evaluation test that ignores unapproved files |
| FR-16 Gold data sourcing | Worker runs unattended for 7 days; every EN and LT gap has ≥ 3 candidates with V ≥ 60; ≥ 80% of V ≥ 85 candidates are approved over the first 50 reviews; R1–R7, R9 and R10 pass | Worker run log; review outcomes in the catalog; walkthrough records |
| FR-17 Score and performance | Every job stores score layer, performance layer and tempo map. Median beat error ≤ 50 ms against spot-checked anchors; ≥ 90% of written durations recovered by quantisation on gold; expression differences (scorecard table) are not counted as errors; a musician can mark performed variants | Layer schema test; anchor files per gold song; quantisation report |
| FR-18 Batch alignment | Unit index L1–L10 stored per job; route correct on all 3 LT songs; bar boundaries ≤ 50 ms median and chord spans ≥ 85% correct against musician-checked songs; note F computed only on written and embellished units; one song per language timed fully by ear | Unit-index schema test; musician-marked routes and modes; benchmark timing files |
| FR-19 Loops and mixes | M1–M5 pass their walkthroughs (M6–M8 if agreed); 20 random bar and phrase loops play with no audible click; exports carry tempo, key and chords; true peak ≤ −0.7 dBFS | Loop listening test record; walkthrough records |

## Per phase gate

A phase closes only when every box under its gate is ticked. Its work items still have to meet the two sections above. Each gate is a GitHub milestone with the same name.

**Gate 0 — Foundation and spike**

- [ ] `torch.cuda.is_available()` is True in the remix env, and the CPU path still passes the test suite
- [ ] At least one hermetic test per pipeline stage (ingest, separation, pitch, transcription, evaluation)
- [ ] Scorecard built and scoring 100 itself; its first run stored as the baseline for every deliverable in EN and LT
- [ ] SoundCraft spike report lists each command the PRD relies on as works, missing or broken
- [ ] An ADR records the host decision (SoundCraft, or Python studio plus web UI)
- [ ] Brief committed under `docs/plan/brief/` and the open questions answered or reassigned
- [ ] Approved gold standards: approval records (author, approving musician, scope, checksum) written for Grikiai, Virusas and Prie Topolio; musicians mark each song's form route and improvised spans; one LT song timed fully by ear as the benchmark; first EN gold songs commissioned or sourced

**Gate 1 — Sidecar upgrade**

- [ ] FR-1, FR-2, FR-3, FR-4, FR-9, FR-10, FR-11, FR-12, FR-17 and FR-18 meet their criteria
- [ ] Note F-measure ≥ baseline + 15 on the gold songs
- [ ] The existing studio (`server.py`, remixes) still works, and the render fingerprints are green or deliberately regenerated

**Gate 2 — Session assembly**

- [ ] FR-5 and FR-7 meet their criteria
- [ ] A 3-minute song becomes an openable session in ≤ 10 min on the GTX 1660
- [ ] Running the same input twice gives an identical session apart from timestamps

**Gate 3 — Synth matching, editing and UI**

- [ ] FR-6, FR-8, FR-13, FR-14 and FR-19 meet their criteria
- [ ] Every v1 success metric in the PRD is met (next section), and every Agreed action passes its walkthrough

## v1 release

v1 is done when all four gates are closed, every Agreed Must action in What the user can do and in Voice passes its walkthrough, every instrument family meets its bar, and every row below passes on the same commit.

| Criterion | Threshold | Measured by |
| --- | --- | --- |
| Note F-measure (onset ±50 ms, pitch ±50 cents) | Baseline + 15 points | `gold_standard_benchmark.py` |
| Vocal stem SDR | ≥ Demucs 6s baseline | Evaluation job on gold reference stems |
| Synth-match win rate | ≥ 80% of held-out clips | FR-6 evaluation report |
| Track to session | ≤ 10 min for 3 min of audio | Timed run on the GTX 1660 |
| True peak on every render | ≤ −0.7 dBFS | `audiocore.dsp.true_peak_dbfs` check in tests |
| Gold-standard coverage | ≥ 8 songs per language (EN and LT), ≥ 2 genres, each signed off by an approved professional musician | Count in `gold_standards/` |
| Test tiers | Hermetic, `slow` and `artifact` all green | `uv run pytest` full run log |
| Licences | Every dependency and checkpoint on the allowlist; no AGPL | Licence table in the repo |
| Docs | README run steps work on a fresh clone; ADRs current | One fresh-clone dry run |

## How to verify

Run these from `apps/remix_studio` unless noted. Paste the output, or link to it, in the PR.

| Check | Command | Evidence lives in |
| --- | --- | --- |
| Hermetic tier | `uv run pytest -m "not slow and not artifact"` | PR description; CI |
| Sound unchanged | `uv run pytest tests/test_render_fingerprints.py` | PR description; `tests/golden/` diff if regenerated |
| Full suite | `uv run pytest` (needs `data/remix` populated) | Gate checklist |
| Shared core | `cd packages/audiocore && uv run --extra tts pytest` | PR description; CI |
| Accuracy | `uv run python gold_standard_benchmark.py` | SQLite catalog `data/remix/db/remix_studio.db` |
| GPU available | `uv run python -c "import torch; print(torch.cuda.is_available())"` | Gate 0 checklist |
| Decisions | New ADR in `docs/adr/` | Git history |
| Scores | `uv run python -m scorecard run`, then `uv run python -m scorecard report` | SQLite tables `score_runs` and `scores`; the report linked in the PR |
