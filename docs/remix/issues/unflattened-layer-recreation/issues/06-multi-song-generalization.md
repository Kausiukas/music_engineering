# 06: Multi-Song Ingestion & Verification for Virusas and Prie Topolio

**What to build:** Generalizes the unflattened synthesis engine across the remaining two gold-standard songs:
1. *Virusas* (`A02 Virusas.mp3`, `Virusas - Full Score (1).pdf`, 115.0 BPM)
2. *Prie Topolio* (`B04 Prie topolio.mp3`, `Prie Topolio (2) (1) (1).pdf`, 114.0 BPM)

**Blocked by:** 05-master-mix-limiter

**Status:** ready-for-agent

## Acceptance Criteria
- [ ] Stems generated for Virusas: `synth_vocals_voice1.wav`, `synth_vocals_voice2.wav`, `synth_vocals_voice3.wav`, `synth_guitar.wav`, `synth_bass.wav`, `synth_drums.wav`, `master_synthetic_recreation_+0.wav`.
- [ ] Stems generated for Prie Topolio with identical unflattened separation.
- [ ] All stems pass `test_audio_perceptual_integrity.py` and True Peak $\le -0.7\text{ dBFS}$.
- [ ] Full regression suite passes cleanly via `pytest tests/`.
