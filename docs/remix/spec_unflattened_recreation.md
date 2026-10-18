# Specification: Unflattened Multi-Layer Music & Vocal Harmony Recreation
## Feature Slug: `unflattened-layer-recreation`
## Status: `ready-for-agent`

---

## 1. Problem Statement

Previous attempts to synthetically recreate vocal trio songs (*The Ditties*: *Grikiai*, *Virusas*, *Prie Topolio*) suffered from three fatal acoustic defects:
1. **Melodic Flattening**: Spoken sentences were shifted by a single static pitch offset, creating monotone pitched-up speech rather than melodic singing of discrete notes ($G4 \to F4 \to E4 \to D4$).
2. **Timing Collapse**: A broken modulo timing loop (`i % 4` with missing `measure` key) collapsed 30 notes onto the first 2 seconds, leaving 28 seconds of digital silence.
3. **Harmonic Dissonance**: Unaligned voice entrances produced clashing chromatic noise instead of close 3-part jazz harmony.
4. **Toy Instrumentation**: Instrument accompaniments used primitive 1-oscillator sine beeps rather than the acoustic swing rhythm section (archtop guitar, upright bass, brushed snare) present in the master recordings.

---

## 2. Solution

An end-to-end unflattened multi-layer recreation pipeline:
1. **Chronological Syllabic Singing Engine**: Sequences notes chronologically ($t_{k+1} = t_k + \Delta t_k$), detects spatial barlines on the Sibelius score, and modulates Edge-TTS phonetic kernels to exact target MIDI pitches with genuine frequency vibrato.
2. **Discrete 3-Voice Staggering**: Voice 1 (Veronika Lead Soprano) opens solo; Voice 2 (Rūta) and Voice 3 (Rūtelė) enter synchronously at Measure 13, locking into close jazz triads.
3. **Dedicated Acoustic Rhythm Section**: Separate physical modeling stems for acoustic archtop guitar comping on beats 2 & 4, walking double bass on beats 1 & 3, and brushed swing drums.
4. **Headroom Compliance**: Equal-power stereo mixing strictly enforcing ITU-R BS.1770 True Peak $\le -0.7\text{ dBFS}$.

---

## 3. User Stories

1. **As a listener**, I want to hear Veronika sing distinct melodic pitches for each syllable (*"E-su dai-li pa-nė-lė"* stepping down $G4 \to F4 \to E4 \to D4$), so that the song's melody is immediately recognizable.
2. **As a listener**, I want vocal singing to continue smoothly across the entire 30-second window, so that there is no abrupt collapse into silence after 2 seconds.
3. **As a listener**, I want Rūta and Rūtelė to enter in harmony at Measure 13 (*"ap-žiū-ri-nė-ju vit-ri-nas"*), so that the signature close 3-part swing harmony of The Ditties is preserved.
4. **As a listener**, I want the acoustic rhythm guitar to comp crisply on beats 2 and 4, so that the swing feel drives the music forward naturally.
5. **As a listener**, I want the upright double bass to play warm, resonant acoustic notes on beats 1 and 3, so that the harmonic foundation supports the vocal chords.
6. **As a listener**, I want the brushed snare and swing hi-hats to groove on off-beat swing eighths, so that the jazz drum feel is authentic.
7. **As a DAW user**, I want to mute, solo, and adjust individual stems (`synth_vocals_voice1.wav`, `synth_vocals_voice2.wav`, `synth_vocals_voice3.wav`, `synth_guitar.wav`, `synth_bass.wav`, `synth_drums.wav`), so that I can perform layer surgery and remixes.
8. **As a mastering engineer**, I want all generated stems and the master mix to maintain True Peak $\le -0.7\text{ dBFS}$, so that zero clipping or inter-sample distortion occurs.
9. **As a radio producer**, I want this unflattened synthesis pipeline to generalize identically to *Virusas* and *Prie Topolio*, so that the entire gold-standard test suite is reproducible.
10. **As an automated test runner**, I want non-tautological perceptual tests asserting continuous energy, F0 movement, and harmony synchronization, so that regressions are caught automatically before delivery.

---

## 4. Implementation Decisions

- **Domain Model Types**: All data entities are defined in `domain_models.py` (`MusicalNote`, `ChordVoicing`, `VocalTrack`, `RhythmTrack`, `SongManifest`).
- **Phonetic Engine**: Microsoft Edge Neural TTS (`lt-LT-OnaNeural`) generated per syllable or cached phrase slice.
- **Pitch Modulation**: Formant-preserving phase vocoder / PSOLA shifting speech base ($210\text{ Hz}$ / MIDI 57) to target note MIDI.
- **Vibrato Mechanism**: Pitch frequency modulation ($\pm 35\text{ cents}$, $5.5\text{ Hz}$) initiated after $100\text{ ms}$ attack on notes $> 300\text{ ms}$ (NOT amplitude tremolo).
- **Barline Detection**: Spatial score delta $\Delta x > 32\text{ pt}$ or system wrap triggers measure-aligned rest insertion.
- **Mastering Limiter**: Soft-knee inter-sample limiter clamping maximum linear peak to $0.92$ ($-0.72\text{ dBFS}$).

---

## 5. Testing Decisions & Public Seams

### What Makes a Good Test
Tests must assert **external behavioral properties** observable in the audio output, not internal implementation variables. They must be capable of failing (RED) on bad audio.

### The 5 Agreed Public Seams:
1. **`Seam 1: Timeline Continuity`** ([`test_vocal_timeline_continuous_energy`](file:///d:/radio/remix_studio/tests/test_audio_perceptual_integrity.py#L18)):
   - Verifies active energy ($\ge -35\text{ dBFS}$) in $\ge 80\%$ of 2-second windows across 30 seconds.
2. **`Seam 2: Melodic F0 Dynamics`** ([`test_melodic_f0_pitch_dynamics`](file:///d:/radio/remix_studio/tests/test_audio_perceptual_integrity.py#L48)):
   - Verifies voiced $F_0$ movement has standard deviation $\ge 12\text{ Hz}$ and pitch range $\ge 40\text{ Hz}$.
3. **`Seam 3: Harmony Synchronization`** ([`test_trio_harmony_synchronization`](file:///d:/radio/remix_studio/tests/test_audio_perceptual_integrity.py#L67)):
   - Verifies Voices 2 and 3 are silent during 0–4s and active ($\ge -30\text{ dBFS}$) during 10–18s.
4. **`Seam 4: Rhythm Stem Presence`** ([`test_rhythm_section_stems_presence`](file:///d:/radio/remix_studio/tests/test_audio_perceptual_integrity.py#L94)):
   - Verifies guitar, bass, and drums stems exist with RMS $\ge -45\text{ dBFS}$ and peak $> 0.05$.
5. **`Seam 5: DAW Headroom`** ([`test_master_recreation_headroom_and_loudness`](file:///d:/radio/remix_studio/tests/test_audio_perceptual_integrity.py#L108)):
   - Verifies master mix True Peak $\le -0.7\text{ dBFS}$ and $\ge -18.0\text{ dBFS}$.

---

## 6. Out of Scope

- Real-time VST3 plugin compilation (all rendering is async non-blocking offline/server pipeline).
- Manual pitch-correction GUI editing (vocal pitch curves are governed directly by Sibelius score gold standards).
- 4-minute full song rendering during unit tests (tests validate 30-second representative verse/chorus slices).
