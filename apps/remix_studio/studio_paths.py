"""Single source of truth for Remix Studio filesystem locations.

Code (and the tracked gold-standard JSON ground truth) lives in APP_DIR. Everything ingested or
generated lives under DATA_DIR = ``<workspace>/data/remix`` (override with ``REMIX_DATA_DIR``),
keeping the same relative layout the HTTP API exposes under ``/audio/<rel>``.
"""
import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "static")
GOLD_JSON_DIR = os.path.join(APP_DIR, "gold_standards")


def _workspace_data_dir():
    try:
        from audiocore.paths import workspace_data_dir
    except ImportError:
        return None
    return workspace_data_dir()


_ws = _workspace_data_dir()
DATA_DIR = os.environ.get("REMIX_DATA_DIR") or (str(_ws / "remix") if _ws else APP_DIR)
SHARED_DIR = os.environ.get("AUDIO_LAB_SHARED_DIR") or (str(_ws / "shared") if _ws else None)

AUDIO_DIR = os.path.join(DATA_DIR, "audio")
STEMS_DIR = os.path.join(AUDIO_DIR, "stems")
MIDI_DIR = os.path.join(DATA_DIR, "midi")
SCORES_DIR = os.path.join(DATA_DIR, "scores")
REMIXES_DIR = os.path.join(DATA_DIR, "remixes")
RECREATIONS_DIR = os.path.join(DATA_DIR, "recreations")
VOCAL_TESTS_DIR = os.path.join(DATA_DIR, "vocal_tests")
GOLD_AUDIO_DIR = os.path.join(DATA_DIR, "gold_standards")
FIXTURES_DIR = os.path.join(DATA_DIR, "fixtures")
DOWNLOADS_DIR = os.path.join(DATA_DIR, "downloads")
DB_PATH = os.environ.get("REMIX_DB_PATH") or os.path.join(DATA_DIR, "db", "remix_studio.db")

# Shared with the radio app (data/shared). None outside the workspace.
SFX_DIR = os.path.join(SHARED_DIR, "sfx") if SHARED_DIR else None
CLASSIC_SAMPLES_DIR = os.path.join(SHARED_DIR, "classic_samples") if SHARED_DIR else None


def resolve_data_path(rel_path):
    """Map an API-relative path (``audio/stems/x.wav``) into DATA_DIR, refusing anything that escapes it."""
    root = os.path.realpath(DATA_DIR)
    # Backslashes are separators on every OS, so `..\..\x` can't slip past the check on Linux.
    target = os.path.realpath(os.path.join(root, rel_path.replace("\\", "/")))
    if os.path.commonpath([root, target]) != root or target == root:
        return None
    return target
