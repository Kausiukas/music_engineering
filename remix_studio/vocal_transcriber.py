"""
Vocal Lyric Transcription Engine
Transcribes lyrics and extracts syllable/word-level timestamps using Whisper.
Aligns text phonemes with vocal melody notes for sheet music and neural singing synthesis.
"""

import os
import sys
import json
import re
import whisper

def split_into_syllables_lt(word):
    """
    Splits Lithuanian words into approximate singing syllables based on vowels and diphthongs.
    Vowels: a, e, i, o, u, y, ė, į, ų, ū, ą
    Diphthongs: ai, au, ei, ie, uo, ui
    """
    clean_w = re.sub(r'[^\w\s]', '', word).lower()
    if len(clean_w) <= 3:
        return [word]
        
    vowel_pattern = r'(ai|au|ei|ie|uo|ui|[aeiouyėįųūą])'
    parts = re.split(vowel_pattern, clean_w)
    # Reassemble consonant-vowel syllable clusters
    syllables = []
    curr = ""
    for p in parts:
        if not p:
            continue
        curr += p
        if re.search(vowel_pattern, p):
            syllables.append(curr)
            curr = ""
    if curr:
        if syllables:
            syllables[-1] += curr
        else:
            syllables.append(curr)
            
    # Retain trailing punctuation on the final syllable
    trailing_punct = re.findall(r'[^\w\s]+$', word)
    if trailing_punct and syllables:
        syllables[-1] += trailing_punct[0]
        
    return syllables if syllables else [word]

def transcribe_vocals(audio_path, out_notes_json=None, out_lyrics_json=None, language="lt", model_size="base"):
    """
    Transcribes vocal audio using Whisper.
    Supports flexible signatures:
    - transcribe_vocals(audio_path, language="lt", model_size="base")
    - transcribe_vocals(audio_path, out_notes_json, out_lyrics_json)
    """
    # Handle parameter overloading
    if isinstance(out_notes_json, str) and not out_notes_json.endswith(".json") and len(out_notes_json) <= 3:
        language = out_notes_json
        out_notes_json = None
        
    print(f"Loading Whisper model '{model_size}'...")
    model = whisper.load_model(model_size)
    
    print(f"Transcribing '{audio_path}' (target language: {language})...")
    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        verbose=False
    )
    
    transcription = {
        'language': result.get('language', language),
        'text': result.get('text', '').strip(),
        'segments': [],
        'words': []
    }
    
    for seg in result.get('segments', []):
        transcription['segments'].append({
            'start': float(round(seg['start'], 2)),
            'end': float(round(seg['end'], 2)),
            'text': seg['text'].strip()
        })
        for w in seg.get('words', []):
            word_str = w['word'].strip()
            word_start = float(round(w['start'], 2))
            word_end = float(round(w['end'], 2))
            sylls = split_into_syllables_lt(word_str)
            
            # Divide word timestamp evenly across syllables
            syll_dur = (word_end - word_start) / max(1, len(sylls))
            syllable_objs = []
            for s_idx, s_text in enumerate(sylls):
                syllable_objs.append({
                    'syllable': s_text,
                    'start': float(round(word_start + s_idx * syll_dur, 2)),
                    'end': float(round(word_start + (s_idx + 1) * syll_dur, 2))
                })
                
            transcription['words'].append({
                'word': word_str,
                'start': word_start,
                'end': word_end,
                'probability': float(round(w.get('probability', 1.0), 3)),
                'syllables': syllable_objs
            })
            
    # Save to lyrics JSON if target provided
    if out_lyrics_json:
        os.makedirs(os.path.dirname(os.path.abspath(out_lyrics_json)), exist_ok=True)
        with open(out_lyrics_json, 'w', encoding='utf-8') as f:
            json.dump(transcription, f, ensure_ascii=False, indent=2)
        print(f"Lyrics transcription saved to: {out_lyrics_json}")
        
    # Extract melodic vocal notes if notes path provided
    if out_notes_json:
        try:
            from audio_to_midi import extract_melody_notes
            notes = extract_melody_notes(audio_path)
            os.makedirs(os.path.dirname(os.path.abspath(out_notes_json)), exist_ok=True)
            with open(out_notes_json, 'w', encoding='utf-8') as f:
                json.dump(notes, f, ensure_ascii=False, indent=2)
            print(f"Vocal melody notes saved to: {out_notes_json} ({len(notes)} notes)")
        except Exception as e:
            print(f"Warning: could not extract notes to {out_notes_json}: {e}")
            
    return transcription

if __name__ == "__main__":
    if len(sys.argv) > 1:
        audio = sys.argv[1]
        out_json = sys.argv[2] if len(sys.argv) > 2 else audio.replace('.wav', '_lyrics.json')
        res = transcribe_vocals(audio, out_lyrics_json=out_json)
        print(f"Transcription saved to {out_json}")
        print("Lyrics snippet:\n", res['text'][:200])
