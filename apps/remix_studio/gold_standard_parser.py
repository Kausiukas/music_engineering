"""
gold_standard_parser.py - Production Ground-Truth Extractor for Sibelius Opus Scores
Extracts 3-vocal staves (Veronika, Rūta, Rūtelė), chord progressions, and lyrics from
Sibelius PDF scores (Grikiai, Virusas, Prie Topolio) into structured JSON benchmarks.
"""

import os
import studio_paths
import sys
import json
import re
from typing import Dict, List, Any, Tuple, Optional
import pymupdf

# Sibelius Opus Chord translation map
CHORD_GLYPH_MAP = {
    'A(„ˆˆ2)': 'A(add2)',
    'A¨(„ˆˆ2)': 'Ab(add2)',
    'A‹(„ˆˆ2)': 'Am(add2)',
    'B¨(„ˆˆ2)': 'Bb(add2)',
    'E7': 'E7',
    'F(„ˆˆ2)': 'F(add2)',
    'F7': 'F7',
    'A': 'A',
    'A/G': 'A/G',
    'B': 'B',
    'B&7': 'B+7',
    'B7': 'B7',
    'C': 'C',
    'CŒ„Š7': 'Cmaj7',
    'D¨&7': 'Db+7',
    'D¨Ø7': 'Dbø7',
    'D¨Ø7/A': 'Dbø7/A',
    'DŒ„Š7': 'Dmaj7',
    'E¨Ø7': 'Ebø7',
    'E‹': 'Em',
    'E‹7/D': 'Em7/D',
    'E‹7/G': 'Em7/G',
    'F&': 'F+',
    'F©‹': 'F#m',
    'F©‹7/E': 'F#m7/E',
    'G&/E¨': 'G+/Eb',
    'G/D': 'G/D',
    'A7': 'A7',
    'A¨': 'Ab',
    'A¨‹': 'Abm',
    'A¨‹9': 'Abm9',
    'B¨7': 'Bb7',
    'D7': 'D7',
    'E¨7': 'Eb7',
    'G‹': 'Gm',
}

# Diatonic steps in Treble Clef relative to bottom line E4 (step 0 = E4)
DIATONIC_SCALE = [
    ('C4', 60), ('D4', 62), ('E4', 64), ('F4', 65), ('G4', 67),
    ('A4', 69), ('B4', 71), ('C5', 72), ('D5', 74), ('E5', 76),
    ('F5', 77), ('G5', 79), ('A5', 81), ('B5', 83), ('C6', 84)
]
E4_INDEX = 2  # ('E4', 64) is at index 2


def decode_chord(text: str) -> str:
    """Translates Sibelius Opus chord symbol into standard lead sheet chord name."""
    clean = text.strip()
    if clean in CHORD_GLYPH_MAP:
        return CHORD_GLYPH_MAP[clean]
    # Fallback replacements
    res = clean
    res = res.replace('‹', 'm')
    res = res.replace('¨', 'b')
    res = res.replace('©', '#')
    res = res.replace('&', '+')
    res = res.replace('Ø', 'ø')
    res = res.replace('Œ„Š', 'maj')
    res = res.replace('(„ˆˆ2)', '(add2)')
    return res


def extract_staves_from_page(page: pymupdf.Page) -> List[List[float]]:
    """Detects 5-line staff groupings from vector drawings."""
    drawings = page.get_drawings()
    h_lines = []
    for d in drawings:
        rect = d['rect']
        width = rect.x1 - rect.x0
        height = rect.y1 - rect.y0
        if width > 80 and height < 2.5:
            h_lines.append(rect.y0)

    unique_y = sorted(list(set([round(y, 1) for y in h_lines])))
    staves = []
    i = 0
    while i < len(unique_y):
        group = [unique_y[i]]
        j = i + 1
        while j < len(unique_y) and len(group) < 5:
            diff = unique_y[j] - group[-1]
            if 4.2 <= diff <= 5.8:
                group.append(unique_y[j])
            j += 1
        if len(group) == 5:
            staves.append(group)
            i = j
        else:
            i += 1
    return staves


def extract_page_data(page: pymupdf.Page, page_num: int) -> Dict[str, Any]:
    """Extracts chords, staves, noteheads, and lyrics from a single PDF page."""
    staves = extract_staves_from_page(page)
    # Staves are organized in systems of 3 (Voice 1, Voice 2, Voice 3)
    # Group staves into systems
    systems = []
    for s_idx in range(0, len(staves) - 2, 3):
        systems.append({
            'system_idx': len(systems) + 1,
            'voice1_staff': staves[s_idx],
            'voice2_staff': staves[s_idx + 1],
            'voice3_staff': staves[s_idx + 2],
        })

    blocks = page.get_text('dict')['blocks']
    opus_spans = []
    chord_spans = []
    text_spans = []

    for b in blocks:
        if 'lines' in b:
            for l in b['lines']:
                for s in l['spans']:
                    font_lower = s['font'].lower()
                    if 'opuschords' in font_lower:
                        chord_spans.append(s)
                    elif 'opus' in font_lower:
                        opus_spans.append(s)
                    else:
                        text_spans.append(s)

    # 1. Parse Chords
    page_chords = []
    for cs in chord_spans:
        chord_name = decode_chord(cs['text'])
        if chord_name:
            page_chords.append({
                'chord': chord_name,
                'bbox': cs['bbox'],
                'x': round(cs['bbox'][0], 1),
                'y': round(cs['bbox'][1], 1),
                'page': page_num
            })
    page_chords.sort(key=lambda c: (c['y'], c['x']))

    # 2. Parse Notes and assign to systems & voices
    voice_notes = {'voice1': [], 'voice2': [], 'voice3': []}

    for sys_info in systems:
        v1_staff = sys_info['voice1_staff']
        v2_staff = sys_info['voice2_staff']
        v3_staff = sys_info['voice3_staff']

        v1_bot, v1_sp = v1_staff[-1], (v1_staff[-1] - v1_staff[0]) / 4.0
        v2_bot, v2_sp = v2_staff[-1], (v2_staff[-1] - v2_staff[0]) / 4.0
        v3_bot, v3_sp = v3_staff[-1], (v3_staff[-1] - v3_staff[0]) / 4.0

        for os in opus_spans:
            text = os['text']
            for char in text:
                if char in ['œ', '˙', 'w']:  # quarter/eighth, half, whole noteheads
                    bbox = os['bbox']
                    cy = (bbox[1] + bbox[3]) / 2.0
                    cx = (bbox[0] + bbox[2]) / 2.0
                    dur_type = 'quarter' if char == 'œ' else ('half' if char == '˙' else 'whole')

                    # Check which staff this note belongs to
                    assigned_voice = None
                    bot_line = None
                    sp = None

                    if (v1_staff[0] - 22) <= cy <= (v1_staff[-1] + 25):
                        assigned_voice = 'voice1'
                        bot_line, sp = v1_bot, v1_sp
                    elif (v2_staff[0] - 22) <= cy <= (v2_staff[-1] + 25):
                        assigned_voice = 'voice2'
                        bot_line, sp = v2_bot, v2_sp
                    elif (v3_staff[0] - 22) <= cy <= (v3_staff[-1] + 25):
                        assigned_voice = 'voice3'
                        bot_line, sp = v3_bot, v3_sp

                    if assigned_voice:
                        step_offset = round((bot_line - cy) / (sp / 2.0))
                        idx = E4_INDEX + step_offset
                        if 0 <= idx < len(DIATONIC_SCALE):
                            pname, midi = DIATONIC_SCALE[idx]
                        else:
                            pname, midi = f"step_{step_offset}", 64 + step_offset

                        voice_notes[assigned_voice].append({
                            'char': char,
                            'duration_type': dur_type,
                            'pitch_name': pname,
                            'midi_pitch': midi,
                            'x': round(cx, 1),
                            'y': round(cy, 1),
                            'page': page_num,
                            'system': sys_info['system_idx'],
                            'bbox': bbox,
                            'syllable': None
                        })

    # Sort notes by x within each system
    for vk in voice_notes:
        voice_notes[vk].sort(key=lambda n: (n['system'], n['x']))

    # 3. Align lyric syllables to notes
    # Lyric syllables typically sit right below the staff (cy ~ staff_bot + 12 to 25)
    for sys_info in systems:
        for vk, staff_key in [('voice1', 'voice1_staff'), ('voice2', 'voice2_staff'), ('voice3', 'voice3_staff')]:
            st = sys_info[staff_key]
            y_min = st[-1] + 2
            y_max = st[-1] + 35
            staff_lyrics = [
                ts for ts in text_spans
                if y_min <= (ts['bbox'][1] + ts['bbox'][3]) / 2.0 <= y_max
                and ts['text'].strip() and ts['text'].strip() != '-'
            ]
            staff_notes = [n for n in voice_notes[vk] if n['system'] == sys_info['system_idx']]

            # Match nearest note by x coordinate
            for lyric_span in staff_lyrics:
                lx = (lyric_span['bbox'][0] + lyric_span['bbox'][2]) / 2.0
                closest_note = None
                min_dist = float('inf')
                for n in staff_notes:
                    dist = abs(n['x'] - lx)
                    if dist < min_dist and dist < 25.0:  # within 25 pt horizontal proximity
                        min_dist = dist
                        closest_note = n
                if closest_note and closest_note['syllable'] is None:
                    closest_note['syllable'] = lyric_span['text'].strip()

    return {
        'page': page_num,
        'chords': page_chords,
        'systems_count': len(systems),
        'notes': voice_notes,
        'text_spans': [ts['text'].strip() for ts in text_spans if ts['text'].strip()]
    }


def parse_score_pdf(pdf_path: str) -> Dict[str, Any]:
    """Parses a full Sibelius score PDF into the standardized Gold-Standard JSON benchmark."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Score PDF not found: {pdf_path}")

    doc = pymupdf.open(pdf_path)
    base_name = os.path.basename(pdf_path)

    # Determine song key and tempo metadata
    if 'grikiai' in base_name.lower():
        song_id = 'grikiai'
        title = 'Grikiai'
        tempo = 150
        meter = '4/4'
        nominal_key = 'A minor'
    elif 'virusas' in base_name.lower():
        song_id = 'virusas'
        title = 'Virusas'
        tempo = 140
        meter = '4/4'
        nominal_key = 'E minor'
    elif 'topolio' in base_name.lower():
        song_id = 'prie_topolio'
        title = 'Prie Topolio'
        tempo = 150
        meter = '4/4'
        nominal_key = 'G minor'
    else:
        song_id = os.path.splitext(base_name)[0].lower()
        title = base_name
        tempo = 140
        meter = '4/4'
        nominal_key = 'C major'

    all_chords = []
    all_notes = {'voice1_veronika': [], 'voice2_ruta': [], 'voice3_rutele': []}
    all_lyrics = {'voice1_veronika': [], 'voice2_ruta': [], 'voice3_rutele': []}

    for pno in range(len(doc)):
        pdata = extract_page_data(doc[pno], pno + 1)
        all_chords.extend(pdata['chords'])
        all_notes['voice1_veronika'].extend(pdata['notes']['voice1'])
        all_notes['voice2_ruta'].extend(pdata['notes']['voice2'])
        all_notes['voice3_rutele'].extend(pdata['notes']['voice3'])

    # Assemble lyrics sequences
    for k in all_notes:
        syllables = [n['syllable'] for n in all_notes[k] if n['syllable']]
        all_lyrics[k] = syllables

    total_notes = sum(len(all_notes[k]) for k in all_notes)

    benchmark_data = {
        'song_id': song_id,
        'title': title,
        'source_pdf': pdf_path,
        'pages_count': len(doc),
        'metadata': {
            'tempo_bpm': tempo,
            'meter': meter,
            'nominal_key': nominal_key,
            'total_notes_ground_truth': total_notes,
            'voice1_notes_count': len(all_notes['voice1_veronika']),
            'voice2_notes_count': len(all_notes['voice2_ruta']),
            'voice3_notes_count': len(all_notes['voice3_rutele']),
            'chords_count': len(all_chords)
        },
        'chords': all_chords,
        'vocal_staves': all_notes,
        'lyrics': all_lyrics
    }

    return benchmark_data


def generate_all_gold_standards(
    pdf_dir: str = studio_paths.FIXTURES_DIR,
    output_dir: str = studio_paths.GOLD_JSON_DIR
) -> List[str]:
    """Generates gold-standard JSON files for all score PDFs in the directory."""
    os.makedirs(output_dir, exist_ok=True)
    created_files = []

    files = [
        ('Grikiai - (1).pdf', 'gold_standard_grikiai.json'),
        ('Virusas - Full Score (1).pdf', 'gold_standard_virusas.json'),
        ('Prie Topolio (2) (1) (1).pdf', 'gold_standard_prie_topolio.json')
    ]

    for pdf_name, json_name in files:
        full_pdf = os.path.join(pdf_dir, pdf_name)
        if os.path.exists(full_pdf):
            print(f"Parsing gold standard: {full_pdf}...")
            data = parse_score_pdf(full_pdf)
            out_path = os.path.join(output_dir, json_name)
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  -> Generated: {out_path} ({data['metadata']['total_notes_ground_truth']} notes, {len(data['chords'])} chords)")
            created_files.append(out_path)
        else:
            print(f"Warning: {full_pdf} not found.")

    return created_files


if __name__ == '__main__':
    created = generate_all_gold_standards()
    print(f"\nSuccessfully generated {len(created)} gold standard benchmark files.")
