"""
vocal_trio_tournament.py - Vectorized Multi-Method Separation Tournament for Female Vocal Trios
Evaluates:
  - Method A: Spatial Azimuth (ILD/IPD) Panning Clustering
  - Method B: Multi-Pitch Harmonic Saliency + Vectorized Harmonic Comb Filtering
  - Method C: Harmonic QUBO Boltzmann Annealing Voice Solver (Ising Hamiltonian)
  - Method D: Hybrid Spatial-Guided QUBO Comb Filtering (The Unified Model)

Computes objective metrics against the Sibelius Ground Truth via GoldStandardBenchmark.
"""

import os
import studio_paths
import sys
import json
import time
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
import soundfile as sf
import librosa
from scipy.signal import stft, istft

# Add parent path for imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from gold_standard_benchmark import GoldStandardBenchmark


class VocalTrioTournament:
    """Executes the 4-method separation tournament on isolated vocal audio."""

    def __init__(self, sample_rate: int = 44100):
        self.sr = sample_rate
        self.n_fft = 2048
        self.hop_length = 512
        self.benchmark = GoldStandardBenchmark()

    def load_vocals(self, vocal_wav_path: str) -> np.ndarray:
        """Loads vocal audio ensuring 2-channel stereo format (2, N)."""
        data, sr = sf.read(vocal_wav_path)
        if sr != self.sr:
            data = librosa.resample(data.T, orig_sr=sr, target_sr=self.sr).T
        if data.ndim == 1:
            data = np.stack([data, data], axis=1)
        return data.T  # returns (2, samples)

    @staticmethod
    def _vectorized_harmonic_mask(f_stft: np.ndarray, f_target: np.ndarray, bandwidth: float = 30.0) -> np.ndarray:
        """Computes vectorized time-frequency harmonic comb mask without Python loops."""
        # f_stft: (F,), f_target: (T,)
        f_grid = f_stft[:, None]  # (F, 1)
        # Compute min distance across harmonics 1..4
        d_min = np.abs(f_grid - f_target[None, :])  # harmonic 1
        for k in range(2, 5):
            d_k = np.abs(f_grid - (k * f_target[None, :]))
            d_min = np.minimum(d_min, d_k)
        return np.exp(- (d_min / bandwidth) ** 2)

    # =========================================================================
    # Method A: Spatial Azimuth (ILD/IPD) Panning Masking
    # =========================================================================
    def method_a_spatial_azimuth(self, vocal_stereo: np.ndarray) -> Dict[str, np.ndarray]:
        """Separates 3 voices using stereo panning azimuth clustering (Left, Center, Right)."""
        L = vocal_stereo[0]
        R = vocal_stereo[1]

        f, t, Zxx_L = stft(L, fs=self.sr, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)
        _, _, Zxx_R = stft(R, fs=self.sr, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)

        mag_L = np.abs(Zxx_L) + 1e-9
        mag_R = np.abs(Zxx_R) + 1e-9

        # Azimuth metric: -1.0 (hard left) to +1.0 (hard right)
        azimuth = (mag_R - mag_L) / (mag_L + mag_R)

        mask_v1 = np.exp(- (azimuth / 0.18) ** 2)  # Gaussian centered at 0 (Veronika Lead)
        mask_v2 = np.where(azimuth < -0.08, 1.0 - mask_v1, 0.05)  # Left (Rūta Harmony)
        mask_v3 = np.where(azimuth > 0.08, 1.0 - mask_v1, 0.05)   # Right (Rūtelė Alto)

        mask_sum = mask_v1 + mask_v2 + mask_v3 + 1e-6
        mask_v1 /= mask_sum
        mask_v2 /= mask_sum
        mask_v3 /= mask_sum

        Z_v1 = (Zxx_L + Zxx_R) * 0.5 * mask_v1
        Z_v2 = Zxx_L * mask_v2
        Z_v3 = Zxx_R * mask_v3

        _, stem_v1 = istft(Z_v1, fs=self.sr, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)
        _, stem_v2 = istft(Z_v2, fs=self.sr, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)
        _, stem_v3 = istft(Z_v3, fs=self.sr, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)

        return {
            'voice1_veronika': stem_v1[:vocal_stereo.shape[1]],
            'voice2_ruta': stem_v2[:vocal_stereo.shape[1]],
            'voice3_rutele': stem_v3[:vocal_stereo.shape[1]]
        }

    # =========================================================================
    # Method B: Multi-Pitch Harmonic Saliency + Vectorized Comb Filtering
    # =========================================================================
    def method_b_harmonic_saliency_dp(self, vocal_stereo: np.ndarray) -> Dict[str, np.ndarray]:
        """Separates 3 voices by multi-pitch CQT harmonic tracking & vectorized comb masking."""
        mono = np.mean(vocal_stereo, axis=0)
        cqt = np.abs(librosa.cqt(mono, sr=self.sr, hop_length=self.hop_length, fmin=130.81, n_bins=72, bins_per_octave=24))
        freqs = librosa.cqt_frequencies(n_bins=72, fmin=130.81, bins_per_octave=24)

        n_frames = cqt.shape[1]
        pitch_trajectories = np.zeros((3, n_frames))

        for t_idx in range(n_frames):
            frame = cqt[:, t_idx]
            top_bins = np.argsort(frame)[-6:]
            top_bins.sort()
            # Pick bottom, middle, top
            pitch_trajectories[2, t_idx] = freqs[top_bins[0]]  # Voice 3 (Low)
            pitch_trajectories[1, t_idx] = freqs[top_bins[len(top_bins)//2]]  # Voice 2 (Mid)
            pitch_trajectories[0, t_idx] = freqs[top_bins[-1]]  # Voice 1 (High)

        f_stft, t_stft, Zxx = stft(mono, fs=self.sr, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)
        n_stft = min(n_frames, Zxx.shape[1])
        Zxx = Zxx[:, :n_stft]

        w1 = self._vectorized_harmonic_mask(f_stft, pitch_trajectories[0, :n_stft], bandwidth=32.0)
        w2 = self._vectorized_harmonic_mask(f_stft, pitch_trajectories[1, :n_stft], bandwidth=32.0)
        w3 = self._vectorized_harmonic_mask(f_stft, pitch_trajectories[2, :n_stft], bandwidth=32.0)
        tot = w1 + w2 + w3 + 1e-5

        m1, m2, m3 = w1 / tot, w2 / tot, w3 / tot

        _, stem_v1 = istft(Zxx * m1, fs=self.sr, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)
        _, stem_v2 = istft(Zxx * m2, fs=self.sr, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)
        _, stem_v3 = istft(Zxx * m3, fs=self.sr, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)

        return {
            'voice1_veronika': stem_v1[:vocal_stereo.shape[1]],
            'voice2_ruta': stem_v2[:vocal_stereo.shape[1]],
            'voice3_rutele': stem_v3[:vocal_stereo.shape[1]]
        }

    # =========================================================================
    # Method C: Harmonic QUBO Boltzmann Annealing Voice Solver
    # =========================================================================
    def method_c_qubo_solver(self, vocal_stereo: np.ndarray) -> Dict[str, np.ndarray]:
        """Separates 3 voices by solving the 7-spin Harmonic QUBO Hamiltonian across frames."""
        mono = np.mean(vocal_stereo, axis=0)
        cqt = np.abs(librosa.cqt(mono, sr=self.sr, hop_length=self.hop_length, fmin=130.81, n_bins=72, bins_per_octave=24))
        freqs = librosa.cqt_frequencies(n_bins=72, fmin=130.81, bins_per_octave=24)
        n_frames = cqt.shape[1]

        # Precompute all 35 combinations of 3 spins chosen from 7 (cardinality 3)
        valid_states = []
        for s_int in range(1, 128):
            st = np.array([(s_int >> b) & 1 for b in range(7)], dtype=float)
            if np.sum(st) == 3:
                valid_states.append(st)
        valid_states = np.array(valid_states)  # (35, 7)

        pitch_trajectories = np.zeros((3, n_frames))

        for t_idx in range(n_frames):
            frame = cqt[:, t_idx]
            top_bins = np.argsort(frame)[-7:]
            top_bins.sort()

            # Construct 7x7 J matrix
            cand_freqs = freqs[top_bins]
            ratios = cand_freqs[:, None] / (cand_freqs[None, :] + 1e-6)
            # Vectorized reward for 3rds (~1.25) and 5ths (~1.5)
            J = np.where((ratios >= 1.15) & (ratios <= 1.30), 2.0, 0.0)
            J = np.where((ratios >= 1.45) & (ratios <= 1.55), 2.5, J)
            J = np.where((ratios < 1.06) & (ratios > 1.0), -2.0, J)
            np.fill_diagonal(J, 0.0)

            h = frame[top_bins] / (np.max(frame[top_bins]) + 1e-6)

            # Evaluate all 35 states simultaneously via vectorization
            interactions = -0.5 * np.einsum('ni,ij,nj->n', valid_states, J, valid_states)
            linears = - np.dot(valid_states, h)
            energies = interactions + linears
            best_idx = np.argmin(energies)
            chosen_state = valid_states[best_idx]

            chosen_bins = top_bins[chosen_state == 1]
            chosen_bins.sort()

            pitch_trajectories[0, t_idx] = freqs[chosen_bins[2]]  # Veronika Top
            pitch_trajectories[1, t_idx] = freqs[chosen_bins[1]]  # Rūta Mid
            pitch_trajectories[2, t_idx] = freqs[chosen_bins[0]]  # Rūtelė Bot

        f_stft, t_stft, Zxx = stft(mono, fs=self.sr, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)
        n_stft = min(n_frames, Zxx.shape[1])
        Zxx = Zxx[:, :n_stft]

        w1 = self._vectorized_harmonic_mask(f_stft, pitch_trajectories[0, :n_stft], bandwidth=28.0)
        w2 = self._vectorized_harmonic_mask(f_stft, pitch_trajectories[1, :n_stft], bandwidth=28.0)
        w3 = self._vectorized_harmonic_mask(f_stft, pitch_trajectories[2, :n_stft], bandwidth=28.0)
        tot = w1 + w2 + w3 + 1e-5

        m1, m2, m3 = w1 / tot, w2 / tot, w3 / tot

        _, stem_v1 = istft(Zxx * m1, fs=self.sr, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)
        _, stem_v2 = istft(Zxx * m2, fs=self.sr, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)
        _, stem_v3 = istft(Zxx * m3, fs=self.sr, nperseg=self.n_fft, noverlap=self.n_fft - self.hop_length)

        return {
            'voice1_veronika': stem_v1[:vocal_stereo.shape[1]],
            'voice2_ruta': stem_v2[:vocal_stereo.shape[1]],
            'voice3_rutele': stem_v3[:vocal_stereo.shape[1]]
        }

    # =========================================================================
    # Method D: Hybrid Spatial-Guided QUBO Comb Filtering (The Unified Model)
    # =========================================================================
    def method_d_hybrid_spatial_qubo(self, vocal_stereo: np.ndarray) -> Dict[str, np.ndarray]:
        """Fuses spatial stereo azimuth with QUBO harmonic optimization for maximal isolation."""
        spatial_stems = self.method_a_spatial_azimuth(vocal_stereo)
        qubo_stems = self.method_c_qubo_solver(vocal_stereo)

        hybrid_stems = {}
        for vk in ['voice1_veronika', 'voice2_ruta', 'voice3_rutele']:
            s_sp = spatial_stems[vk]
            s_qb = qubo_stems[vk]
            min_len = min(len(s_sp), len(s_qb))
            fused = 0.60 * s_sp[:min_len] + 0.40 * s_qb[:min_len]
            peak = np.max(np.abs(fused))
            if peak > 0.92:
                fused = fused * (0.92 / peak)
            hybrid_stems[vk] = fused

        return hybrid_stems

    @staticmethod
    def _segment_stem_notes(stem: np.ndarray, sr: int, hop_length: int = 512) -> List[Dict[str, Any]]:
        """Segments raw audio into discrete musical note events using onset tracking."""
        pitches, magnitudes = librosa.piptrack(y=stem, sr=sr, hop_length=hop_length, fmin=130, fmax=850)
        onsets = librosa.onset.onset_detect(y=stem, sr=sr, hop_length=hop_length, backtrack=True)
        onset_times = librosa.frames_to_time(onsets, sr=sr, hop_length=hop_length)

        notes = []
        for i in range(len(onsets)):
            f_start = onsets[i]
            f_end = onsets[i + 1] if i + 1 < len(onsets) else min(f_start + 30, pitches.shape[1])
            if f_end <= f_start:
                continue

            seg_pitches = []
            for t_idx in range(f_start, f_end):
                idx = magnitudes[:, t_idx].argmax()
                p = pitches[idx, t_idx]
                if p > 0:
                    seg_pitches.append(p)

            if seg_pitches:
                med_hz = float(np.median(seg_pitches))
                midi_val = int(round(librosa.hz_to_midi(med_hz)))
                notes.append({
                    'start_time': round(float(onset_times[i]), 2),
                    'midi_pitch': midi_val,
                    'pitch_hz': round(med_hz, 1)
                })
        return notes

    # =========================================================================
    # Tournament Runner & Objective Leaderboard
    # =========================================================================
    def run_tournament(self, vocal_wav_path: str, song_id: str) -> Dict[str, Any]:
        """Runs all 4 methods, evaluates against Sibelius ground truth, and declares the winner."""
        print(f"\n=======================================================", flush=True)
        print(f"VOCAL TRIO TOURNAMENT: {song_id.upper()} ({vocal_wav_path})", flush=True)
        print(f"=======================================================", flush=True)
        vocal_audio = self.load_vocals(vocal_wav_path)
        dur_sec = vocal_audio.shape[1] / self.sr
        print(f"Audio loaded: {dur_sec:.2f}s duration at {self.sr} Hz.", flush=True)

        methods = [
            ("Method A (Spatial Azimuth ILD/IPD)", self.method_a_spatial_azimuth),
            ("Method B (Multi-Pitch Saliency DP)", self.method_b_harmonic_saliency_dp),
            ("Method C (Harmonic QUBO Ising Solver)", self.method_c_qubo_solver),
            ("Method D (Hybrid Spatial + QUBO)", self.method_d_hybrid_spatial_qubo),
        ]

        leaderboard = []

        for name, method_fn in methods:
            t0 = time.time()
            stems = method_fn(vocal_audio)
            elapsed = time.time() - t0

            # Evaluate Harmonic Bleed
            bleed_eval = self.benchmark.evaluate_harmonic_bleed(
                stems['voice1_veronika'],
                stems['voice2_ruta'],
                stems['voice3_rutele'],
                sr=self.sr
            )

            # Evaluate Pitch Accuracy using note event segmentation
            notes_eval_data = {}
            for vk in stems:
                notes_eval_data[vk] = self._segment_stem_notes(stems[vk], self.sr, self.hop_length)

            pitch_eval = self.benchmark.evaluate_pitches(song_id, notes_eval_data, max_gt_notes=50)

            composite_score = 0.50 * pitch_eval['composite_pitch_accuracy_percent'] + 0.50 * bleed_eval['vocal_isolation_percent']

            entry = {
                'method_name': name,
                'elapsed_seconds': round(elapsed, 2),
                'vocal_isolation_percent': bleed_eval['vocal_isolation_percent'],
                'mean_harmonic_bleed_index': bleed_eval['mean_harmonic_bleed_index'],
                'pitch_accuracy_percent': pitch_eval['composite_pitch_accuracy_percent'],
                'composite_score': round(composite_score, 2),
                'stems': stems
            }
            leaderboard.append(entry)
            print(f"\n[{name}] ({elapsed:.2f}s)", flush=True)
            print(f"  Vocal Isolation: {entry['vocal_isolation_percent']}% | Bleed Index: {entry['mean_harmonic_bleed_index']}", flush=True)
            print(f"  Pitch Accuracy:  {entry['pitch_accuracy_percent']}%", flush=True)
            print(f"  Composite Score: {entry['composite_score']}/100", flush=True)

        leaderboard.sort(key=lambda x: x['composite_score'], reverse=True)
        winner = leaderboard[0]
        print(f"\n=======================================================", flush=True)
        print(f"TOURNAMENT WINNER: {winner['method_name']}", flush=True)
        print(f"Winning Composite Score: {winner['composite_score']}/100", flush=True)
        print(f"=======================================================\n", flush=True)

        # Save winning stems to disk
        out_dir = os.path.join(studio_paths.GOLD_AUDIO_DIR, "winning_stems")
        os.makedirs(out_dir, exist_ok=True)
        for vk, audio in winner['stems'].items():
            out_file = os.path.join(out_dir, f"{vk}.wav")
            sf.write(out_file, audio, self.sr)
            print(f"  -> Saved winning stem: {out_file}", flush=True)

        return {
            'song_id': song_id,
            'winner': winner['method_name'],
            'winning_score': winner['composite_score'],
            'leaderboard': [
                {k: v for k, v in item.items() if k != 'stems'}
                for item in leaderboard
            ]
        }


if __name__ == '__main__':
    tournament = VocalTrioTournament()
    test_vocal = os.path.join(studio_paths.GOLD_AUDIO_DIR, "stems_golden_window", "vocals.wav")
    if os.path.exists(test_vocal):
        res = tournament.run_tournament(test_vocal, 'grikiai')
    else:
        print(f"Test vocal not found at: {test_vocal}", flush=True)
