# Music Engineering

An audio reverse-engineering workstation: it takes a mixed recording apart into stems, notes, sheet music, timed lyrics and synth patches, measures how trustworthy each result is, and lets the user loop, recreate and remix the parts.

## Recordings and jobs

**Job**:
One recording taken through the pipeline, with everything produced for it and a manifest of inputs, models and services used.
_Avoid_: Song run, session (a session is the host's editable project)

**Stem**:
One isolated part of a recording (vocals, bass, drums, synth/other, sfx), produced by separation.
_Avoid_: Layer, track (a track is a lane in the host session)

**Instrument family**:
The kind of instrument a stem holds (piano, guitar, bass, drums and kick, synth, vocals, sfx); it selects the transcriber, the notation and the checks.
_Avoid_: Instrument type, category

**Host**:
The DAW-style application that opens a job as an editable session: SoundCraft or the web studio, chosen at Gate 0.
_Avoid_: Frontend, DAW (when the choice is still open)

## Music structure

**Score layer**:
What would be written: notes, durations, meter, chords and lyric syllables, measured in bars and beats.
_Avoid_: Sheet, notation (notation is how the score layer is drawn)

**Performance layer**:
What actually sounds in the recording: when each note and word starts and ends, with its pitch curve, measured in seconds.
_Avoid_: Transcription (a transcription has both layers)

**Tempo map**:
The link between the two layers: the second each beat falls on, plus each note's offset from its beat.
_Avoid_: Beat grid, click track

**Unit**:
One span of music at a level of the unit ladder, from a 10 ms frame (L0) to the whole song (L10), aligned inside its parent unit.
_Avoid_: Segment, chunk, slice

**Chord span**:
The unit (L5) covering how long one chord lasts.
_Avoid_: Harmonic segment

**Form cycle**:
The unit (L9) covering one pass through a tune's form; in jazz, a chorus.
_Avoid_: Chorus (ambiguous with a song's chorus section), loop

**Route**:
The order in which a recording actually plays the sheet's form cycles and sections, including repeats, extra solo choruses and cuts.
_Avoid_: Arrangement, structure

**Mode**:
How freely a unit from phrase up is played relative to the sheet: written, embellished, improvised or comping. It sets the lowest level the unit is judged at.
_Avoid_: Style, type

**Expression**:
A difference from the score layer that belongs to the performance (timing feel, swing, slides, ornaments) and is not counted as an error.
_Avoid_: Deviation, mistake

**Performed variant**:
A consistent difference from the sheet that a musician has marked as how the piece is performed, kept in the gold set beside the written version.
_Avoid_: Alternate take

## Truth and evidence

**Gold item**:
One song or clip with a reference a musician has approved for a stated scope (notes, chords, lyrics, timing).
_Avoid_: Ground truth (the whole gold set), test song, fixture

**Gold set**:
All gold items for one evidence set and language.
_Avoid_: Dataset, corpus

**Approved musician**:
A professional musician on the approved list who may author or approve gold items for given languages and instruments.
_Avoid_: Reviewer, annotator

**Approval record**:
The `approval.json` beside a gold item: author, approving musician, date, scope and file checksums; any later file change voids it.
_Avoid_: Sign-off

**Benchmark song**:
A gold item whose bar and word timings a musician marked completely by ear; the only full evidence for timing below bar level.
_Avoid_: Reference song

**Derived timing**:
Timing produced by aligning an approved score to its recording and spot-checking it; full evidence from bar level up, half below.
_Avoid_: Auto timing, estimated timing

**Spot-check**:
A musician listening at anchor points (phrase starts, one per 4 bars, plus 10 random points) to confirm or correct derived timing.
_Avoid_: Sampling, QA pass

**Candidate**:
A song, score, MIDI file or lyric file found by sourcing and waiting for review before it can become a gold item.
_Avoid_: Lead, suggestion

**Validity score**:
The 0–100 estimate (V) of how likely a candidate's reference is correct for its audio, computed from eight signals.
_Avoid_: Confidence, quality score

## Scoring and delivery

**Deliverable**:
Anything the plan scores: a requirement (FR), an instrument family (F), a user action (U, V, R, M) or the scorecard itself.
_Avoid_: Feature, epic

**Score**:
The 0–100 number per deliverable and language, floor(100 × quality × evidence); 100 means done.
_Avoid_: Rating, progress

**Quality**:
Q, the weighted mean of a deliverable's components (accuracy, user acceptance, robustness, performance, consistency), each normalised between floor and target.
_Avoid_: Accuracy (only one component)

**Evidence**:
E, the share of a deliverable's required gold items that back its measurement; unreviewed candidates with V ≥ 85 count half.
_Avoid_: Coverage, confidence

**Hard check**:
A failure (crash on valid input, true peak over −0.7 dBFS, unintended fingerprint change, failing hermetic test, disallowed licence) that caps a score at 39.
_Avoid_: Gate (a gate is a phase checkpoint)

**Gate**:
The checkpoint closing a phase (Gate 0 to Gate 3), passed when its DoD checklist is ticked.
_Avoid_: Milestone (the GitHub object that tracks a gate), phase

**Language pack**:
What one language supplies to the shared pipeline: text normalisation, syllable rules, aligner, engine choices and required evidence.
_Avoid_: Locale

**Language trust score**:
The mean score of a language's language-dependent deliverables, Must items weighted twice.
_Avoid_: Language score

**Walkthrough**:
A recorded run of a user action's done-when text on real songs, passed or failed as a whole.
_Avoid_: Demo, UAT

**Agreement status**:
Whether a plan row is Proposed, Agreed, Changed or Cut; decided in the plan, separate from work status.
_Avoid_: Status (work status lives on the board)

## Work tracking

**Ticket**:
A vertical slice of one deliverable, sized for one agent session and filed as a sub-issue of the deliverable's issue.
_Avoid_: Task (a Gate 0 enabling item), story

**Map**:
The issue labelled `wayfinder:map` whose child tickets are open decisions, resolved one per session.
_Avoid_: Roadmap, decision log (decisions live in their tickets and ADRs)
