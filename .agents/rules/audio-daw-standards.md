# Audio DAW Engineering & Remix Studio Standards

These standards govern all digital signal processing (DSP), multi-track stem manipulation, notation rendering, and audio server endpoints in the Remix Studio (`apps/remix_studio`) and, for sections 1 and 5, the radio (`apps/radio`).

## 1. Zero-Clipping & True-Peak Headroom Rule
- All generated, transposed, or summed audio stems must maintain headroom &le; -0.7 dBFS (normalized linear amplitude max &le; 0.92).
- When combining or cross-synthesizing stems, apply `audiocore.dsp.limit_peak` (or `normalize_peak`) before writing to WAV/MP3 files. Both act on sample peak; measure inter-sample peaks with `audiocore.dsp.true_peak_dbfs`.
- Never output hard-clipped or floating-point overflow samples to client audio nodes.

## 2. Non-Blocking Ingestion & DSP Rule
- Demucs 6-stem separation, Librosa pitch tracking, chord recognition, and layer subtraction are computationally intensive. They must NEVER run synchronously inside an HTTP request handler.
- Run heavy operations inside asynchronous workers or background threads with thread-safe atomic status updates.
- Report continuous progress (0% to 100%) through the server's ingest task manager (`server.py` `ingest_manager`, polled via `/api/ingest/status`) so the UI status bar remains responsive.

## 3. Grand Staff Interactive Notation Invariant

> Superseded per instrument family by `docs/plan/dod.md#instrument-families` (FR-11): piano keeps the Grand Staff, guitar gets staff + TAB, bass gets bass clef + TAB, drums a percussion staff. Until a family's issue lands, the rule below still applies to it.

- Instruments spanning multiple octaves (Acoustic Guitar, Electric Guitar, Piano, Synths) must be rendered on a Dual-Clef Grand Staff.
- Notes with MIDI pitch < 55 (G3) map to the Bass Clef. Notes with MIDI pitch &ge; 55 map to the Treble Clef.
- SVG stave coordinates, ledger lines, and stem directions must be mathematically accurate according to diatonic pitch steps.
- Interactive notes in the SVG score must retain `data-midi`, `data-time`, `data-layer`, and `data-transposed` attributes for interactive audition.

## 4. Layer Surgery & SQLite Transaction Invariants
- Layer surgery operations (`split`, `merge`, `duplicate`, `delete`) must:
  1. Preserve original stem source files intact.
  2. Use phase-accurate waveform arithmetic (e.g. `diff = layer_A - layer_B`) when disaggregating stems.
  3. Enforce SQLite transactional integrity (`BEGIN TRANSACTION`, `COMMIT` on success, `ROLLBACK` on error).
  4. Sync metadata to the catalog (`studio_paths.DB_PATH`, i.e. `data/remix/db/remix_studio.db`, via `database/db.py`) with updated layer counts, stem paths, and key/tempo signatures.

## 5. Client WebAudio & Cache-Busting Rule
- When serving client scripts or stylesheets (`app.js`, `audio.js`, `render.js`, `style.css`), always attach or increment cache-busting query version parameters (e.g., `<script src="app.js?v=TIMESTAMP">`).
- WebAudio contexts must handle browser autoplay policy gracefully via explicit user gesture resume (`audioCtx.resume()`).
- Stems played concurrently must be sample-synchronized to an identical master clock time (`audioCtx.currentTime + delay`).

## 6. Unflattened Multi-Layer & Perceptual Integrity Invariant (Matt Pocock Methodology)
- **No Stem / Track Flattening**: All discrete layers identified during layer discovery (e.g. 3 distinct vocal staves for trios, individual guitar, upright bass, and drums) must be generated and preserved as independent, unflattened stems. Never collapse vocal counterpoint or distinct instruments into generic monolithic stems.
- **Chronological Timeline Sequencing**: Vocal synthesis engines must advance timestamps sequentially ($t_{k+1} = t_k + \Delta t_k$) across the full duration of the performance. Modulo-measure or static measure index calculations that collapse audio into the first few seconds are strictly prohibited.
- **Non-Tautological Perceptual Integrity Gates**: Audio tests must assert perceptual integrity:
  1. *Temporal Continuity*: Audio energy must span $>80\%$ of the active performance window (no silent tails or squished bursts).
  2. *Melodic F0 Dynamics*: Vocal pitch contour must demonstrate authentic singing melody ($\text{std}(F_0) \ge 12\text{ Hz}$, $\text{range}(F_0) \ge 40\text{ Hz}$), preventing flat monotone speech.
  3. *Arrangement Staggering*: Voice entries and rests must match score dynamics (e.g. solo intro silence on backing voices, synchronous harmony entry at designated measures).
- **Red-Capable Command Requirement**: In accordance with Matt Pocock's *diagnosing-bugs* and *TDD* disciplines, never attempt bug fixes or DSP refactoring without a reproduction command that reliably fails in the red state before turning green.

