# 01: Note Chronological Accumulator & Barline Detector

**What to build:** An accumulative musical timing engine that places notes sequentially ($t_{k+1} = t_k + \Delta t_k$), detects spatial score barlines ($\Delta x > 32\text{ pt}$), and inserts measure-aligned rests. Eliminates the 2-second collapse bug.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

## Acceptance Criteria
- [ ] Each note starts after the previous note finishes ($t_{k+1} \ge t_k$).
- [ ] Spatial score spacing $\Delta x > 32\text{ pt}$ or system break triggers an intentional rest gap.
- [ ] Active audio spans smoothly across the entire 30-second window ($>80\%$ duty cycle).
- [ ] Verified by `test_vocal_timeline_continuous_energy()`.
