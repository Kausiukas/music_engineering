# 05: Multi-Track Summing & True Peak Limiter

**What to build:** Equal-power stereo summing engine balancing 3 vocal tracks and 3 rhythm section stems into `master_synthetic_recreation_+0.wav`, enforcing ITU-R BS.1770 true peak limit $\le -0.7\text{ dBFS}$ with healthy commercial loudness.

**Blocked by:** 03-trio-harmony-staggering, 04-acoustic-rhythm-section

**Status:** ready-for-agent

## Acceptance Criteria
- [ ] Master recreation mix is saved with all 6 unflattened stems balanced.
- [ ] True Peak level strictly satisfies $\le -0.7\text{ dBFS}$ ($0.92$ linear).
- [ ] Master peak is musically audible and healthy ($\ge -18.0\text{ dBFS}$).
- [ ] Verified by `test_master_recreation_headroom_and_loudness()`.
