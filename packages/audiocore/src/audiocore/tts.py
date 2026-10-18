"""Microsoft Edge neural TTS (network service). Requires the ``audiocore[tts]`` extra."""


async def save_speech(text, voice, out_path, rate="+0%", pitch="+0Hz"):
    """Synthesize ``text`` with ``voice`` and write the service's MP3 to ``out_path``."""
    import edge_tts

    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(out_path)
