"""Locate the workspace ``data/`` directory shared by all audio-lab apps.

Resolution order:
1. ``AUDIO_LAB_DATA`` environment variable.
2. ``<workspace>/data`` found by walking up from this file (editable install inside the repo).

Returns ``None`` when neither applies (e.g. a production host with its own layout);
apps then fall back to their own legacy/env-var configuration.
"""
import os
from pathlib import Path


def workspace_data_dir():
    env = os.environ.get("AUDIO_LAB_DATA")
    if env:
        return Path(env)
    for parent in Path(__file__).resolve().parents:
        if (parent / "packages").is_dir() and (parent / "data" / "README.md").is_file():
            return parent / "data"
    return None
