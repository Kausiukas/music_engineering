@echo off
title REMIX DNA // Audio-to-MIDI & Multi-Genre Studio
cd /d "%~dp0"
echo ===============================================================================
echo   REMIX DNA // AUDIO-TO-MIDI & JUNGLE/TECHNO/HOUSE REMIX WORKSTATION
echo ===============================================================================
echo   * Host: http://localhost:8790/
echo   * Test Track: Kolorado vabalai - Vytautas Kernagis (174 BPM Ragga Jungle)
echo   * Stems: Vocals, Guitar/Harmony, Bassline, Drums
echo   * Voice Lab: Multi-Engine Evaluation Suite (Engines A, B, C, D)
echo ===============================================================================
echo.
uv run python server.py
pause
