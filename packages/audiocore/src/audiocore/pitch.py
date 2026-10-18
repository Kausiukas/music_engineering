"""Equal-temperament pitch conversions (A4 = 440 Hz, MIDI 69)."""
import numpy as np

A4_HZ = 440.0
A4_MIDI = 69.0

# Note-name spelling used for individual notes (MIDI/MusicXML export).
NOTE_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Spelling used for song keys and chord roots across both apps.
KEY_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def midi_to_hz(midi):
    """Fractional MIDI note (scalar or array) -> frequency in Hz."""
    return A4_HZ * (2.0 ** ((midi - A4_MIDI) / 12.0))


def hz_to_midi(hz, default=None):
    """Frequency in Hz -> nearest integer MIDI note; ``default`` for missing/non-positive input."""
    if hz is None or hz <= 0:
        return default
    return int(round(A4_MIDI + 12.0 * np.log2(hz / A4_HZ)))


def hz_to_midi_cents(hz):
    """Frequency in Hz -> (nearest MIDI note, cents deviation); ``(None, 0)`` for missing input."""
    if hz is None or hz <= 0:
        return None, 0
    midi = A4_MIDI + 12.0 * np.log2(hz / A4_HZ)
    nearest = int(round(midi))
    return nearest, int(round((midi - nearest) * 100))


def midi_to_name(note):
    """Integer MIDI note -> scientific pitch name, e.g. 60 -> 'C4'."""
    return f"{NOTE_NAMES_SHARP[note % 12]}{(note // 12) - 1}"
