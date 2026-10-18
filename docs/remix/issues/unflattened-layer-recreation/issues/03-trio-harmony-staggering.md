# 03: 3-Voice Trio Harmony Staggering & Concordance

**What to build:** Synchronizes multi-voice entrances: Voice 1 (Veronika Lead Soprano) sings solo during Measures 9–12 ($0.0\text{s} - 8.5\text{s}$), while Voice 2 (Rūta) and Voice 3 (Rūtelė) enter in close harmony at Measure 13 ($t = 8.55\text{s}$), forming verified jazz triads.

**Blocked by:** 02-syllabic-pitch-modulator

**Status:** ready-for-agent

## Acceptance Criteria
- [ ] Voices 2 and 3 remain resting ($\le -45\text{ dBFS}$) during Voice 1's solo opening ($0 - 4\text{s}$).
- [ ] Voices 2 and 3 enter actively ($\ge -30\text{ dBFS}$) at Measure 13 ($t = 8.55\text{s}$).
- [ ] Simultaneous notes form concordant triads (major/minor 3rds, 5ths, 6ths).
- [ ] Verified by `test_trio_harmony_synchronization()`.
