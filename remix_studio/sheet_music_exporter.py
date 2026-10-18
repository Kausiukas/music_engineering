"""
Sheet Music & Score Exporter
Converts transcribed MIDI notes and lyric alignments into:
- Standard MusicXML (.musicxml) for MuseScore, Sibelius, Dorico, Finale
- Browser-renderable SVG Score and HTML notation
- Supports Grand Staff dual-clef rendering, polyphonic chord stacking, and syllable-by-syllable lyric alignment
- Supports instant pitch transposition (+/- 12 semitones)
"""

import os
import sys
import json
try:
    import music21 as m21
except ImportError:
    m21 = None

DIATONIC_STEP = [0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6]
IS_SHARP = [False, True, False, True, False, False, True, False, True, False, True, False]
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def generate_musicxml(notes, lyrics_words=None, output_path="score.musicxml", title="Žiemą vasarą", composer="Vytautas Kernagis", bpm=120, transpose_semitones=0):
    """
    Creates a formal MusicXML document with melody notes, chords, rests, and lyrics.
    """
    score = m21.stream.Score()
    score.metadata = m21.metadata.Metadata()
    score.metadata.title = title
    score.metadata.composer = composer
    
    part = m21.stream.Part()
    part.partName = "Lead Score"
    
    # Clef, Time Signature, Tempo
    part.append(m21.clef.TrebleClef())
    part.append(m21.meter.TimeSignature('4/4'))
    part.append(m21.tempo.MetronomeMark(number=bpm))
    
    key_root = 'C'
    part.append(m21.key.Key(key_root, 'major'))
    
    # Flatten syllables for chronological note mapping
    flat_syllables = []
    if lyrics_words:
        for w in lyrics_words:
            if 'syllables' in w and w['syllables']:
                for s in w['syllables']:
                    flat_syllables.append(s)
            else:
                flat_syllables.append({'syllable': w['word'], 'start': w['start'], 'end': w['end']})
                
    flat_syllables.sort(key=lambda x: x['start'])
    syll_idx = 0
    num_sylls = len(flat_syllables)
    
    # Group simultaneous notes into chords/columns
    sorted_notes = sorted(notes, key=lambda n: (n.get('start', 0.0), n.get('pitch', 0)))
    columns = []
    curr_col = []
    curr_t = -1.0
    for n in sorted_notes:
        st = float(n.get('start', 0.0))
        if curr_t < 0 or abs(st - curr_t) <= 0.045:
            curr_col.append(n)
            if curr_t < 0:
                curr_t = st
        else:
            columns.append(curr_col)
            curr_col = [n]
            curr_t = st
    if curr_col:
        columns.append(curr_col)
        
    last_end = 0.0
    seconds_per_quarter = 60.0 / bpm
    
    for col in columns:
        start_sec = col[0]['start']
        end_sec = max(n['end'] for n in col)
        duration_sec = end_sec - start_sec
        
        def snap_duration(val):
            valid = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
            return min(valid, key=lambda x: abs(x - val))
            
        rest_sec = start_sec - last_end
        if rest_sec > 0.15:
            raw_rest = rest_sec / seconds_per_quarter
            if raw_rest >= 0.2:
                r = m21.note.Rest()
                r.quarterLength = snap_duration(raw_rest)
                part.append(r)
                
        raw_dur = max(0.2, duration_sec / seconds_per_quarter)
        pitches = [n['pitch'] + transpose_semitones for n in col]
        
        if len(pitches) > 1:
            el = m21.chord.Chord(pitches)
        else:
            el = m21.note.Note(pitches[0])
            
        el.quarterLength = snap_duration(raw_dur)
        
        # Match syllable
        if syll_idx < num_sylls:
            s_obj = flat_syllables[syll_idx]
            if abs(s_obj['start'] - start_sec) < 0.5:
                el.lyric = s_obj['syllable']
                syll_idx += 1
                
        part.append(el)
        last_end = end_sec
        
    score.append(part)
    score.write('musicxml', fp=output_path)
    return output_path

def generate_svg_score(notes, lyrics_words=None, title="Žiemą vasarą", bpm=152, transpose_semitones=0, layer="vocals"):
    """
    Generates a diatonic vector SVG lead sheet for in-browser rendering:
    - Vertical chord note head stacking for multi-string guitar/piano
    - Syllable-by-syllable lyric alignment directly under note heads
    - Grand Staff dual-clef rendering with interactive note audition
    """
    svg_width = 960
    
    DIATONIC_STEP = [0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6]
    IS_SHARP = [False, True, False, True, False, False, True, False, True, False, True, False]
    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    base_keys = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
    current_key = base_keys[(5 + transpose_semitones) % 12]
    
    # Dynamic Manifest Layer Discovery
    manifest_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", "song_manifest.json")
    layer_config = None
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
                title = manifest_data.get('title', title)
                for l in manifest_data.get('layers', []):
                    if l['id'] == layer:
                        layer_config = l
                        break
        except Exception:
            pass

    notes_to_render = []
    layer_color = "#00f0ff"
    is_bass_clef = (layer == "bass")
    is_grand_staff = (layer in ["piano", "acoustic_guitar"])

    if layer_config:
        active_layer_label = f"{layer_config.get('icon', '🎵')} {layer_config['name'].upper()}"
        layer_color = layer_config.get('color', '#00f0ff')
        clef_setting = layer_config.get('clef', 'treble')
        is_bass_clef = (clef_setting == "bass")
        is_grand_staff = (clef_setting == "grand_staff")
        
        # Load from disk layer file if present
        target_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", f"{layer}_notes.json")
        if not os.path.exists(target_file) and layer == "vocals":
            target_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", "vocal_notes.json")
            
        if os.path.exists(target_file):
            try:
                with open(target_file, 'r', encoding='utf-8') as f:
                    notes_to_render = json.load(f)
            except Exception:
                pass
                
    if not notes_to_render:
        notes_to_render = notes

    # Group notes into time-aligned columns/chord stacks
    sorted_notes = sorted(notes_to_render, key=lambda n: (float(n.get('start', 0.0)), int(n.get('pitch', 0))))
    columns = []
    curr_col = []
    curr_t = -1.0
    for n in sorted_notes:
        st = float(n.get('start', 0.0))
        if curr_t < 0 or abs(st - curr_t) <= 0.045:
            curr_col.append(n)
            if curr_t < 0:
                curr_t = st
        else:
            columns.append(curr_col)
            curr_col = [n]
            curr_t = st
    if curr_col:
        columns.append(curr_col)

    # Prepare flattened syllables for vocal mapping
    flat_syllables = []
    if lyrics_words:
        for w in lyrics_words:
            if 'syllables' in w and w['syllables']:
                for s in w['syllables']:
                    flat_syllables.append(s)
            else:
                flat_syllables.append({'syllable': w['word'], 'start': w['start'], 'end': w['end']})
    flat_syllables.sort(key=lambda s: s['start'])

    cols_per_staff = 10
    total_cols = min(60, len(columns))  # Render up to 60 columns (6 staves) for clean browser display
    num_staves = max(1, (total_cols + cols_per_staff - 1) // cols_per_staff)
    staff_spacing = 130
    y_staff_start = 110
    svg_height = max(450, 160 + num_staves * staff_spacing)
    
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="100%" height="100%" style="background:#090c14; font-family:-apple-system, sans-serif;">',
        f'<text x="{svg_width//2}" y="32" text-anchor="middle" fill="#00f0ff" font-size="19" font-weight="bold">{title}</text>',
        f'<text x="{svg_width//2}" y="52" text-anchor="middle" fill="{layer_color}" font-size="12" font-weight="bold">LAYER: {layer.upper()} | KEY: {current_key} Major | TRANSPOSITION: {transpose_semitones:+d} semitones</text>',
        f'<text x="{svg_width//2}" y="68" text-anchor="middle" fill="#64748b" font-size="10">💡 Click any note head in the chord to audition its pitch</text>',
        '<!-- Staff Lines -->'
    ]

    # Draw Staves
    for staff_idx in range(num_staves):
        sy = y_staff_start + staff_idx * staff_spacing
        for line in range(5):
            ly = sy + line * 10
            svg_lines.append(f'<line x1="60" y1="{ly}" x2="900" y2="{ly}" stroke="#27354f" stroke-width="1.5" />')
            
        svg_lines.append(f'<line x1="60" y1="{sy}" x2="60" y2="{sy+40}" stroke="#3b82f6" stroke-width="2.5" />')
        svg_lines.append(f'<line x1="900" y1="{sy}" x2="900" y2="{sy+40}" stroke="#3b82f6" stroke-width="2.5" />')
        
        if is_grand_staff:
            svg_lines.append(f'<text x="64" y="{sy+26}" fill="#10b981" font-size="20" font-weight="bold" font-family="serif">&#x1D11E;+𝄢</text>')
            svg_lines.append(f'<text x="68" y="{sy+44}" fill="#10b981" font-size="8" font-weight="bold">Grand</text>')
        elif is_bass_clef:
            svg_lines.append(f'<text x="68" y="{sy+26}" fill="#ffaa00" font-size="22" font-weight="bold" font-family="serif">𝄢</text>')
            svg_lines.append(f'<text x="75" y="{sy+44}" fill="#ffaa00" font-size="9" font-weight="bold">Bass</text>')
        else:
            svg_lines.append(f'<text x="68" y="{sy+28}" fill="#38bdf8" font-size="24" font-weight="bold" font-family="serif">&#x1D11E;</text>')
            svg_lines.append(f'<text x="75" y="{sy+44}" fill="#00f0ff" font-size="9" font-weight="bold">8vb</text>')
            
        svg_lines.append(f'<text x="96" y="{sy+18}" fill="#94a3b8" font-size="16" font-weight="bold">4</text>')
        svg_lines.append(f'<text x="96" y="{sy+36}" fill="#94a3b8" font-size="16" font-weight="bold">4</text>')

    x_start = 135
    x_step = 74
    syll_cursor = 0
    num_sylls = len(flat_syllables)

    # Render each column (chord stack or vocal note)
    for col_i in range(total_cols):
        col = columns[col_i]
        staff_idx = col_i // cols_per_staff
        col_in_staff = col_i % cols_per_staff
        sy = y_staff_start + staff_idx * staff_spacing
        x_pos = x_start + col_in_staff * x_step
        col_start_t = col[0]['start']
        
        # Chord tag display above staff
        chord_tag = next((n.get('chord') for n in col if n.get('chord')), None)
        if chord_tag:
            svg_lines.append(f'<text x="{x_pos}" y="{sy-14}" text-anchor="middle" fill="#ffaa00" font-size="13" font-weight="bold">{chord_tag}</text>')
            
        # Vocal Syllable text display below staff
        if layer == "vocals" and syll_cursor < num_sylls:
            matched_syll = None
            for s_look in range(syll_cursor, min(num_sylls, syll_cursor + 4)):
                s_obj = flat_syllables[s_look]
                if abs(s_obj['start'] - col_start_t) <= 0.45:
                    matched_syll = s_obj['syllable']
                    syll_cursor = s_look + 1
                    break
            if matched_syll:
                svg_lines.append(f'<text x="{x_pos}" y="{sy+74}" text-anchor="middle" fill="#38bdf8" font-size="12" font-weight="700">{matched_syll}</text>')

        # Render all notes in this column (chord stack)
        for n_in_chord_idx, n in enumerate(col):
            raw_pitch = n['pitch'] + transpose_semitones
            note_is_bass = is_bass_clef or (is_grand_staff and raw_pitch < 55)
            display_pitch = raw_pitch if note_is_bass else (raw_pitch + 12)
            
            octave = (display_pitch // 12) - 1
            chroma = display_pitch % 12
            note_name = NOTE_NAMES[chroma]
            is_sharp = IS_SHARP[chroma]
            
            diatonic_step = (octave * 7) + DIATONIC_STEP[chroma]
            ref_step = 16 if note_is_bass else 30
            note_y = (sy + 40) - (diatonic_step - ref_step) * 5.0
            freq_hz = 440.0 * (2.0 ** ((raw_pitch - 69.0) / 12.0))
            
            # Dynamic Ledger Lines
            if note_y >= sy + 48:
                for l_y in range(sy + 50, int(note_y) + 3, 10):
                    svg_lines.append(f'<line x1="{x_pos-10}" y1="{l_y}" x2="{x_pos+10}" y2="{l_y}" stroke="#475569" stroke-width="1.4" />')
            elif note_y <= sy - 8:
                for l_y in range(sy - 10, int(note_y) - 3, -10):
                    svg_lines.append(f'<line x1="{x_pos-10}" y1="{l_y}" x2="{x_pos+10}" y2="{l_y}" stroke="#475569" stroke-width="1.4" />')
                    
            if is_sharp:
                svg_lines.append(f'<text x="{x_pos-12}" y="{note_y+4}" fill="#38bdf8" font-size="13" font-weight="bold">♯</text>')
                
            note_color = "#ffaa00" if note_is_bass else ("#10b981" if is_grand_staff else "#00f0ff")
            raw_dur = max(0.18, min(1.2, float(n.get('end', 0.0) - n.get('start', 0.0))))
            
            svg_lines.append(f'<ellipse class="interactive-note" data-pitch="{raw_pitch}" data-freq="{freq_hz:.2f}" data-dur="{raw_dur:.2f}" data-name="{note_name}{octave}" cx="{x_pos}" cy="{note_y}" rx="5.5" ry="4.2" fill="{note_color}" stroke="#fff" stroke-width="0.8" transform="rotate(-25 {x_pos} {note_y})" style="cursor:pointer;"><title>Click to play: {note_name}{octave} ({freq_hz:.1f} Hz)</title></ellipse>')

        # Measure Bar Line
        if (col_in_staff + 1) % 4 == 0 and col_in_staff < cols_per_staff - 1:
            bar_x = x_pos + (x_step // 2)
            svg_lines.append(f'<line x1="{bar_x}" y1="{sy}" x2="{bar_x}" y2="{sy+40}" stroke="#334155" stroke-width="1.2" />')

    svg_lines.append('</svg>')
    return '\n'.join(svg_lines)


def generate_3vocal_svg_score(song_id="grikiai", transpose_semitones=0, svg_width=980, max_systems=4):
    """
    Renders a comprehensive 3-Vocal Grand Lead Score in SVG:
    - Staff 1: Veronika (Soprano 1 / Lead) in Cyan (#00f0ff) + Lyrics
    - Staff 2: Rūta (Soprano 2 / Harmony) in Emerald (#10b981) + Lyrics
    - Staff 3: Rūtelė (Alto / Counter) in Amber (#f59e0b) + Lyrics
    - Accompaniment Chords above Staff 1 in Yellow (#facc15)
    - Full WebAudio interactive audition on every notehead
    """
    bench_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gold_standards", f"gold_standard_{song_id.lower()}.json")
    if not os.path.exists(bench_file):
        # Fallback to single voice SVG
        return generate_svg_score([], transpose_semitones=transpose_semitones, title=f"3-Voice Score: {song_id}")

    with open(bench_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    title = data.get('title', song_id.capitalize())
    tempo = data['metadata'].get('tempo_bpm', 150)
    key_name = data['metadata'].get('nominal_key', 'A minor')
    staves = data.get('vocal_staves', {})
    chords = data.get('chords', [])

    v1_notes = staves.get('voice1_veronika', [])
    v2_notes = staves.get('voice2_ruta', [])
    v3_notes = staves.get('voice3_rutele', [])

    # Filter notes to the first few systems for clean browser display
    num_systems = min(max_systems, 6)
    system_spacing = 250
    y_start = 120
    svg_height = y_start + num_systems * system_spacing + 40

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="100%" height="100%" style="background:#090c14; font-family:-apple-system, sans-serif;">',
        f'<text x="{svg_width//2}" y="36" text-anchor="middle" fill="#00f0ff" font-size="22" font-weight="900">{title.upper()} - 3-PART VOCAL LEAD SCORE</text>',
        f'<text x="{svg_width//2}" y="58" text-anchor="middle" fill="#94a3b8" font-size="13" font-weight="bold">THE DITTIES (Veronika Lead • Rūta Harmony • Rūtelė Alto) | {tempo} BPM | KEY: {key_name} | {transpose_semitones:+d} st</text>',
        f'<text x="{svg_width//2}" y="76" text-anchor="middle" fill="#64748b" font-size="11">💡 Click any note head across all 3 staves to audition isolated vocal pitch</text>',
    ]

    # Legend tags
    svg_lines.append(f'<rect x="80" y="86" width="12" height="12" fill="#00f0ff" rx="2" />')
    svg_lines.append(f'<text x="98" y="96" fill="#00f0ff" font-size="11" font-weight="bold">Veronika (Lead)</text>')
    svg_lines.append(f'<rect x="230" y="86" width="12" height="12" fill="#10b981" rx="2" />')
    svg_lines.append(f'<text x="248" y="96" fill="#10b981" font-size="11" font-weight="bold">Rūta (Harmony)</text>')
    svg_lines.append(f'<rect x="380" y="86" width="12" height="12" fill="#f59e0b" rx="2" />')
    svg_lines.append(f'<text x="398" y="96" fill="#f59e0b" font-size="11" font-weight="bold">Rūtelė (Alto)</text>')
    svg_lines.append(f'<rect x="520" y="86" width="12" height="12" fill="#facc15" rx="2" />')
    svg_lines.append(f'<text x="538" y="96" fill="#facc15" font-size="11" font-weight="bold">Chords</text>')

    x_left = 70
    x_right = svg_width - 50

    # Draw Systems
    for sys_idx in range(num_systems):
        sys_y = y_start + sys_idx * system_spacing
        system_id = sys_idx + 1

        # System bracket / barline connecting all 3 staves
        bracket_y_top = sys_y
        bracket_y_bot = sys_y + 160 + 40
        svg_lines.append(f'<line x1="{x_left}" y1="{bracket_y_top}" x2="{x_left}" y2="{bracket_y_bot}" stroke="#64748b" stroke-width="3" />')
        svg_lines.append(f'<line x1="{x_right}" y1="{bracket_y_top}" x2="{x_right}" y2="{bracket_y_bot}" stroke="#64748b" stroke-width="2" />')

        # 3 Staves: Staff 1 (Lead, +0), Staff 2 (Harmony, +80), Staff 3 (Alto, +160)
        staves_meta = [
            (sys_y, "Veronika", "#00f0ff", v1_notes),
            (sys_y + 80, "Rūta", "#10b981", v2_notes),
            (sys_y + 160, "Rūtelė", "#f59e0b", v3_notes)
        ]

        # Draw staff lines & clefs
        for staff_y, voice_label, color, n_list in staves_meta:
            for line in range(5):
                ly = staff_y + line * 10
                svg_lines.append(f'<line x1="{x_left}" y1="{ly}" x2="{x_right}" y2="{ly}" stroke="#27354f" stroke-width="1.4" />')

            # Staff Label & Treble Clef
            svg_lines.append(f'<text x="{x_left-8}" y="{staff_y+24}" text-anchor="end" fill="{color}" font-size="10" font-weight="bold">{voice_label}</text>')
            svg_lines.append(f'<text x="{x_left+6}" y="{staff_y+28}" fill="{color}" font-size="24" font-family="serif">&#x1D11E;</text>')

            # Notes for this system & staff
            notes_in_sys = [n for n in n_list if n.get('system') == system_id or (system_id == 1 and n.get('system') <= 2)]
            # If empty for this system, sample first 12
            if not notes_in_sys and n_list:
                slice_start = sys_idx * 12
                notes_in_sys = n_list[slice_start:slice_start + 12]

            # Distribute notes horizontally
            n_count = max(1, len(notes_in_sys))
            x_step = (x_right - x_left - 80) / max(8, n_count)

            for i, note_obj in enumerate(notes_in_sys[:14]):
                nx = x_left + 60 + i * x_step
                midi_p = note_obj.get('midi_pitch', 67) + transpose_semitones
                # Diatonic vertical mapping
                octave = (midi_p // 12) - 1
                chroma = midi_p % 12
                note_name = NOTE_NAMES[chroma]
                diatonic_step = (octave * 7) + DIATONIC_STEP[chroma]
                # E4 is step 30
                ny = (staff_y + 40) - (diatonic_step - 30) * 5.0
                freq = 440.0 * (2.0 ** ((midi_p - 69.0) / 12.0))

                # Notehead
                svg_lines.append(f'<ellipse class="interactive-note" data-pitch="{midi_p}" data-freq="{freq:.2f}" data-name="{note_name}{octave}" data-voice="{voice_label}" cx="{nx:.1f}" cy="{ny:.1f}" rx="5.5" ry="4.2" fill="{color}" stroke="#fff" stroke-width="0.8" transform="rotate(-25 {nx:.1f} {ny:.1f})" style="cursor:pointer;"><title>{voice_label}: {note_name}{octave} ({freq:.1f} Hz)</title></ellipse>')

                # Syllable below staff
                syll = note_obj.get('syllable')
                if syll:
                    svg_lines.append(f'<text x="{nx:.1f}" y="{staff_y+56}" text-anchor="middle" fill="#e2e8f0" font-size="10" font-weight="600">{syll}</text>')

        # Chords row above Staff 1
        sys_chords = [c for c in chords if c.get('page', 1) == 1 and sys_idx * 4 <= chords.index(c) < (sys_idx + 1) * 4]
        if not sys_chords and chords:
            slice_start = sys_idx * 4
            sys_chords = chords[slice_start:slice_start + 4]

        c_step = (x_right - x_left - 80) / max(1, len(sys_chords))
        for ci, c_obj in enumerate(sys_chords):
            cx_pos = x_left + 60 + ci * c_step
            chord_name = c_obj.get('chord', '')
            svg_lines.append(f'<text x="{cx_pos:.1f}" y="{sys_y-12}" fill="#facc15" font-size="14" font-weight="bold">{chord_name}</text>')

        # Measure barlines (every 4 quarter notes)
        for b_i in range(1, 4):
            bx = x_left + 60 + b_i * ((x_right - x_left - 80) / 4)
            svg_lines.append(f'<line x1="{bx}" y1="{sys_y}" x2="{bx}" y2="{bracket_y_bot}" stroke="#334155" stroke-width="1.2" />')

    svg_lines.append('</svg>')
    return '\n'.join(svg_lines)

