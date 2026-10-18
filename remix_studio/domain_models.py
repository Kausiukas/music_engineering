"""
domain_models.py - Formal Domain Models for Antigravity Remix Studio DAW
Adopts Matt Pocock's domain-modeling engineering skill:
Encodes explicit types, entities, musical units, and acoustic invariants.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import numpy as np


@dataclass
class MusicalNote:
    """
    Represents an atomic musical note event linked to score coordinates and phonetics.
    All temporal values are in SI seconds and musical beats.
    """
    pitch_name: str
    midi_pitch: float
    duration_type: str = "quarter"
    duration_sec: float = 0.534
    onset_sec: float = 0.0
    syllable: Optional[str] = None
    measure: int = 1
    beat: float = 1.0
    staff_id: str = "voice1_veronika"
    x: float = 0.0
    y: float = 0.0
    page: int = 1
    system: int = 1

    @property
    def frequency_hz(self) -> float:
        """Computes fundamental frequency F0 in Hertz (A4 = 440 Hz)."""
        return 440.0 * (2.0 ** ((self.midi_pitch - 69.0) / 12.0))

    def clean_syllable(self) -> str:
        """Returns sanitized phonetic text for speech synthesis."""
        text = str(self.syllable).strip() if self.syllable else ""
        if not text or text in ['None', 'null', 'œ', '-']:
            return "la"
        return text


@dataclass
class ChordVoicing:
    """
    Represents a harmonic chord structure anchored to an exact measure and beat.
    """
    chord_name: str
    measure: int
    beat: float = 1.0
    root_midi: int = 48  # C3 = 48
    pitches: List[int] = field(default_factory=lambda: [48, 52, 55, 60])
    onset_sec: float = 0.0


@dataclass
class VocalTrack:
    """
    Represents an isolated, unflattened vocal line (e.g. Lead, Harmony, Alto).
    """
    voice_id: str
    name: str
    clef: str
    color_hex: str
    panning: float  # -1.0 (left) to +1.0 (right)
    target_gain_db: float = 0.0
    notes: List[MusicalNote] = field(default_factory=list)

    @property
    def total_notes(self) -> int:
        return len(self.notes)


@dataclass
class RhythmTrack:
    """
    Represents an isolated, unflattened acoustic instrument line.
    """
    instrument_id: str
    name: str
    icon: str
    panning: float
    pattern_style: str  # e.g. "freddie_green_comping", "walking_bass", "brush_shuffle"
    target_gain_db: float = -2.0


@dataclass
class SongManifest:
    """
    Complete domain specification for an ingested and recreated song.
    """
    song_id: str
    title: str
    source_pdf_path: str
    source_audio_path: Optional[str]
    tempo_bpm: float = 112.3
    meter: str = "4/4"
    nominal_key: str = "A minor"
    duration_sec: float = 30.0
    vocal_tracks: Dict[str, VocalTrack] = field(default_factory=dict)
    rhythm_tracks: Dict[str, RhythmTrack] = field(default_factory=dict)
    chords: List[ChordVoicing] = field(default_factory=list)
    master_peak_dbfs: float = -5.64

    @property
    def sec_per_beat(self) -> float:
        return 60.0 / self.tempo_bpm

    @property
    def beats_per_measure(self) -> float:
        try:
            return float(self.meter.split('/')[0])
        except (ValueError, IndexError):
            return 4.0

    @property
    def sec_per_measure(self) -> float:
        return self.sec_per_beat * self.beats_per_measure
