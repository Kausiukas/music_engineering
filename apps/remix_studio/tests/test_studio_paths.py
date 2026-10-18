"""Hermetic: filesystem layout and the /audio/<rel> confinement used by the studio server."""
import os

import studio_paths


def test_data_lives_outside_the_code_tree():
    assert os.path.commonpath([studio_paths.DATA_DIR, studio_paths.APP_DIR]) != studio_paths.APP_DIR
    assert studio_paths.DB_PATH.startswith(studio_paths.DATA_DIR)
    assert studio_paths.GOLD_JSON_DIR.startswith(studio_paths.APP_DIR)  # tracked ground truth


def test_resolve_data_path_maps_api_paths_into_data_dir():
    target = studio_paths.resolve_data_path("audio/stems/vocals.wav")
    assert target == os.path.realpath(os.path.join(studio_paths.DATA_DIR, "audio", "stems", "vocals.wav"))


def test_resolve_data_path_refuses_escapes():
    for rel in ["../../apps/remix_studio/server.py", "..\\..\\.git\\config", "audio/../../radio/state/.ip_salt",
                os.path.abspath(__file__), "", "."]:
        assert studio_paths.resolve_data_path(rel) is None, rel
