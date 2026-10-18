// REMIX DNA // Dynamic Studio Coordinator & WebAudio Engine
// 100% Dynamically driven by song_manifest.json

class RemixStudio {
  constructor() {
    this.audioCtx = null;
    this.manifest = null;
    this.layers = [];
    this.stems = [];
    this.audioElements = {};
    this.gainNodes = {};
    this.panNodes = {};
    this.trackStates = {};
    
    this.isPlaying = false;
    this.currentRemixAudio = null;
    this.currentVocalAudio = null;
    this.currentTransposedAudio = null;
    this.duration = 60.0;
    this.currentSemitones = 0;
    this.currentLayer = "vocals";
    this.isScoreNotesPlaying = false;
    this.scoreNotesPlaybackTimer = null;
    this.currentGenre = 'jungle';
    this.genreData = {
      jungle: {
        title: '🌴 KOLORADO VABALAI (174 BPM RAGGA JUNGLE RE-CREATION)',
        desc: 'Amen Break Slicing // 808 Sub-Bassline // Dub Delay Chops // Airhorn Drops // Vocal Lead',
        file: '/audio/remixes/kolorado_vabalai_jungle_remix.wav',
        loop: '/audio/remixes/kolorado_vabalai_jungle_loop.wav'
      },
      techno: {
        title: '⚡ KOLORADO VABALAI (134 BPM BERLIN TECHNO RE-CREATION)',
        desc: '909 Rumble Kick // 16th Driving Open/Closed Hats // 303 Acid Saw Riff // Sidechain Vocal',
        file: '/audio/remixes/kolorado_vabalai_techno_remix.wav',
        loop: '/audio/remixes/kolorado_vabalai_techno_remix_loop.wav'
      },
      house: {
        title: '🪩 KOLORADO VABALAI (126 BPM FRENCH TOUCH HOUSE RE-CREATION)',
        desc: 'Punchy 909 Groove // Classic M1 Organ Chords // Funky Bouncy Bassline // Upfront Vocal Lead',
        file: '/audio/remixes/kolorado_vabalai_house_remix.wav',
        loop: '/audio/remixes/kolorado_vabalai_house_remix_loop.wav'
      }
    };
    
    this.init();
  }

  async init() {
    await this.loadProjectMeta();
    this.buildDynamicMixerDeck();
    this.buildDynamicScoreTabs();
    this.buildDynamicPitchRouting();
    this.initAudioNodes();
    this.initUIEventListeners();
    this.loadWaveforms();
    this.loadScore(0, this.currentLayer);
    this.startPlayheadSync();
  }

  async loadProjectMeta() {
    try {
      const res = await fetch('/api/project');
      const data = await res.json();
      document.getElementById('track-title').textContent = `${data.title} - ${data.artist}`;
      document.getElementById('track-bpm').textContent = data.original_bpm.toFixed(1);
      document.getElementById('track-key').textContent = data.key;
      this.duration = data.duration_sec || 60.0;
      this.manifest = data.manifest;

      if (this.manifest && this.manifest.layers) {
        this.layers = this.manifest.layers.filter(l => l.is_active);
        this.stems = this.layers.map(l => l.id);
        const badge = document.getElementById('discovery-badge');
        if (badge) {
          badge.textContent = `${this.manifest.active_layers_count} Active Layers Discovered`;
        }
      } else {
        this.stems = ['vocals', 'guitar', 'piano', 'bass', 'drums', 'other'];
      }

      this.stems.forEach(s => {
        this.trackStates[s] = { solo: false, mute: false, vol: 1.0, pan: 0.0 };
      });
    } catch (e) {
      console.warn("Could not load project metadata:", e);
    }
  }

  buildDynamicMixerDeck() {
    const container = document.getElementById('stem-tracks');
    if (!container) return;
    container.innerHTML = '';

    const layersToRender = (this.manifest && this.manifest.layers) ? this.manifest.layers.filter(l => l.is_active) : [
      { id: 'vocals', name: 'Lead Vocals', icon: '🎤', color: '#00f0ff' },
      { id: 'guitar', name: 'Acoustic Guitar', icon: '🎸', color: '#10b981' },
      { id: 'piano', name: 'Piano / Keyboards', icon: '🎹', color: '#f59e0b' },
      { id: 'bass', name: 'Bassline', icon: '🎸', color: '#ffaa00' },
      { id: 'drums', name: 'Drums & Percussion', icon: '🥁', color: '#b026ff' }
    ];

    layersToRender.forEach(l => {
      const trackDiv = document.createElement('div');
      trackDiv.className = 'stem-track';
      trackDiv.dataset.stem = l.id;

      const metricsTag = l.metrics ? `${l.metrics.rms_db} dB | ${(l.metrics.active_duty_cycle * 100).toFixed(0)}%` : '';

      trackDiv.innerHTML = `
        <div class="track-info">
          <div class="track-name" style="color:${l.color || '#38bdf8'}">${l.icon || '🎵'} ${l.name.toUpperCase()}</div>
          <div class="track-metrics-sub" style="font-size:0.65rem; color:#64748b;">${metricsTag}</div>
          <div class="track-actions">
            <button class="btn-track btn-solo" data-action="solo">S</button>
            <button class="btn-track btn-mute" data-action="mute">M</button>
          </div>
          <div class="track-sliders">
            <label>VOL <input type="range" class="slider-vol" min="0" max="1.5" step="0.05" value="1.0"></label>
            <label>PAN <input type="range" class="slider-pan" min="-1" max="1" step="0.1" value="0.0"></label>
          </div>
        </div>
        <div class="canvas-wrapper">
          <canvas class="waveform-canvas" id="canvas-${l.id}" width="800" height="75"></canvas>
          <div class="playhead" id="playhead-${l.id}"></div>
        </div>
      `;
      container.appendChild(trackDiv);
    });

    this.bindMixerTrackEvents();
  }

  buildDynamicScoreTabs() {
    const tabsContainer = document.getElementById('layer-tabs');
    if (!tabsContainer) return;
    tabsContainer.innerHTML = '';

    const harmonicLayers = (this.manifest && this.manifest.layers) 
      ? this.manifest.layers.filter(l => l.is_active && !l.pitch_locked)
      : [
          { id: 'vocals', name: 'Vocals', icon: '🎤' },
          { id: 'guitar', name: 'Guitar', icon: '🎸' },
          { id: 'piano', name: 'Piano', icon: '🎹' },
          { id: 'bass', name: 'Bassline', icon: '🎸' }
        ];

    harmonicLayers.forEach((l, idx) => {
      const btn = document.createElement('button');
      btn.className = `btn-layer-tab ${l.id === this.currentLayer ? 'active' : ''}`;
      btn.dataset.layer = l.id;
      btn.textContent = `${l.icon || ''} ${l.name.toUpperCase()}`;
      btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-layer-tab').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        this.stopScoreNotes();
        this.currentLayer = l.id;
        this.updateAuditionLabels();
        this.loadScore(this.currentSemitones, this.currentLayer);
      });
      tabsContainer.appendChild(btn);
    });
  }

  buildDynamicPitchRouting() {
    const routingContainer = document.getElementById('layer-routing-matrix');
    if (!routingContainer) return;
    routingContainer.innerHTML = '<span class="label">PITCH ROUTING:</span>';

    const layers = (this.manifest && this.manifest.layers) ? this.manifest.layers.filter(l => l.is_active) : [];
    layers.forEach(l => {
      if (l.pitch_locked) {
        const span = document.createElement('span');
        span.className = 'drum-lock-badge';
        span.textContent = `🔒 ${l.name} (Pitch Locked)`;
        routingContainer.appendChild(span);
      } else {
        const label = document.createElement('label');
        label.innerHTML = `<input type="checkbox" id="route-${l.id}" checked> ${l.icon || ''} ${l.name}`;
        routingContainer.appendChild(label);
      }
    });
  }

  buildLayerConfigModal() {
    const list = document.getElementById('modal-layers-list');
    if (!list || !this.manifest || !this.manifest.layers) return;
    list.innerHTML = '';

    this.manifest.layers.forEach(l => {
      const item = document.createElement('div');
      item.className = 'modal-layer-item';
      const m = l.metrics || {};

      item.innerHTML = `
        <div class="modal-layer-left">
          <span style="font-size:1.3rem;">${l.icon}</span>
          <div>
            <div class="modal-layer-name" style="color:${l.color}">${l.name} <span style="font-size:0.75rem; color:#64748b;">(${l.type})</span></div>
            <div class="modal-layer-metrics">RMS: ${m.rms_db || -99} dBFS | Active Duty: ${((m.active_duty_cycle || 0) * 100).toFixed(1)}% | Onsets: ${m.onsets || 0}</div>
          </div>
        </div>
        <div class="modal-layer-right">
          <button class="btn-snippet-play" data-src="${l.audio_file}">▶ Audition</button>
          <label style="display:flex; align-items:center; gap:0.4rem; cursor:pointer;">
            <input type="checkbox" class="toggle-layer-checkbox" data-layer="${l.id}" ${l.is_active ? 'checked' : ''}>
            <span style="font-size:0.75rem; font-weight:bold;">${l.is_active ? 'ENABLED' : 'PRUNED'}</span>
          </label>
        </div>
      `;
      list.appendChild(item);
    });

    // Snippet play handlers
    list.querySelectorAll('.btn-snippet-play').forEach(b => {
      b.addEventListener('click', () => {
        const src = b.dataset.src;
        if (this.currentVocalAudio && !this.currentVocalAudio.paused) {
          this.currentVocalAudio.pause();
          b.textContent = '▶ Audition';
          return;
        }
        this.currentVocalAudio = new Audio(src);
        this.currentVocalAudio.play();
        b.textContent = '⏸ Pause';
        this.currentVocalAudio.onended = () => { b.textContent = '▶ Audition'; };
      });
    });

    // Toggle checkbox handlers
    list.querySelectorAll('.toggle-layer-checkbox').forEach(cb => {
      cb.addEventListener('change', async () => {
        const layerId = cb.dataset.layer;
        try {
          const res = await fetch('/api/manifest/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ layer: layerId })
          });
          const d = await res.json();
          if (d.success) {
            this.manifest = d.manifest;
            cb.nextElementSibling.textContent = cb.checked ? 'ENABLED' : 'PRUNED';
          }
        } catch (e) {
          console.error("Layer toggle error:", e);
        }
      });
    });
  }

  initAudioNodes() {
    this.stems.forEach(stem => {
      const stemObj = this.layers.find(l => l.id === stem);
      const audioUrl = stemObj ? stemObj.audio_file : `/audio/audio/${stem}.wav`;
      const audio = new Audio(audioUrl);
      audio.preload = 'none';
      audio.loop = true;
      this.audioElements[stem] = audio;
    });
  }

  ensureAudioContext() {
    if (!this.audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.audioCtx = new AudioContext();
      this.stems.forEach(stem => {
        const audio = this.audioElements[stem];
        if (!audio) return;
        const source = this.audioCtx.createMediaElementSource(audio);
        const gain = this.audioCtx.createGain();
        const pan = this.audioCtx.createStereoPanner ? this.audioCtx.createStereoPanner() : null;
        
        if (pan) {
          source.connect(pan);
          pan.connect(gain);
        } else {
          source.connect(gain);
        }
        gain.connect(this.audioCtx.destination);
        this.gainNodes[stem] = gain;
        this.panNodes[stem] = pan;
      });
    }
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  // --- Real-Time Acoustic Feedback Synthesizer ---
  playSynthNote(freq, duration = 0.5, layer = this.currentLayer) {
    this.ensureAudioContext();
    if (!freq || isNaN(freq) || freq <= 0) return;

    const now = this.audioCtx.currentTime;
    const osc = this.audioCtx.createOscillator();
    const gain = this.audioCtx.createGain();

    if (layer === 'piano' || layer === 'grand_staff') {
      // Acoustic Grand Piano simulation: rich fundamental + warm 2nd harmonic
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now);

      const osc2 = this.audioCtx.createOscillator();
      const gain2 = this.audioCtx.createGain();
      osc2.type = 'triangle';
      osc2.frequency.setValueAtTime(freq * 2.0, now);

      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.42, now + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

      gain2.gain.setValueAtTime(0.001, now);
      gain2.gain.linearRampToValueAtTime(0.18, now + 0.02);
      gain2.gain.exponentialRampToValueAtTime(0.0001, now + duration * 0.7);

      osc.connect(gain);
      osc2.connect(gain2);
      gain.connect(this.audioCtx.destination);
      gain2.connect(this.audioCtx.destination);

      osc.start(now);
      osc2.start(now);
      osc.stop(now + duration + 0.05);
      osc2.stop(now + duration + 0.05);
      return;
    } else if (layer === 'bass' || layer.endsWith('_low')) {
      // Warm resonant sub-bass sine tone
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now);
      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.55, now + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
      osc.connect(gain);
      gain.connect(this.audioCtx.destination);
    } else if (layer === 'guitar' || layer === 'other' || layer.includes('guitar')) {
      // Acoustic plucked string tone with lowpass filter decay
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(freq, now);
      const filter = this.audioCtx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(1400, now);
      filter.frequency.exponentialRampToValueAtTime(300, now + duration);
      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.32, now + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
      osc.connect(filter);
      filter.connect(gain);
      gain.connect(this.audioCtx.destination);
    } else {
      // Vocal lead tone: warm triangle wave with slight swell
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(freq, now);
      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.40, now + 0.04);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
      osc.connect(gain);
      gain.connect(this.audioCtx.destination);
    }

    osc.start(now);
    osc.stop(now + duration + 0.05);
  }

  playSynthTonicChord(semitones = this.currentSemitones, layer = this.currentLayer) {
    this.ensureAudioContext();
    const factor = Math.pow(2.0, semitones / 12.0);

    let freqs = [];
    let stepDelay = 80;
    let sustain = 1.2;

    if (layer === 'piano' || layer.includes('piano')) {
      // Two-handed Grand Piano Voicing: Left hand (F2, C3) + Right hand (A3, C4, F4, A4)
      freqs = [87.31, 130.81, 220.00, 261.63, 349.23, 440.00];
      stepDelay = 60;
      sustain = 1.6;
    } else if (layer === 'bass' || layer.endsWith('_low')) {
      // Sub-bass tonic register: F1 (43.65 Hz), C2 (65.41 Hz), F2 (87.31 Hz), A2 (110.0 Hz)
      freqs = [43.65, 65.41, 87.31, 110.00];
      stepDelay = 130;
      sustain = 1.4;
    } else if (layer === 'guitar' || layer === 'other' || layer.includes('guitar')) {
      // Acoustic guitar 6-string voicing strum: F2, C3, F3, A3, C4, F4
      freqs = [87.31, 130.81, 174.61, 220.00, 261.63, 349.23];
      stepDelay = 35; // Guitar pick strum speed
      sustain = 1.5;
    } else {
      // Vocal lead range tonic arpeggio: F3, A3, C4, F4, A4
      freqs = [174.61, 220.00, 261.63, 349.23, 440.00];
      stepDelay = 90;
      sustain = 1.3;
    }

    freqs.forEach((bf, idx) => {
      setTimeout(() => {
        this.playSynthNote(bf * factor, sustain, layer);
      }, idx * stepDelay);
    });
  }

  playScoreNotes() {
    const btn = document.getElementById('btn-play-score-notes');
    if (this.isScoreNotesPlaying) {
      this.stopScoreNotes();
      return;
    }

    const wrapper = document.getElementById('score-viewer');
    const noteElements = Array.from(wrapper.querySelectorAll('.interactive-note'));
    if (noteElements.length === 0) return;

    this.ensureAudioContext();
    this.isScoreNotesPlaying = true;
    if (btn) {
      btn.classList.add('playing');
      btn.textContent = `⏹ STOP ${this.currentLayer.toUpperCase()} SCORE NOTES`;
    }

    let currentIndex = 0;
    const playNext = () => {
      if (!this.isScoreNotesPlaying || currentIndex >= noteElements.length) {
        this.stopScoreNotes();
        return;
      }

      const noteEl = noteElements[currentIndex];
      const freq = parseFloat(noteEl.dataset.freq);
      const dur = parseFloat(noteEl.dataset.dur) || 0.28;
      const playDur = Math.max(0.18, Math.min(0.65, dur));

      this.playSynthNote(freq, playDur, this.currentLayer);

      const origFill = noteEl.getAttribute('fill');
      const origStroke = noteEl.getAttribute('stroke');
      const origStrokeWidth = noteEl.getAttribute('stroke-width');

      noteEl.setAttribute('fill', '#ff0055');
      noteEl.setAttribute('stroke', '#ffffff');
      noteEl.setAttribute('stroke-width', '2.5');

      setTimeout(() => {
        noteEl.setAttribute('fill', origFill);
        noteEl.setAttribute('stroke', origStroke);
        noteEl.setAttribute('stroke-width', origStrokeWidth);
      }, playDur * 850);

      currentIndex++;
      const nextDelay = Math.max(160, playDur * 1000 * 0.95);
      this.scoreNotesPlaybackTimer = setTimeout(playNext, nextDelay);
    };

    playNext();
  }

  stopScoreNotes() {
    this.isScoreNotesPlaying = false;
    if (this.scoreNotesPlaybackTimer) {
      clearTimeout(this.scoreNotesPlaybackTimer);
      this.scoreNotesPlaybackTimer = null;
    }
    const btn = document.getElementById('btn-play-score-notes');
    if (btn) {
      btn.classList.remove('playing');
      this.updateAuditionLabels();
    }
    const wrapper = document.getElementById('score-viewer');
    if (wrapper) {
      wrapper.querySelectorAll('.interactive-note').forEach(el => {
        el.setAttribute('stroke-width', '0.8');
      });
    }
  }

  updateAuditionLabels() {
    const baseKeys = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'];
    const keyName = baseKeys[(5 + this.currentSemitones + 120) % 12] + " Major";
    const layerObj = this.manifest && this.manifest.layers ? this.manifest.layers.find(l => l.id === this.currentLayer) : null;
    const lName = layerObj ? layerObj.name.toUpperCase() : this.currentLayer.toUpperCase();
    const stTag = this.currentSemitones > 0 ? `+${this.currentSemitones}` : `${this.currentSemitones}`;

    const btnScore = document.getElementById('btn-play-score-notes');
    if (btnScore && !this.isScoreNotesPlaying) {
      btnScore.textContent = `▶ PLAY TRANSPOSED ${lName} NOTES (${stTag} st)`;
    }

    const btnChord = document.getElementById('btn-play-synth-chord');
    if (btnChord) {
      const chordLabel = (this.currentLayer === 'piano') ? 'GRAND PIANO CHORD' : ((this.currentLayer === 'guitar') ? 'GUITAR STRUM' : `${lName} TONIC`);
      btnChord.textContent = `🔊 PLAY ${chordLabel} (${keyName})`;
    }
  }

  async loadWaveforms() {
    try {
      const res = await fetch('/api/waveforms/all');
      const data = await res.json();
      if (data && data.peaks) {
        Object.keys(data.peaks).forEach(stem => {
          this.drawWaveform(stem, data.peaks[stem] || []);
        });
        return;
      }
    } catch (e) {
      console.warn("Batch waveforms failed, falling back to sequential:", e);
    }

    // Fallback if batch endpoint fails
    for (const stem of this.stems) {
      try {
        const res = await fetch(`/api/waveform/${stem}`);
        const data = await res.json();
        this.drawWaveform(stem, data.peaks || []);
      } catch (e) {
        console.warn(`Failed loading waveform for ${stem}:`, e);
      }
    }
  }

  drawWaveform(stem, peaks) {
    const canvas = document.getElementById(`canvas-${stem}`);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    if (peaks.length === 0) return;

    const layerObj = this.manifest && this.manifest.layers ? this.manifest.layers.find(l => l.id === stem) : null;
    const color = layerObj ? layerObj.color : '#00f0ff';

    ctx.fillStyle = color;
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;

    // Center line
    ctx.beginPath();
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();

    const barWidth = width / peaks.length;
    for (let i = 0; i < peaks.length; i++) {
      const p = peaks[i];
      const barHeight = p * (height * 0.85);
      const x = i * barWidth;
      const y = (height - barHeight) / 2;
      ctx.fillStyle = color;
      ctx.fillRect(x, y, Math.max(1, barWidth - 0.5), barHeight);
    }
  }

  async loadScore(semitones = this.currentSemitones, layer = this.currentLayer) {
    if (this.isScoreNotesPlaying) {
      this.stopScoreNotes();
    }
    const wrapper = document.getElementById('score-viewer');
    wrapper.innerHTML = '<div class="score-loading">Rendering interactive lead sheet...</div>';
    try {
      const res = await fetch(`/api/score/svg?semitones=${semitones}&layer=${layer}&t=${Date.now()}`);
      const svg = await res.text();
      wrapper.innerHTML = svg;

      wrapper.querySelectorAll('.interactive-note').forEach(el => {
        el.addEventListener('click', () => {
          const freq = parseFloat(el.dataset.freq);
          const dur = parseFloat(el.dataset.dur) || 0.6;
          this.playSynthNote(freq, dur, this.currentLayer);
          el.setAttribute('stroke', '#ff0055');
          el.setAttribute('stroke-width', '2.5');
          setTimeout(() => {
            el.setAttribute('stroke', '#fff');
            el.setAttribute('stroke-width', '0.8');
          }, 350);
        });
      });
      this.updateAuditionLabels();
    } catch (e) {
      wrapper.innerHTML = `<div style="color:#ef4444; padding:1rem;">Failed loading score: ${e}</div>`;
    }
  }

  bindMixerTrackEvents() {
    this.stems.forEach(stem => {
      const trackEl = document.querySelector(`.stem-track[data-stem="${stem}"]`);
      if (!trackEl) return;

      const soloBtn = trackEl.querySelector('.btn-solo');
      const muteBtn = trackEl.querySelector('.btn-mute');
      const volSlider = trackEl.querySelector('.slider-vol');
      const panSlider = trackEl.querySelector('.slider-pan');

      soloBtn.addEventListener('click', () => {
        this.trackStates[stem].solo = !this.trackStates[stem].solo;
        soloBtn.classList.toggle('active', this.trackStates[stem].solo);
        this.applyTrackGains();
      });

      muteBtn.addEventListener('click', () => {
        this.trackStates[stem].mute = !this.trackStates[stem].mute;
        muteBtn.classList.toggle('active', this.trackStates[stem].mute);
        this.applyTrackGains();
      });

      volSlider.addEventListener('input', (e) => {
        this.trackStates[stem].vol = parseFloat(e.target.value);
        this.applyTrackGains();
      });

      panSlider.addEventListener('input', (e) => {
        this.trackStates[stem].pan = parseFloat(e.target.value);
        if (this.panNodes[stem]) {
          this.panNodes[stem].pan.value = this.trackStates[stem].pan;
        }
      });

      const canvasWrapper = trackEl.querySelector('.canvas-wrapper');
      canvasWrapper.addEventListener('click', (e) => {
        const rect = canvasWrapper.getBoundingClientRect();
        const ratio = (e.clientX - rect.left) / rect.width;
        this.seekTo(ratio * this.duration);
      });
    });
  }

  initUIEventListeners() {
    // Master Play / Stop
    const btnPlay = document.getElementById('btn-master-play');
    const btnStop = document.getElementById('btn-master-stop');

    btnPlay.addEventListener('click', () => {
      this.ensureAudioContext();
      if (this.isPlaying) {
        this.pauseAllStems();
      } else {
        this.playAllStems();
      }
    });

    btnStop.addEventListener('click', () => {
      this.stopAllStems();
    });

    // Master Volume
    document.getElementById('master-vol').addEventListener('input', () => {
      this.applyTrackGains();
    });

    // Discovery Modal open / close
    const btnModalOpen = document.getElementById('btn-open-discovery-modal');
    const modal = document.getElementById('layer-modal');
    const btnModalClose = document.getElementById('btn-close-modal');
    const btnSaveLayers = document.getElementById('btn-save-layers');

    if (btnModalOpen && modal) {
      btnModalOpen.addEventListener('click', () => {
        this.buildLayerConfigModal();
        modal.style.display = 'flex';
      });
    }

    if (btnModalClose && modal) {
      btnModalClose.addEventListener('click', () => {
        modal.style.display = 'none';
      });
    }

    if (btnSaveLayers && modal) {
      btnSaveLayers.addEventListener('click', () => {
        modal.style.display = 'none';
        // Re-align studio with new layer configuration
        this.layers = this.manifest.layers.filter(l => l.is_active);
        this.stems = this.layers.map(l => l.id);
        this.buildDynamicMixerDeck();
        this.buildDynamicScoreTabs();
        this.buildDynamicPitchRouting();
        this.initAudioNodes();
        this.loadWaveforms();
        this.loadScore(this.currentSemitones, this.currentLayer);
      });
    }

    // Ingest Modal Controls & Live Telemetry Stepper
    const btnOpenIngest = document.getElementById('btn-open-ingest-modal');
    const ingestModal = document.getElementById('ingest-modal');
    const btnCloseIngest = document.getElementById('btn-close-ingest-modal');
    const btnCancelIngest = document.getElementById('btn-cancel-ingest');
    const btnStartIngest = document.getElementById('btn-start-ingest');

    if (btnOpenIngest && ingestModal) {
      btnOpenIngest.addEventListener('click', () => {
        ingestModal.style.display = 'flex';
        const sBox = document.getElementById('ingest-status-box');
        if (sBox) sBox.style.display = 'none';
        const errBox = document.getElementById('ingest-error-box');
        if (errBox) errBox.style.display = 'none';
        if (btnStartIngest) {
          btnStartIngest.disabled = false;
          btnStartIngest.textContent = '🚀 LAUNCH AUTONOMOUS INGESTION';
        }
        if (btnCancelIngest) btnCancelIngest.style.display = 'none';
      });
    }

    const closeIngest = () => {
      if (ingestModal) ingestModal.style.display = 'none';
    };
    if (btnCloseIngest) btnCloseIngest.addEventListener('click', closeIngest);
    if (btnCancelIngest) btnCancelIngest.addEventListener('click', closeIngest);

    const STAGES_ORDER = [
      'downloading',
      'analyzing',
      'demixing',
      'profiling',
      'transcribing',
      'remixing',
      'completed'
    ];

    const updateStepperUI = (task) => {
      if (!task) return;
      const isError = task.status === 'error';
      const isCompleted = task.status === 'completed';
      const curStage = (isError && task.failed_stage) ? task.failed_stage : (task.stage || 'downloading');
      let curIdx = STAGES_ORDER.indexOf(curStage);
      if (curIdx < 0) curIdx = 0;

      STAGES_ORDER.forEach((stageName, idx) => {
        if (stageName === 'completed') return;
        const stageEl = document.getElementById(`stage-${stageName}`);
        const badgeEl = document.getElementById(`badge-${stageName}`);
        if (!stageEl || !badgeEl) return;

        stageEl.classList.remove('active', 'completed', 'error');

        if (isError && idx === curIdx) {
          stageEl.classList.add('error');
          badgeEl.textContent = 'FAILED ❌';
        } else if (isCompleted || (curIdx > idx)) {
          stageEl.classList.add('completed');
          badgeEl.textContent = 'DONE ✔';
        } else if (curIdx === idx) {
          stageEl.classList.add('active');
          badgeEl.textContent = 'ACTIVE ⚙️';
        } else {
          badgeEl.textContent = 'PENDING';
        }
      });

      const pBar = document.getElementById('ingest-progress-bar');
      const pBadge = document.getElementById('ingest-pct-badge');
      const sText = document.getElementById('ingest-status-text');
      const pct = task.progress_pct || 0;

      if (pBar) pBar.style.width = `${pct}%`;
      if (pBadge) pBadge.textContent = `${pct}%`;
      if (sText) sText.textContent = task.stage_msg || 'Processing...';

      const terminal = document.getElementById('ingest-terminal-logs');
      const logCount = document.getElementById('log-count-indicator');
      if (terminal && task.logs) {
        terminal.textContent = task.logs.join('\n');
        terminal.scrollTop = terminal.scrollHeight;
        if (logCount) logCount.textContent = `${task.logs.length} lines`;
      }

      const errBox = document.getElementById('ingest-error-box');
      const errMsg = document.getElementById('ingest-error-msg');
      if (errBox) {
        if (isError) {
          errBox.style.display = 'block';
          if (errMsg) errMsg.textContent = task.error || 'Pipeline execution failed';
        } else {
          errBox.style.display = 'none';
        }
      }
    };

    if (btnStartIngest && ingestModal) {
      btnStartIngest.addEventListener('click', async () => {
        const source = document.getElementById('ingest-source').value.trim();
        const title = document.getElementById('ingest-title').value.trim();
        const artist = document.getElementById('ingest-artist').value.trim();
        const bpm = parseFloat(document.getElementById('ingest-bpm').value) || 174.0;
        const statusBox = document.getElementById('ingest-status-box');
        const errBox = document.getElementById('ingest-error-box');

        if (!source) {
          alert("Please enter a YouTube URL or audio file path.");
          return;
        }

        btnStartIngest.disabled = true;
        btnStartIngest.textContent = '⏳ INGESTION RUNNING...';
        statusBox.style.display = 'block';
        if (errBox) errBox.style.display = 'none';

        try {
          const res = await fetch('/api/ingest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source, title, artist, bpm })
          });
          const data = await res.json();
          if (!data.success) {
            alert(`Could not start ingestion: ${data.error || 'Server error'}`);
            btnStartIngest.disabled = false;
            return;
          }

          const taskId = data.task_id;
          let pollCount = 0;
          const pollStatus = async () => {
            pollCount++;
            try {
              const statusRes = await fetch(`/api/ingest/status?task_id=${taskId}&t=${Date.now()}`);
              const statusData = await statusRes.json();
              if (statusData && statusData.task) {
                const task = statusData.task;
                updateStepperUI(task);

                if (task.status === 'completed') {
                  clearInterval(pollInterval);
                  btnStartIngest.textContent = '✅ INGESTION FINISHED! RELOADING...';
                  setTimeout(() => {
                    window.location.reload();
                  }, 1500);
                } else if (task.status === 'error') {
                  clearInterval(pollInterval);
                  btnStartIngest.disabled = false;
                  btnStartIngest.textContent = '🔄 RETRY INGESTION';
                  if (btnCancelIngest) btnCancelIngest.style.display = 'inline-block';
                }
              }
            } catch (err) {
              console.warn("Telemetry fetch error:", err);
            }

            if (pollCount > 600) {
              clearInterval(pollInterval);
              btnStartIngest.disabled = false;
              btnStartIngest.textContent = '⚠️ TIMEOUT (CHECK CONSOLE)';
              if (btnCancelIngest) btnCancelIngest.style.display = 'inline-block';
            }
          };

          pollStatus();
          const pollInterval = setInterval(pollStatus, 500);

        } catch (err) {
          alert(`Network error starting ingestion: ${err.message}`);
          btnStartIngest.disabled = false;
        }
      });
    }

    // Transposition Slider
    const stSlider = document.getElementById('semitone-slider');
    const stDisplay = document.getElementById('semitone-display');
    stSlider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value);
      this.currentSemitones = val;
      stDisplay.textContent = (val > 0 ? `+${val}` : `${val}`) + ' semitones';
      this.updateTransposePillState(val);
      this.updateAuditionLabels();
      this.loadScore(val, this.currentLayer);
      this.playSynthTonicChord(val, this.currentLayer);
    });

    // Quick Transpose Pills
    document.querySelectorAll('.pill-st').forEach(pill => {
      pill.addEventListener('click', () => {
        const st = parseInt(pill.dataset.st);
        stSlider.value = st;
        this.currentSemitones = st;
        stDisplay.textContent = (st > 0 ? `+${st}` : `${st}`) + ' semitones';
        this.updateTransposePillState(st);
        this.updateAuditionLabels();
        this.loadScore(st, this.currentLayer);
        this.playSynthTonicChord(st, this.currentLayer);
      });
    });

    // Play Transposed Score Notes Button (Sequential Staff Audition)
    const btnScoreNotes = document.getElementById('btn-play-score-notes');
    if (btnScoreNotes) {
      btnScoreNotes.addEventListener('click', () => {
        this.playScoreNotes();
      });
    }

    // Audition Synth Tonic Chord Button (Layer-Aware Full Voicing)
    const btnChord = document.getElementById('btn-play-synth-chord');
    if (btnChord) {
      btnChord.addEventListener('click', () => {
        this.playSynthTonicChord(this.currentSemitones, this.currentLayer);
      });
    }

    // Audition Transposed Layer Audio Button
    const btnTransAudio = document.getElementById('btn-play-transposed-audio');
    if (btnTransAudio) {
      btnTransAudio.addEventListener('click', async () => {
        if (this.currentTransposedAudio && !this.currentTransposedAudio.paused) {
          this.currentTransposedAudio.pause();
          btnTransAudio.classList.remove('playing');
          btnTransAudio.textContent = '▶ AUDITION TRANSPOSED LAYER AUDIO';
          return;
        }

        btnTransAudio.textContent = '⏳ Rendering Transposed Audio...';
        try {
          const res = await fetch('/api/transpose', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              semitones: this.currentSemitones,
              layer: this.currentLayer
            })
          });
          const data = await res.json();
          if (data.preview_audio) {
            this.pauseAllStems();
            this.currentTransposedAudio = new Audio(data.preview_audio + `?t=${Date.now()}`);
            this.currentTransposedAudio.play();
            btnTransAudio.classList.add('playing');
            btnTransAudio.textContent = `⏸ PAUSE TRANSPOSED ${this.currentLayer.toUpperCase()} (${data.key_name})`;
            this.currentTransposedAudio.onended = () => {
              btnTransAudio.classList.remove('playing');
              btnTransAudio.textContent = '▶ AUDITION TRANSPOSED LAYER AUDIO';
            };
          }
        } catch (e) {
          console.error("Transposed audio error:", e);
          btnTransAudio.textContent = '⚠️ Error Playing Audio';
          setTimeout(() => {
            btnTransAudio.textContent = '▶ AUDITION TRANSPOSED LAYER AUDIO';
          }, 2000);
        }
      });
    }

    // Audition Synthetic Recreation Layer (ACE Closed-Loop Synthesis)
    const btnSynthLayer = document.getElementById('btn-play-synthetic-layer');
    if (btnSynthLayer) {
      btnSynthLayer.addEventListener('click', async () => {
        if (this.currentSynthAudio && !this.currentSynthAudio.paused) {
          this.currentSynthAudio.pause();
          btnSynthLayer.classList.remove('playing');
          btnSynthLayer.textContent = '🤖 AUDITION SYNTHETIC LAYER (ACE)';
          return;
        }

        btnSynthLayer.textContent = '⏳ Synthesizing ACE Model...';
        const selectedVoice = document.getElementById('sel-synth-voice')?.value || 'lt-LT-LeonasNeural';
        try {
          const res = await fetch('/api/synthetic/recreate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              semitones: this.currentSemitones,
              layer: this.currentLayer,
              voice: selectedVoice
            })
          });
          const data = await res.json();
          if (data.preview_audio) {
            this.pauseAllStems();
            this.currentSynthAudio = new Audio(data.preview_audio + `?t=${Date.now()}`);
            this.currentSynthAudio.play();
            btnSynthLayer.classList.add('playing');
            btnSynthLayer.textContent = `⏸ PAUSE SYNTHETIC ${this.currentLayer.toUpperCase()}`;
            this.currentSynthAudio.onended = () => {
              btnSynthLayer.classList.remove('playing');
              btnSynthLayer.textContent = '🤖 AUDITION SYNTHETIC LAYER (ACE)';
            };

            // Update HUD if metrics returned
            if (data.accuracy && data.accuracy.fidelity_score) {
              const m = data.accuracy.metrics || {};
              const fidEl = document.getElementById('acc-fidelity');
              const pitchEl = document.getElementById('acc-pitch');
              const chromaEl = document.getElementById('acc-chroma');
              const rmsEl = document.getElementById('acc-rms');
              if (fidEl) fidEl.textContent = `${data.accuracy.fidelity_score}%`;
              if (pitchEl && m.raw_pitch_accuracy_rpa) pitchEl.textContent = `${m.raw_pitch_accuracy_rpa}%`;
              if (chromaEl && m.chroma_similarity) chromaEl.textContent = `${m.chroma_similarity}%`;
              if (rmsEl && m.energy_correlation) rmsEl.textContent = `${m.energy_correlation}%`;
            }
          }
        } catch (e) {
          console.error("Synthetic layer error:", e);
          btnSynthLayer.textContent = '⚠️ Error Synthesizing';
          setTimeout(() => {
            btnSynthLayer.textContent = '🤖 AUDITION SYNTHETIC LAYER (ACE)';
          }, 2000);
        }
      });
    }

    // Recreate Master Song Synthetically & Benchmark Accuracy
    const btnRecreateMaster = document.getElementById('btn-recreate-master');
    if (btnRecreateMaster) {
      btnRecreateMaster.addEventListener('click', async () => {
        btnRecreateMaster.disabled = true;
        btnRecreateMaster.textContent = '⏳ Assembling Synthetic Song...';
        const selectedVoice = document.getElementById('sel-synth-voice')?.value || 'lt-LT-LeonasNeural';
        try {
          const res = await fetch('/api/synthetic/recreate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              semitones: this.currentSemitones,
              layer: 'master',
              voice: selectedVoice
            })
          });
          const data = await res.json();
          if (data.preview_audio) {
            this.pauseAllStems();
            const masterAudio = new Audio(data.preview_audio + `?t=${Date.now()}`);
            masterAudio.play();
            btnRecreateMaster.textContent = `✅ PLAYING SYNTHETIC SONG (${data.layers_count} layers)`;
            setTimeout(() => {
              btnRecreateMaster.disabled = false;
              btnRecreateMaster.textContent = '⚡ RECREATE MASTER SONG';
            }, 4000);

            if (data.accuracy && data.accuracy.overall_fidelity_score) {
              const fidEl = document.getElementById('acc-fidelity');
              if (fidEl) fidEl.textContent = `${data.accuracy.overall_fidelity_score}%`;
            }
          }
        } catch (e) {
          console.error("Master recreate error:", e);
          btnRecreateMaster.disabled = false;
          btnRecreateMaster.textContent = '⚠️ Recreate Failed';
          setTimeout(() => {
            btnRecreateMaster.textContent = '⚡ RECREATE MASTER SONG';
          }, 2000);
        }
      });
    }

    // Vocal Audition Buttons
    document.querySelectorAll('.btn-audition').forEach(btn => {
      btn.addEventListener('click', () => {
        const audioSrc = btn.dataset.audio;
        this.auditionVocal(audioSrc, btn);
      });
    });

    // Genre Switcher Tabs
    document.querySelectorAll('.btn-genre-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.btn-genre-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.currentGenre = tab.dataset.genre;
        this.switchGenre(this.currentGenre);
      });
    });

    // Remix Buttons
    const btnPlayRemix = document.getElementById('btn-play-remix');
    if (btnPlayRemix) {
      btnPlayRemix.addEventListener('click', () => {
        const info = this.genreData[this.currentGenre];
        this.playRemixTrack(info.file);
      });
    }

    const btnPlayLoop = document.getElementById('btn-play-loop');
    if (btnPlayLoop) {
      btnPlayLoop.addEventListener('click', () => {
        const info = this.genreData[this.currentGenre];
        this.playRemixTrack(info.loop);
      });
    }

    // Run Quality Check
    document.getElementById('btn-run-qc').addEventListener('click', async () => {
      try {
        const res = await fetch('/api/quality_check', { method: 'POST' });
        const data = await res.json();
        document.getElementById('qc-jitter').textContent = `${data.jitter.mean_jitter_ms} ms`;
        document.getElementById('qc-consonance').textContent = `${data.dissonance.consonance_score}%`;
      } catch (e) {
        console.warn("Quality check error:", e);
      }
    });

    // Song Library Modal Controls
    const btnOpenLibrary = document.getElementById('btn-open-library-modal');
    const libraryModal = document.getElementById('library-modal');
    const btnCloseLibrary = document.getElementById('btn-close-library-modal');
    const btnLibNewIngest = document.getElementById('btn-library-new-ingest');

    if (btnOpenLibrary && libraryModal) {
      btnOpenLibrary.addEventListener('click', () => {
        this.openSongLibrary();
      });
    }
    if (btnCloseLibrary && libraryModal) {
      btnCloseLibrary.addEventListener('click', () => {
        libraryModal.style.display = 'none';
      });
    }
    if (btnLibNewIngest) {
      btnLibNewIngest.addEventListener('click', () => {
        if (libraryModal) libraryModal.style.display = 'none';
        const ingestModal = document.getElementById('ingest-modal');
        if (ingestModal) ingestModal.style.display = 'flex';
      });
    }

    // Layer Surgery Modal Controls
    const btnOpenSurgery = document.getElementById('btn-open-surgery-modal');
    const surgeryModal = document.getElementById('surgery-modal');
    const btnCloseSurgery = document.getElementById('btn-close-surgery-modal');
    const tabMerge = document.getElementById('tab-surgery-merge');
    const tabSplit = document.getElementById('tab-surgery-split');
    const panelMerge = document.getElementById('surgery-merge-panel');
    const panelSplit = document.getElementById('surgery-split-panel');

    if (btnOpenSurgery && surgeryModal) {
      btnOpenSurgery.addEventListener('click', () => {
        this.openSurgeryModal();
      });
    }
    if (btnCloseSurgery && surgeryModal) {
      btnCloseSurgery.addEventListener('click', () => {
        surgeryModal.style.display = 'none';
      });
    }
    if (tabMerge && tabSplit && panelMerge && panelSplit) {
      tabMerge.addEventListener('click', () => {
        tabMerge.classList.add('active');
        tabSplit.classList.remove('active');
        panelMerge.style.display = 'flex';
        panelSplit.style.display = 'none';
      });
      tabSplit.addEventListener('click', () => {
        tabSplit.classList.add('active');
        tabMerge.classList.remove('active');
        panelSplit.style.display = 'flex';
        panelMerge.style.display = 'none';
      });
    }

    // Quick-Merge Folk Guitar Preset Button
    const btnQuickGuitar = document.getElementById('btn-quick-merge-guitar');
    if (btnQuickGuitar) {
      btnQuickGuitar.addEventListener('click', () => {
        document.querySelectorAll('.merge-src-checkbox').forEach(cb => {
          cb.checked = (cb.value === 'bass' || cb.value === 'guitar');
        });
        const idInput = document.getElementById('merge-target-id');
        const nameInput = document.getElementById('merge-target-name');
        const clefSelect = document.getElementById('merge-target-clef');
        if (idInput) idInput.value = 'acoustic_guitar';
        if (nameInput) nameInput.value = 'Acoustic Guitar (Full Range)';
        if (clefSelect) clefSelect.value = 'grand_staff';
      });
    }

    // Execute Merge Button
    const btnExecMerge = document.getElementById('btn-execute-merge');
    if (btnExecMerge) {
      btnExecMerge.addEventListener('click', () => {
        this.executeMerge();
      });
    }

    // Split Frequency Slider
    const splitSlider = document.getElementById('split-freq-slider');
    const splitDisplay = document.getElementById('split-freq-display');
    if (splitSlider && splitDisplay) {
      splitSlider.addEventListener('input', (e) => {
        const hz = parseInt(e.target.value);
        let noteEst = "G3";
        if (hz < 130) noteEst = "B2";
        else if (hz < 165) noteEst = "E3";
        else if (hz < 220) noteEst = "A3";
        else if (hz < 280) noteEst = "C4";
        else if (hz < 350) noteEst = "E4";
        else noteEst = "A4";
        splitDisplay.textContent = `${hz} Hz (Approx Pitch: ${noteEst})`;
      });
    }

    // Execute Split Button
    const btnExecSplit = document.getElementById('btn-execute-split');
    if (btnExecSplit) {
      btnExecSplit.addEventListener('click', () => {
        this.executeSplit();
      });
    }
  }

  updateTransposePillState(st) {
    document.querySelectorAll('.pill-st').forEach(p => {
      p.classList.toggle('active', parseInt(p.dataset.st) === st);
    });
  }

  applyTrackGains() {
    const masterVol = parseFloat(document.getElementById('master-vol').value);
    const hasSolo = this.stems.some(s => this.trackStates[s] && this.trackStates[s].solo);

    this.stems.forEach(stem => {
      if (!this.gainNodes[stem]) return;
      const state = this.trackStates[stem];
      if (!state) return;
      let gainVal = 0.0;
      if (hasSolo) {
        gainVal = state.solo && !state.mute ? state.vol * masterVol : 0.0;
      } else {
        gainVal = state.mute ? 0.0 : state.vol * masterVol;
      }
      this.gainNodes[stem].gain.setTargetAtTime(gainVal, this.audioCtx.currentTime, 0.02);
    });
  }

  playAllStems() {
    this.stems.forEach(stem => {
      if (this.audioElements[stem]) {
        this.audioElements[stem].play();
      }
    });
    this.isPlaying = true;
    document.getElementById('btn-master-play').textContent = '⏸ PAUSE ALL STEMS';
  }

  pauseAllStems() {
    this.stems.forEach(stem => {
      if (this.audioElements[stem]) {
        this.audioElements[stem].pause();
      }
    });
    this.isPlaying = false;
    document.getElementById('btn-master-play').textContent = '▶ PLAY ALL STEMS';
  }

  stopAllStems() {
    this.pauseAllStems();
    this.seekTo(0);
  }

  seekTo(seconds) {
    this.stems.forEach(stem => {
      if (this.audioElements[stem]) {
        this.audioElements[stem].currentTime = seconds;
      }
    });
  }

  auditionVocal(src, btn) {
    if (this.currentVocalAudio && !this.currentVocalAudio.paused) {
      this.currentVocalAudio.pause();
      document.querySelectorAll('.btn-audition').forEach(b => b.classList.remove('playing'));
      if (this.currentVocalAudio.src.endsWith(src)) {
        return;
      }
    }
    this.currentVocalAudio = new Audio(src);
    this.currentVocalAudio.play();
    btn.classList.add('playing');
    this.currentVocalAudio.onended = () => {
      btn.classList.remove('playing');
    };
  }

  switchGenre(genre) {
    this.currentGenre = genre;
    const info = this.genreData[genre] || this.genreData['jungle'];
    document.getElementById('remix-genre-title').textContent = info.title;
    document.getElementById('remix-genre-desc').textContent = info.desc;
    document.getElementById('btn-play-remix').textContent = `▶ PLAY ${genre.toUpperCase()} REMIX`;
    
    const dlBtn = document.getElementById('btn-dl-remix');
    if (dlBtn) {
      dlBtn.href = info.file;
      dlBtn.download = info.file.split('/').pop();
    }

    if (this.currentRemixAudio && !this.currentRemixAudio.paused) {
      this.currentRemixAudio.pause();
      this.currentRemixAudio = null;
    }
  }

  playRemixTrack(src) {
    const genre = this.currentGenre;
    const genreUpper = genre.toUpperCase();
    const btnPlay = document.getElementById('btn-play-remix');

    if (this.currentRemixAudio && !this.currentRemixAudio.paused) {
      this.currentRemixAudio.pause();
      btnPlay.textContent = `▶ PLAY ${genreUpper} REMIX`;
      return;
    }
    this.pauseAllStems();
    this.currentRemixAudio = new Audio(src);
    this.currentRemixAudio.play();
    btnPlay.textContent = `⏸ PAUSE ${genreUpper} REMIX`;
    this.currentRemixAudio.onended = () => {
      btnPlay.textContent = `▶ PLAY ${genreUpper} REMIX`;
    };
  }

  startPlayheadSync() {
    const update = () => {
      const ref = this.audioElements['vocals'] || this.audioElements[this.stems[0]];
      if (ref && !isNaN(ref.currentTime) && ref.duration > 0) {
        const t = ref.currentTime;
        const dur = ref.duration || this.duration;
        const pct = (t / dur) * 100.0;

        this.stems.forEach(stem => {
          const ph = document.getElementById(`playhead-${stem}`);
          if (ph) ph.style.left = `${pct}%`;
        });

        const formatTime = (sec) => {
          const m = Math.floor(sec / 60);
          const s = Math.floor(sec % 60);
          const ms = Math.floor((sec % 1) * 100);
          return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
        };
        const disp = document.getElementById('time-display');
        if (disp) disp.textContent = `${formatTime(t)} / ${formatTime(dur)}`;
      }
      requestAnimationFrame(update);
    };
    requestAnimationFrame(update);
  }

  async openSongLibrary() {
    const modal = document.getElementById('library-modal');
    const list = document.getElementById('library-songs-list');
    if (!modal || !list) return;
    list.innerHTML = '<div style="color:#94a3b8; padding:1rem; font-style:italic;">Loading song catalog from SQLite database...</div>';
    modal.style.display = 'flex';

    try {
      const res = await fetch('/api/songs?t=' + Date.now());
      const data = await res.json();
      if (!data.songs || data.songs.length === 0) {
        list.innerHTML = '<div style="color:#94a3b8; padding:1rem;">No songs found in catalog. Ingest your first track!</div>';
        return;
      }

      list.innerHTML = '';
      data.songs.forEach(song => {
        const isCurrent = song.is_current;
        const card = document.createElement('div');
        card.className = `library-song-card ${isCurrent ? 'active-song' : ''}`;
        card.innerHTML = `
          <div class="library-card-info">
            <h4>${song.title} ${isCurrent ? '<span class="library-pill active-pill">LOADED IN STUDIO</span>' : ''}</h4>
            <div class="artist-line">by ${song.artist || 'Unknown Artist'}</div>
            <div class="library-pill-row">
              <span class="library-pill">BPM: ${(song.original_bpm || 120).toFixed(1)}</span>
              <span class="library-pill">Key: ${song.key || 'C Major'}</span>
              <span class="library-pill">Duration: ${Math.round(song.duration_sec || 60)}s</span>
              <span class="library-pill">${song.active_layers} Active / ${song.total_layers} Total Layers</span>
            </div>
          </div>
          <div class="library-card-actions">
            ${isCurrent 
              ? '<button class="btn-action" disabled style="opacity:0.6; cursor:default;">CURRENT TRACK</button>' 
              : `<button class="btn-action btn-load-song" data-id="${song.id}" style="background:#2563eb; color:#fff; border-color:#2563eb; font-weight:bold;">▶ LOAD TRACK</button>`
            }
          </div>
        `;
        list.appendChild(card);
      });

      list.querySelectorAll('.btn-load-song').forEach(btn => {
        btn.addEventListener('click', async () => {
          const sid = btn.dataset.id;
          btn.textContent = '⏳ Loading...';
          btn.disabled = true;
          await this.switchSong(sid);
        });
      });

    } catch (e) {
      list.innerHTML = `<div style="color:#ef4444; padding:1rem;">Error querying SQLite catalog: ${e.message}</div>`;
    }
  }

  async switchSong(songId) {
    try {
      this.stopAllStems();
      const res = await fetch('/api/songs/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ song_id: songId })
      });
      const data = await res.json();
      if (data.success) {
        const modal = document.getElementById('library-modal');
        if (modal) modal.style.display = 'none';

        // Re-initialize entire studio with new song manifest
        await this.loadProjectMeta();
        this.buildDynamicMixerDeck();
        this.buildDynamicScoreTabs();
        this.buildDynamicPitchRouting();
        this.initAudioNodes();
        this.loadWaveforms();
        const activeHarmonic = this.manifest.layers.find(l => l.is_active && !l.pitch_locked);
        this.currentLayer = activeHarmonic ? activeHarmonic.id : "vocals";
        this.loadScore(0, this.currentLayer);
      } else {
        alert(`Failed switching song: ${data.error}`);
      }
    } catch (e) {
      alert(`Network error switching song: ${e.message}`);
    }
  }

  openSurgeryModal() {
    const modal = document.getElementById('surgery-modal');
    if (!modal) return;
    const checklist = document.getElementById('surgery-merge-checklist');
    const select = document.getElementById('split-source-select');
    const statusMerge = document.getElementById('merge-status-box');
    const statusSplit = document.getElementById('split-status-box');

    if (statusMerge) statusMerge.style.display = 'none';
    if (statusSplit) statusSplit.style.display = 'none';

    // Populate merge checklist
    if (checklist && this.manifest && this.manifest.layers) {
      checklist.innerHTML = '';
      this.manifest.layers.forEach(l => {
        const row = document.createElement('label');
        row.className = 'surgery-layer-row';
        const isPreselected = (l.id === 'bass' || l.id === 'guitar');
        const m = l.metrics || {};
        row.innerHTML = `
          <div class="surgery-layer-left">
            <input type="checkbox" class="merge-src-checkbox" value="${l.id}" ${isPreselected ? 'checked' : ''}>
            <span style="color:${l.color || '#fff'}">${l.icon || '🎵'} <strong>${l.name}</strong> <span style="font-size:0.75rem; color:#64748b;">(${l.id})</span></span>
          </div>
          <div class="surgery-layer-metrics">${m.rms_db ? `${m.rms_db} dBFS | ${(m.active_duty_cycle*100).toFixed(0)}% duty` : (l.is_active ? 'Active' : 'Inactive')}</div>
        `;
        checklist.appendChild(row);
      });
    }

    // Populate split source select
    if (select && this.manifest && this.manifest.layers) {
      select.innerHTML = '';
      this.manifest.layers.filter(l => l.is_active).forEach(l => {
        const opt = document.createElement('option');
        opt.value = l.id;
        opt.textContent = `${l.icon || ''} ${l.name} (${l.id})`;
        if (l.id === 'guitar' || l.id === 'piano' || l.id === 'acoustic_guitar') opt.selected = true;
        select.appendChild(opt);
      });
    }

    modal.style.display = 'flex';
  }

  async executeMerge() {
    const checked = Array.from(document.querySelectorAll('.merge-src-checkbox:checked')).map(cb => cb.value);
    const statusBox = document.getElementById('merge-status-box');
    const btn = document.getElementById('btn-execute-merge');

    if (checked.length < 2) {
      if (statusBox) {
        statusBox.style.display = 'block';
        statusBox.style.background = 'rgba(239,68,68,0.15)';
        statusBox.style.border = '1px solid #ef4444';
        statusBox.style.color = '#fca5a5';
        statusBox.textContent = '⚠️ Please select at least two source layers to merge.';
      }
      return;
    }

    const targetId = document.getElementById('merge-target-id').value.trim() || 'acoustic_guitar';
    const targetName = document.getElementById('merge-target-name').value.trim() || 'Acoustic Guitar (Full Range)';
    const targetClef = document.getElementById('merge-target-clef').value;
    const replaceSources = document.getElementById('merge-replace-sources').checked;

    btn.disabled = true;
    btn.textContent = '⏳ Summing Audio & Merging Notes...';
    if (statusBox) {
      statusBox.style.display = 'block';
      statusBox.style.background = 'rgba(59,130,246,0.15)';
      statusBox.style.border = '1px solid #3b82f6';
      statusBox.style.color = '#93c5fd';
      statusBox.textContent = `Merging ${checked.join(' + ')} into '${targetName}'...`;
    }

    try {
      const res = await fetch('/api/layers/merge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          song_id: this.manifest ? this.manifest.song_id : null,
          source_layer_ids: checked,
          target_layer_id: targetId,
          target_name: targetName,
          target_clef: targetClef,
          replace_sources: replaceSources
        })
      });

      const data = await res.json();
      if (data.success) {
        statusBox.style.background = 'rgba(16,185,129,0.15)';
        statusBox.style.border = '1px solid #10b981';
        statusBox.style.color = '#6ee7b7';
        statusBox.textContent = `✔ Merge Complete! ${data.num_notes} notes combined with soft peak limiting.`;

        this.manifest = data.manifest;
        this.layers = this.manifest.layers.filter(l => l.is_active);
        this.stems = this.layers.map(l => l.id);
        this.currentLayer = targetId;

        setTimeout(() => {
          const modal = document.getElementById('surgery-modal');
          if (modal) modal.style.display = 'none';
          btn.disabled = false;
          btn.textContent = '🪢 EXECUTE LAYER MERGE';

          // Refresh studio view
          this.buildDynamicMixerDeck();
          this.buildDynamicScoreTabs();
          this.buildDynamicPitchRouting();
          this.initAudioNodes();
          this.loadWaveforms();
          this.loadScore(this.currentSemitones, this.currentLayer);
        }, 1000);

      } else {
        throw new Error(data.error || 'Merge failed');
      }
    } catch (e) {
      btn.disabled = false;
      btn.textContent = '🪢 EXECUTE LAYER MERGE';
      if (statusBox) {
        statusBox.style.background = 'rgba(239,68,68,0.15)';
        statusBox.style.border = '1px solid #ef4444';
        statusBox.style.color = '#fca5a5';
        statusBox.textContent = `❌ Error: ${e.message}`;
      }
    }
  }

  async executeSplit() {
    const srcSelect = document.getElementById('split-source-select');
    const sourceId = srcSelect ? srcSelect.value : null;
    const crossoverFreq = parseFloat(document.getElementById('split-freq-slider').value) || 200.0;
    const lowName = document.getElementById('split-low-name').value.trim();
    const highName = document.getElementById('split-high-name').value.trim();
    const statusBox = document.getElementById('split-status-box');
    const btn = document.getElementById('btn-execute-split');

    if (!sourceId) return;

    btn.disabled = true;
    btn.textContent = '⏳ Applying Linkwitz-Riley Crossover...';
    if (statusBox) {
      statusBox.style.display = 'block';
      statusBox.style.background = 'rgba(59,130,246,0.15)';
      statusBox.style.border = '1px solid #3b82f6';
      statusBox.style.color = '#93c5fd';
      statusBox.textContent = `Filtering '${sourceId}' at ${crossoverFreq} Hz...`;
    }

    try {
      const res = await fetch('/api/layers/split', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          song_id: this.manifest ? this.manifest.song_id : null,
          source_layer_id: sourceId,
          crossover_freq: crossoverFreq,
          low_name: lowName,
          high_name: highName
        })
      });

      const data = await res.json();
      if (data.success) {
        statusBox.style.background = 'rgba(16,185,129,0.15)';
        statusBox.style.border = '1px solid #10b981';
        statusBox.style.color = '#6ee7b7';
        statusBox.textContent = `✔ Split Complete! Created Low and High register layers.`;

        this.manifest = data.manifest;
        this.layers = this.manifest.layers.filter(l => l.is_active);
        this.stems = this.layers.map(l => l.id);

        setTimeout(() => {
          const modal = document.getElementById('surgery-modal');
          if (modal) modal.style.display = 'none';
          btn.disabled = false;
          btn.textContent = '✂️ EXECUTE LAYER SPLIT';

          this.buildDynamicMixerDeck();
          this.buildDynamicScoreTabs();
          this.buildDynamicPitchRouting();
          this.initAudioNodes();
          this.loadWaveforms();
          this.loadScore(this.currentSemitones, this.currentLayer);
        }, 1000);

      } else {
        throw new Error(data.error || 'Split failed');
      }
    } catch (e) {
      btn.disabled = false;
      btn.textContent = '✂️ EXECUTE LAYER SPLIT';
      if (statusBox) {
        statusBox.style.background = 'rgba(239,68,68,0.15)';
        statusBox.style.border = '1px solid #ef4444';
        statusBox.style.color = '#fca5a5';
        statusBox.textContent = `❌ Error: ${e.message}`;
      }
    }
  }
}

window.addEventListener('DOMContentLoaded', () => {
  window.studio = new RemixStudio();
});
