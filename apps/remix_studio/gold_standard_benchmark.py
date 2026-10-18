"""
gold_standard_benchmark.py - Objective Ground-Truth Verification Benchmark Suite
Evaluates separated stems, STT lyric transcriptions, sheet music notes, and synthetic
recreations against the Sibelius Opus Ground-Truth Gold Standards (Grikiai, Virusas, Prie Topolio).
"""

import os
import studio_paths
import sys
import json
import math
from typing import Dict, List, Any, Tuple, Optional
import numpy as np


class GoldStandardBenchmark:
    """Benchmark engine comparing transcribed and synthesized music against Sibelius Gold Standards."""

    def __init__(self, gold_standards_dir: str = studio_paths.GOLD_JSON_DIR):
        self.gold_standards_dir = gold_standards_dir
        self.cache: Dict[str, Dict[str, Any]] = {}

    def load_gold_standard(self, song_id: str) -> Dict[str, Any]:
        """Loads the parsed ground-truth JSON for a given song."""
        clean_id = song_id.lower().replace('-', '_').replace(' ', '_')
        if clean_id in self.cache:
            return self.cache[clean_id]

        filename = f"gold_standard_{clean_id}.json"
        path = os.path.join(self.gold_standards_dir, filename)
        if not os.path.exists(path):
            # Try alternate matching
            candidates = [f for f in os.listdir(self.gold_standards_dir) if clean_id in f.lower()]
            if candidates:
                path = os.path.join(self.gold_standards_dir, candidates[0])
            else:
                raise FileNotFoundError(f"Gold standard file not found for song: {song_id} at {path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.cache[clean_id] = data
        return data

    @staticmethod
    def levenshtein_distance(seq1: List[str], seq2: List[str]) -> int:
        """Computes edit distance between two token sequences."""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1].lower() == seq2[j - 1].lower():
                    cost = 0
                else:
                    cost = 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,      # deletion
                    dp[i][j - 1] + 1,      # insertion
                    dp[i - 1][j - 1] + cost  # substitution
                )
        return dp[m][n]

    def evaluate_lyrics(self, song_id: str, hypothesis_lyrics: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Evaluates Word Error Rate (WER) and Syllable Error Rate (SER)
        for each voice against ground truth.
        """
        gt = self.load_gold_standard(song_id)
        gt_lyrics = gt.get('lyrics', {})

        results = {}
        for voice_key in ['voice1_veronika', 'voice2_ruta', 'voice3_rutele']:
            gt_tokens = gt_lyrics.get(voice_key, [])
            hyp_tokens = hypothesis_lyrics.get(voice_key, hypothesis_lyrics.get(voice_key.split('_')[0], []))

            if not gt_tokens:
                results[voice_key] = {'wer': 0.0, 'ser': 0.0, 'gt_count': 0, 'hyp_count': len(hyp_tokens)}
                continue

            dist = self.levenshtein_distance(gt_tokens, hyp_tokens)
            error_rate = min(1.0, dist / max(1, len(gt_tokens)))
            results[voice_key] = {
                'syllable_error_rate': round(error_rate * 100.0, 2),
                'ground_truth_tokens': len(gt_tokens),
                'hypothesis_tokens': len(hyp_tokens),
                'edit_distance': dist,
                'match_rate': round(max(0.0, (1.0 - error_rate)) * 100.0, 2)
            }

        mean_match = np.mean([results[vk]['match_rate'] for vk in results if results[vk]['ground_truth_tokens'] > 0])
        return {
            'voice_breakdown': results,
            'composite_lyric_match_percent': round(float(mean_match), 2)
        }

    def evaluate_pitches(
        self,
        song_id: str,
        hypothesis_notes: Dict[str, List[Dict[str, Any]]],
        tolerance_semitones: float = 1.0,
        max_gt_notes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Evaluates transcribed or synthesized note pitches against Sibelius ground truth.
        hypothesis_notes: {'voice1_veronika': [{'midi_pitch': 67, ...}, ...]}
        """
        gt = self.load_gold_standard(song_id)
        gt_staves = gt.get('vocal_staves', {})

        results = {}
        for vk in ['voice1_veronika', 'voice2_ruta', 'voice3_rutele']:
            gt_notes = gt_staves.get(vk, [])
            if max_gt_notes is not None and max_gt_notes > 0:
                gt_notes = gt_notes[:max_gt_notes]
            hyp_notes = hypothesis_notes.get(vk, hypothesis_notes.get(vk.split('_')[0], []))

            if not gt_notes or not hyp_notes:
                results[vk] = {'pitch_accuracy_percent': 0.0, 'matches': 0, 'total': len(gt_notes)}
                continue

            # Compare pitch sequences
            n_eval = min(len(gt_notes), len(hyp_notes))
            matches = 0
            deltas = []
            for idx in range(n_eval):
                gt_pitch = gt_notes[idx]['midi_pitch']
                hyp_pitch = hyp_notes[idx].get('midi_pitch', hyp_notes[idx].get('pitch', 0))
                delta = abs(gt_pitch - hyp_pitch)
                deltas.append(delta)
                if delta <= tolerance_semitones:
                    matches += 1

            acc = (matches / n_eval) * 100.0 if n_eval > 0 else 0.0
            mean_delta = float(np.mean(deltas)) if deltas else 0.0
            results[vk] = {
                'pitch_accuracy_percent': round(acc, 2),
                'mean_semitone_delta': round(mean_delta, 2),
                'evaluated_notes': n_eval,
                'ground_truth_total': len(gt_notes)
            }

        mean_acc = np.mean([results[vk]['pitch_accuracy_percent'] for vk in results if results[vk]['ground_truth_total'] > 0])
        return {
            'voice_pitch_breakdown': results,
            'composite_pitch_accuracy_percent': round(float(mean_acc), 2)
        }

    def evaluate_harmonic_bleed(
        self,
        stem_v1: np.ndarray,
        stem_v2: np.ndarray,
        stem_v3: np.ndarray,
        sr: int = 44100
    ) -> Dict[str, Any]:
        """
        Measures inter-voice harmonic bleed between isolated vocal stems using cross-spectral correlation.
        """
        def spectral_energy(audio: np.ndarray) -> np.ndarray:
            if len(audio) == 0:
                return np.zeros(1024)
            fft_mag = np.abs(np.fft.rfft(audio[:min(len(audio), sr * 10)]))
            norm = np.linalg.norm(fft_mag)
            return fft_mag / (norm + 1e-12)

        s1 = spectral_energy(stem_v1)
        s2 = spectral_energy(stem_v2)
        s3 = spectral_energy(stem_v3)

        min_len = min(len(s1), len(s2), len(s3))
        s1, s2, s3 = s1[:min_len], s2[:min_len], s3[:min_len]

        bleed_12 = float(np.dot(s1, s2))
        bleed_13 = float(np.dot(s1, s3))
        bleed_23 = float(np.dot(s2, s3))

        mean_bleed = (bleed_12 + bleed_13 + bleed_23) / 3.0
        isolation_score = max(0.0, 1.0 - mean_bleed) * 100.0

        return {
            'bleed_voice1_voice2': round(bleed_12, 4),
            'bleed_voice1_voice3': round(bleed_13, 4),
            'bleed_voice2_voice3': round(bleed_23, 4),
            'mean_harmonic_bleed_index': round(mean_bleed, 4),
            'vocal_isolation_percent': round(isolation_score, 2)
        }

    def evaluate_chord_progression(self, song_id: str, hypothesis_chords: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluates detected chord symbols against Sibelius ground-truth chords."""
        gt = self.load_gold_standard(song_id)
        gt_chords = [c['chord'] for c in gt.get('chords', [])]
        hyp_chords = [c.get('chord', '') for c in hypothesis_chords]

        if not gt_chords:
            return {'chord_accuracy_percent': 100.0, 'gt_count': 0, 'hyp_count': len(hyp_chords)}

        dist = self.levenshtein_distance(gt_chords, hyp_chords)
        err = min(1.0, dist / max(1, len(gt_chords)))
        acc = max(0.0, 1.0 - err) * 100.0

        return {
            'chord_accuracy_percent': round(acc, 2),
            'ground_truth_count': len(gt_chords),
            'hypothesis_count': len(hyp_chords),
            'edit_distance': dist
        }

    def generate_full_scorecard(
        self,
        song_id: str,
        hypothesis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generates comprehensive objective scorecard across all 4 pillars:
        1. Pitch Accuracy vs. Sibelius score
        2. Lyric & Scat Accuracy vs. Sibelius lyrics
        3. Harmonic Bleed Index across vocal stems
        4. Chord Progression Match
        """
        pitch_res = self.evaluate_pitches(song_id, hypothesis_data.get('notes', {}))
        lyric_res = self.evaluate_lyrics(song_id, hypothesis_data.get('lyrics', {}))
        chord_res = self.evaluate_chord_progression(song_id, hypothesis_data.get('chords', []))

        stems = hypothesis_data.get('stems', {})
        bleed_res = self.evaluate_harmonic_bleed(
            stems.get('voice1', np.array([])),
            stems.get('voice2', np.array([])),
            stems.get('voice3', np.array([])),
            sr=hypothesis_data.get('sample_rate', 44100)
        )

        composite_score = (
            0.35 * pitch_res['composite_pitch_accuracy_percent'] +
            0.30 * lyric_res['composite_lyric_match_percent'] +
            0.20 * bleed_res['vocal_isolation_percent'] +
            0.15 * chord_res['chord_accuracy_percent']
        )

        return {
            'song_id': song_id,
            'composite_accuracy_score': round(composite_score, 2),
            'verdict': 'PASS' if composite_score >= 80.0 else 'NEEDS_OPTIMIZATION',
            'pitch_evaluation': pitch_res,
            'lyric_evaluation': lyric_res,
            'bleed_evaluation': bleed_res,
            'chord_evaluation': chord_res
        }


if __name__ == '__main__':
    bench = GoldStandardBenchmark()
    for s in ['grikiai', 'virusas', 'prie_topolio']:
        data = bench.load_gold_standard(s)
        print(f"Loaded Gold Standard: {data['title']} ({data['metadata']['total_notes_ground_truth']} notes, {len(data['chords'])} chords)")
