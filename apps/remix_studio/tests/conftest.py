import pytest

# These suites assert on pipeline outputs under data/remix (recreations, DB, manifest),
# not on code in isolation. Select the hermetic tier with: pytest -m "not artifact".
ARTIFACT_MODULES = {"test_audio_perceptual_integrity", "test_gold_standard_verification", "test_studio_core"}
SLOW_TESTS = {"test_vocal_lyric_intelligibility"}


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.module.__name__.rsplit(".", 1)[-1] in ARTIFACT_MODULES:
            item.add_marker(pytest.mark.artifact)
        if item.originalname in SLOW_TESTS or "whisper" in item.name.lower():
            item.add_marker(pytest.mark.slow)
