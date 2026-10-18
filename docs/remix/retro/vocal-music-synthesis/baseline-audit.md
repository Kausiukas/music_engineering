# Forensic Baseline Audit: Master Recording vs. Synthetic Reconstruction

## 1. Audit Perimeter & Scope

- **Slice**: Multi-Track Vocal & Instrumental Synthetic Recreation Engine
- **Files Audited**:
  - `remix_studio/unflattened_layer_recreator.py`
  - `remix_studio/domain_models.py`
  - `remix_studio/gold_standards/`
  - `remix_studio/recreations/grikiai/`
  - Ground truth reference: `d:\radio\test\Grikiai.wav` (96 kHz, 24-bit stereo master)
- **Current Phase**: Phase 1 — Present-State Forensic Audit

---

## 2. Empirical Acoustic Measurement Delta

The table below contrasts the empirical measurements extracted from the **Original Master Performance** (`d:\radio\test\Grikiai.wav`, 20s–35s vocal entrance) against the **Synthetic Reconstruction** (`recreations/grikiai/`):

| Acoustic Feature | Original Performance (`Grikiai.wav`) | Current Synthetic Output (`synth_*.wav`) | Gap Diagnosis |
| :--- | :--- | :--- | :--- |
| **Vocal Pitch Center (F0 Mean)** | **245.8 Hz** (Note: B3) | **259.7 Hz** (Note: C4) | **MATCHED** ($\pm 14\text{ Hz}$): Both operate in the authentic low mezzo/contralto register. |
| **Vocal Pitch Dynamic (F0 Std)** | **150.5 Hz** (Active melodic intervals) | **23.5 Hz** (Speech prosody inflection) | **CRITICAL GAP**: Real singer leaps between melodic scale degrees (130 Hz to 340+ Hz). Synthetic voice recites within a static conversational band. |
| **Vocal Pitch Range** | **532.3 Hz** ($[130.8, 663.1]\text{ Hz}$) | **151.1 Hz** ($[181.3, 301.4]\text{ Hz}$) | **CRITICAL GAP**: Lacks octaves, musical leaps, and scale transitions. |
| **Vocal Spectral Centroid** | **2230 Hz** (Singer's formant brilliance) | **1226 Hz** (Muffled speech spectrum) | **CRITICAL GAP**: Synthetic voice lacks upper harmonic projection and 3 kHz resonant energy. |
| **Guitar Spectral Centroid** | **1443 Hz** (Acoustic wood & pick attack) | **517 Hz** (Muffled sine wave decay) | **CRITICAL GAP**: Algorithmic sine waves lack string pick transient and archtop body resonance. |
| **Upright Bass Centroid** | **1448 Hz** (Finger snap, string buzz, wood) | **424 Hz** (Pure sub-bass sine tone) | **CRITICAL GAP**: Synthetic bass has no tactile string slap or acoustic room bloom. |
| **Acoustic Production Glue** | 150ms vintage jazz room early reflections | 0ms sterile digital direct feed | **CRITICAL GAP**: Sounds like disparate elements stacked on top of each other rather than a band in a room. |

---

## 3. Key Forensic Discoveries

1. **The Melody Scale Degree Deficit**:
   - The user perceives the voice as "better, but not yet good" because the speech TTS model does not sing the descending musical line defined in the sheet music (`G4 -> F4 -> E4 -> C4`).
   - Although the pitch offset ($+35\text{ Hz}$) placed the voice in the correct female register, the internal pitch variation ($23.5\text{ Hz}$ std) is purely conversational speech melody, not musical melody ($150.5\text{ Hz}$ std).

2. **The 8-Bit Synthetic Rhythm Section Trap**:
   - The rhythm section was written as mathematical equations: $\sin(2\pi f t)e^{-t/\tau}$.
   - While theoretically unflattened, human ears immediately recognize sine decays as computer-generated test tones rather than a living jazz trio.

3. **Formant Muffling vs. Singer's Formant**:
   - The original recording has significant energy in the 2.5 kHz to 4.0 kHz band (the classical "singer's formant" which allows a human voice to cut through an acoustic band).
   - The neural TTS model filters out this energy to sound natural for spoken conversation in quiet headphones, resulting in a muffled, distant vocal in a musical mix.
