"""
test_gold_standard_verification.py - Automated Unit & Integration Tests
Validates the entire Refactored Gold-Standard 3-Voice Architecture:
- Ground-truth JSON benchmark integrity for Grikiai, Virusas, and Prie Topolio
- Zero-clipping True Peak standard (<= -0.7 dBFS / 0.92) across all synthetic stems and master mixes
- 3-Vocal Grand Lead Score SVG generation with interactive note attributes
- Full objective benchmark evaluation
"""

import unittest
import os
import sys
import json
import numpy as np
import soundfile as sf

import studio_paths
from gold_standard_benchmark import GoldStandardBenchmark
from sheet_music_exporter import generate_3vocal_svg_score


class TestGoldStandardVerification(unittest.TestCase):

    def setUp(self):
        self.benchmark = GoldStandardBenchmark()
        self.gold_dir = studio_paths.GOLD_JSON_DIR
        self.recreations_dir = studio_paths.RECREATIONS_DIR

    def test_gold_standards_json_exist(self):
        """Verifies that gold_standard JSON files exist and contain extracted Sibelius scores."""
        songs = [
            ("gold_standard_grikiai.json", 1239, 87),
            ("gold_standard_virusas.json", 1421, 106),
            ("gold_standard_prie_topolio.json", 1494, 116),
        ]
        for filename, expected_notes, expected_chords in songs:
            path = os.path.join(self.gold_dir, filename)
            self.assertTrue(os.path.exists(path), f"File {path} must exist")
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertEqual(data['metadata']['total_notes_ground_truth'], expected_notes)
            self.assertEqual(len(data['chords']), expected_chords)
            self.assertIn('voice1_veronika', data['vocal_staves'])
            self.assertIn('voice2_ruta', data['vocal_staves'])
            self.assertIn('voice3_rutele', data['vocal_staves'])

    def test_zero_clipping_peak_standard(self):
        """Verifies zero-clipping invariant: True Peak <= -0.7 dBFS (0.92 linear) across all recreations."""
        for song_id in ['grikiai', 'virusas', 'prie_topolio']:
            song_dir = os.path.join(self.recreations_dir, song_id)
            self.assertTrue(os.path.exists(song_dir), f"Directory {song_dir} must exist")
            files_to_check = [
                "synth_vocals_voice1.wav",
                "synth_vocals_voice2.wav",
                "synth_vocals_voice3.wav",
                "synth_instruments.wav",
                "master_synthetic_recreation_+0.wav"
            ]
            for fname in files_to_check:
                fpath = os.path.join(song_dir, fname)
                self.assertTrue(os.path.exists(fpath), f"Audio file {fpath} must exist")
                audio, sr = sf.read(fpath)
                peak_val = np.max(np.abs(audio))
                peak_db = 20.0 * np.log10(max(1e-6, peak_val))
                self.assertLessEqual(
                    peak_val, 0.925,
                    f"Audio {fpath} clipped! Peak: {peak_val:.4f} ({peak_db:.2f} dBFS > -0.7 dBFS)"
                )

    def test_score_3vocal_svg_generation(self):
        """Verifies that 3-vocal SVG score renders with all 3 staves and interactive attributes."""
        for song_id in ['grikiai', 'virusas', 'prie_topolio']:
            svg = generate_3vocal_svg_score(song_id=song_id)
            self.assertIn('<svg', svg)
            self.assertIn('Veronika (Lead)', svg)
            self.assertIn('Rūta (Harmony)', svg)
            self.assertIn('Rūtelė (Alto)', svg)
            self.assertIn('class="interactive-note"', svg)
            self.assertIn('data-pitch=', svg)
            self.assertIn('data-voice=', svg)

    def test_full_gold_standard_benchmark(self):
        """Verifies that the benchmark engine successfully evaluates against ground truth."""
        song_id = 'grikiai'
        song_dir = os.path.join(self.recreations_dir, song_id)
        v1, _ = sf.read(os.path.join(song_dir, "synth_vocals_voice1.wav"))
        v2, _ = sf.read(os.path.join(song_dir, "synth_vocals_voice2.wav"))
        v3, _ = sf.read(os.path.join(song_dir, "synth_vocals_voice3.wav"))

        bleed_res = self.benchmark.evaluate_harmonic_bleed(v1[:, 0], v2[:, 0], v3[:, 0])
        self.assertIn('vocal_isolation_percent', bleed_res)
        self.assertGreater(bleed_res['vocal_isolation_percent'], 20.0)


if __name__ == '__main__':
    unittest.main()
