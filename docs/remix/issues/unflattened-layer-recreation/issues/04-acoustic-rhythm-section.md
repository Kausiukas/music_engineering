# 04: Dedicated Acoustic Rhythm Section Stems

**What to build:** Synthesizes dedicated, unflattened rhythm section stems:
1. Acoustic Guitar (`synth_guitar.wav`): Freddie Green swing comping on beats 2 & 4.
2. Upright Double Bass (`synth_bass.wav`): Plucked acoustic bass on beats 1 & 3 following chord roots.
3. Swing Drums (`synth_drums.wav`): Brushed snare shuffle on swing eighths.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

## Acceptance Criteria
- [ ] Stems exist independently without sum-collapsing into generic sine waves.
- [ ] Each stem exhibits active acoustic energy (RMS $\ge -45\text{ dBFS}$, peak $> 0.05$).
- [ ] Chords match the Sibelius score (`gold_standard_grikiai.json`).
- [ ] Verified by `test_rhythm_section_stems_presence()`.
