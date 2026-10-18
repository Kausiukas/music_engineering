@echo off
title REMIX DNA // Audio-to-MIDI & Multi-Genre Studio
cd /d "d:\radio\remix_studio"
echo ===============================================================================
echo   REMIX DNA // AUDIO-TO-MIDI & JUNGLE/TECHNO/HOUSE REMIX WORKSTATION
echo ===============================================================================
echo   * Host: http://localhost:8790/
echo   * Test Track: Kolorado vabalai - Vytautas Kernagis (174 BPM Ragga Jungle)
echo   * Stems: Vocals, Guitar/Harmony, Bassline, Drums
echo   * Voice Lab: Multi-Engine Evaluation Suite (Engines A, B, C, D)
echo ===============================================================================
echo.
.venv\Scripts\python.exe server.py
pause
