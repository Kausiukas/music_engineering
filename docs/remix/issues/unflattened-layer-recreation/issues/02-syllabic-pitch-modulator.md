# 02: Syllabic Melodic Pitch Modulator & Frequency Vibrato

**What to build:** Syllable-level phase vocoder pitch shifting that modulates speech phonemes directly to target MIDI note frequencies ($G4 \to F4 \to E4 \to D4$), sustaining vowels to exact note durations, and applying frequency vibrato ($\pm 35\text{ cents}$, $5.5\text{ Hz}$). Eliminates flat monotone speech.

**Blocked by:** 01-timeline-sequencer

**Status:** ready-for-agent

## Acceptance Criteria
- [ ] Each syllable is shifted to its exact target MIDI pitch ($F_0 = 440 \cdot 2^{(\text{midi}-69)/12}$).
- [ ] Vowels sustain for exact note duration ($1/4$ note = 0.534s at 112.3 BPM).
- [ ] Pitched audio exhibits dynamic pitch movement ($\text{std}(F_0) \ge 12\text{ Hz}$, range $\ge 40\text{ Hz}$).
- [ ] Verified by `test_melodic_f0_pitch_dynamics()`.
