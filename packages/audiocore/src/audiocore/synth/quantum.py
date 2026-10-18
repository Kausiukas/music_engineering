import numpy as np
from typing import Dict, Tuple, List

class QuantumRelationalSynth:
    """
    4-Site Transverse-Field Ising Model (TFIM) with RK4 Spin Precession,
    Landau-Lifshitz Damping, and 7-Spin Harmonic QUBO Chord Solver.
    Control rate: 1000 Hz (dt = 0.001s).
    """
    def __init__(self, J: float = 1.0, h: float = 0.85, T: float = 0.15, gamma: float = 0.06, seed: int = 42):
        self.J = float(J)
        self.h = float(h)
        self.T = float(T)
        self.gamma = float(gamma)
        self.dt = 0.001  # 1000 Hz control rate
        self.rng = np.random.default_rng(seed)

        # Initialize 4-site spin ring S_i = (Sx, Sy, Sz) on unit sphere |S_i| = 1
        angles_theta = self.rng.uniform(0.1, np.pi - 0.1, size=4)
        angles_phi = self.rng.uniform(0.0, 2.0 * np.pi, size=4)
        self.spins = np.stack([
            np.sin(angles_theta) * np.cos(angles_phi),
            np.sin(angles_theta) * np.sin(angles_phi),
            np.cos(angles_theta)
        ], axis=-1).astype(np.float64)
        self._normalize_spins()

    def _normalize_spins(self) -> None:
        norms = np.linalg.norm(self.spins, axis=-1, keepdims=True)
        norms = np.where(norms < 1e-12, 1.0, norms)
        self.spins = self.spins / norms

    def _compute_effective_field(self, s_state: np.ndarray, noise_xy: np.ndarray) -> np.ndarray:
        """
        Computes B_i^eff = (Bx, By, Bz) for the 4-site periodic ring:
        B_i^z = J * (S_{i-1}^z + S_{i+1}^z)
        B_i^x = h + N(0, T * 0.2)
        B_i^y = N(0, T * 0.2)
        """
        sz_prev = np.roll(s_state[:, 2], 1)
        sz_next = np.roll(s_state[:, 2], -1)
        bz = self.J * (sz_prev + sz_next)
        bx = self.h + noise_xy[:, 0]
        by = noise_xy[:, 1]
        return np.stack([bx, by, bz], axis=-1)

    def _landau_lifshitz_rhs(self, s_state: np.ndarray, b_eff: np.ndarray) -> np.ndarray:
        """
        T_i = S_i x B_i (Precession Torque)
        D_i = S_i x (S_i x B_i) (Dissipative Damping)
        dS_i / dt = 2 * T_i - gamma * D_i
        """
        torque = np.cross(s_state, b_eff)
        damping = np.cross(s_state, torque)
        return 2.0 * torque - self.gamma * damping

    def step_rk4(self) -> np.ndarray:
        """Advances the 4-site spin lattice by one control step dt = 0.001s via RK4."""
        sigma_thermal = self.T * 0.2
        noise_xy = self.rng.normal(0.0, sigma_thermal, size=(4, 2))

        b1 = self._compute_effective_field(self.spins, noise_xy)
        k1 = self._landau_lifshitz_rhs(self.spins, b1)

        s2 = self.spins + 0.5 * self.dt * k1
        b2 = self._compute_effective_field(s2, noise_xy)
        k2 = self._landau_lifshitz_rhs(s2, b2)

        s3 = self.spins + 0.5 * self.dt * k2
        b3 = self._compute_effective_field(s3, noise_xy)
        k3 = self._landau_lifshitz_rhs(s3, b3)

        s4 = self.spins + self.dt * k3
        b4 = self._compute_effective_field(s4, noise_xy)
        k4 = self._landau_lifshitz_rhs(s4, b4)

        self.spins = self.spins + (self.dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        self._normalize_spins()
        return self.spins.copy()

    def generate_modulation_curves(self, duration_sec: float) -> Dict[str, np.ndarray]:
        """
        Simulates spin trajectory at 1000 Hz and outputs the 4 physical-to-acoustic
        parameter curves plus criticality telemetry.
        """
        n_steps = int(np.ceil(duration_sec / self.dt))
        traj = np.zeros((n_steps, 4, 3), dtype=np.float64)
        for idx in range(n_steps):
            traj[idx] = self.step_rk4()

        s0_z = traj[:, 0, 2]
        s1_z_abs = np.abs(traj[:, 1, 2])
        s2_x_abs = np.abs(traj[:, 2, 0])
        s3_x = traj[:, 3, 0]

        f_sub = 42.0 + 12.0 * s0_z
        rate_wobble = 5.0 + 4.5 * s1_z_abs
        f_cutoff = 400.0 + 1200.0 * np.clip(s2_x_abs, 0.1, 1.0)
        dt_jitter = 0.005 * s3_x
        reese_drive = 2.5 + 1.5 * s1_z_abs
        is_critical = abs(self.h - self.J) < 0.25

        return {
            "f_sub_hz": f_sub,
            "rate_wobble_hz": rate_wobble,
            "f_cutoff_hz": f_cutoff,
            "dt_jitter_sec": dt_jitter,
            "reese_drive": reese_drive,
            "is_critical": np.full(n_steps, is_critical, dtype=bool),
            "raw_spins": traj
        }

    def solve_harmonic_qubo(
        self,
        mode: str = "dorian",
        cardinality_k: int = 4,
        prev_voicing: np.ndarray = None,
        penalty_lambda: float = 4.0
    ) -> Tuple[np.ndarray, float]:
        """
        Solves the 7-spin Harmonic QUBO across all 2^7 = 128 states via exact
        Boltzmann-weighted quantum annealing evaluation to select optimal modal chord
        voicings.
        """
        J_mat = np.zeros((7, 7), dtype=np.float64)
        # Reward tertian/quartal/seventh consonances across scale degrees 0..6
        consonant_pairs = [(0, 2, 1.8), (0, 4, 2.2), (2, 4, 1.6), (0, 6, 1.5), (2, 6, 1.4), (1, 4, 1.2), (3, 6, 1.1)]
        if mode == "phrygian":
            # Reward characteristic Phrygian b2 (degree 1) + root/fifth tension
            consonant_pairs.extend([(0, 1, 1.6), (1, 4, 1.7)])
        elif mode == "dorian":
            # Reward Dorian minor 7th + major 6th/9th jazz extensions
            consonant_pairs.extend([(0, 5, 1.5), (2, 5, 1.6), (1, 5, 1.4)])

        for u, v, weight in consonant_pairs:
            J_mat[u, v] = weight
            J_mat[v, u] = weight

        # Penalize adjacent semitone/whole-tone muddiness unless stylistically enabled
        for u in range(6):
            if J_mat[u, u + 1] == 0.0:
                J_mat[u, u + 1] = -1.25
                J_mat[u + 1, u] = -1.25

        h_vec = np.array([1.2, 0.4, 0.9, 0.5, 1.0, 0.6, 0.8], dtype=np.float64)
        if prev_voicing is not None and len(prev_voicing) == 7:
            # Neo-Riemannian parsimonious voice-leading bias (retain 2 common tones, shift 1-2)
            h_vec += 0.65 * prev_voicing

        best_energy = float("inf")
        candidates = []
        energies = []
        for state_int in range(1, 128):
            x = np.array([(state_int >> b) & 1 for b in range(7)], dtype=np.float64)
            interaction = -0.5 * float(x @ J_mat @ x)
            linear = -float(np.dot(h_vec, x))
            constraint = penalty_lambda * ((np.sum(x) - cardinality_k) ** 2)
            energy = interaction + linear + constraint
            candidates.append(x)
            energies.append(energy)
            if energy < best_energy:
                best_energy = energy

        # Thermal/tunneling sampling near ground state
        energies_arr = np.array(energies)
        beta = 1.0 / max(self.T, 0.05)
        logits = -beta * (energies_arr - np.min(energies_arr))
        probs = np.exp(logits)
        probs /= np.sum(probs)
        chosen_idx = self.rng.choice(len(candidates), p=probs)
        return candidates[chosen_idx].astype(int), float(energies_arr[chosen_idx])


class MathLaboratorySynth:
    """
    Closed-form mathematical synthesis & visual telemetry generator inspired by @thelab.67.
    Produces 100% phase-coherent audio waveforms alongside exact analytical beat-domain
    curves y(x) for 60 FPS live Cartesian plotting.
    """
    SCALE_SEMITONES = {
        "minor": np.array([0, 2, 3, 5, 7, 8, 10, 12], dtype=np.float64),
        "dorian": np.array([0, 2, 3, 5, 7, 9, 10, 12], dtype=np.float64),
        "phrygian": np.array([0, 1, 3, 5, 7, 8, 10, 12], dtype=np.float64),
    }

    STAGE_MATRIX = [
        ("1. SUB KICK", r"$y = 5e^{-14r} - 1 - r/2$", "exponential pitch punch locks the 43Hz sub fundamental"),
        ("2. REVERSE BASS", r"$y = -1.9 + 1.6w^2$", "parabolic reverse-bass swell fills the off-beat vacuum"),
        ("3. HI-HAT BURST", r"$H(x) = A(x)\sin(2\pi f_h x)$", "metallic transient ticks slice the 16th-note grid"),
        ("4. QUBO CHORDS", r"$H(\mathbf{x}) = -\frac{1}{2}\mathbf{x}^T J \mathbf{x} - \mathbf{h}^T\mathbf{x}$", "7-spin quantum Ising solver locks consonant 4-note voicings"),
        ("5. DX7 FM BELL", r"$y = \sin(2\pi f t + I e^{-t/\tau}\sin 2\pi f_m t)$", "one sine bends another: 1983 DX7 phase modulation"),
        ("6. OCTAVE WOBBLE", r"$f_c(t) = 70\cdot 2^{5.5\sin^2(\pi r t)}\text{ Hz}$", "r = 1, 2, 3, 4 wobbles per beat: exponential filter sweep"),
        ("7. TAPE WARP", r"$\mathrm{speed}(t) = (1 - t/T)^2$", "quadratic deceleration pulls the pre-drop to a standstill"),
        ("8. DIRAC DROP", r"$y(x) = K(x) + H(x) + C(x) + L(x)$", "four functions, one drop: full mathematical superposition"),
        ("9. PHONK LIFT", r"$y = \mathrm{scale}(\lfloor 4x \rfloor - 7) \to -1 - 23\sin^2\frac{\pi(x-2)}{2}$", "lift, drop, loop: one function"),
        ("10. CLIMAX 2X", r"$y(x) = K(2x \bmod 1) + L(x) + L_{+1}(x)$", "double-time kick + octave-doubled lead climax"),
    ]

    def __init__(self, sr: int = 44100, bpm: float = 174.0, f_root_hz: float = 43.65):
        self.sr = int(sr)
        self.bpm = float(bpm)
        self.f_root_hz = float(f_root_hz)

    @staticmethod
    def eval_kick_curve(x_beats: np.ndarray, double_time: bool = False) -> np.ndarray:
        """Piecewise kick + reverse-bass visual curve K(x) in [-2.0, 4.0] (PF3LqHECSQs)."""
        r = np.mod(2.0 * x_beats if double_time else x_beats, 1.0)
        w = (r - 0.775) / 0.225
        return np.where(r < 0.55, 5.0 * np.exp(-14.0 * r) - 1.0 - 0.5 * r, -1.9 + 1.6 * (w ** 2))

    def render_piecewise_kick(self, duration_sec: float, double_time: bool = False) -> tuple[np.ndarray, np.ndarray]:
        """Returns (audio_mono_float64, k_vis_curve) for duration_sec."""
        n = max(1, int(round(duration_sec * self.sr)))
        t = np.arange(n, dtype=np.float64) / self.sr
        x_beats = t * (self.bpm / 60.0)
        r = np.mod(2.0 * x_beats if double_time else x_beats, 1.0)
        k_vis = self.eval_kick_curve(x_beats, double_time=double_time)

        f_inst = self.f_root_hz + 185.0 * np.exp(-24.0 * r)
        phase = 2.0 * np.pi * np.cumsum(f_inst) / self.sr
        env_punch = np.where(r < 0.55, np.exp(-6.5 * r), 0.0)
        w = np.clip((r - 0.55) / 0.45, 0.0, 1.0)
        env_rev = np.where(r >= 0.55, np.sin(np.pi * w) ** 1.5, 0.0)
        raw = env_punch * np.sin(phase) + 0.85 * env_rev * np.tanh(2.4 * np.sin(phase))
        return np.tanh(1.35 * raw), k_vis

    def eval_lift_drop_loop_curve(self, x_beats: np.ndarray, mode: str = "phrygian") -> np.ndarray:
        """
        pwdQ_4k7HUM equation:
        y = scale(floor(4x) - 7) for x < 2 (lift)
        y = -1 - 23 * sin^2(pi*(x-2)/2) for 2 <= x < 3 (drop)
        y = -24 + 12 * sin^2(pi*(x-3)) for 3 <= x < 4 (loop)
        """
        scale = self.SCALE_SEMITONES.get(mode, self.SCALE_SEMITONES["phrygian"])
        xm = np.mod(x_beats, 4.0)
        idx = np.clip(np.floor(4.0 * xm).astype(int), 0, 7)
        y_lift = scale[idx] - 7.0
        y_drop = -1.0 - 23.0 * (np.sin(np.pi * (xm - 2.0) / 2.0) ** 2)
        y_loop = -24.0 + 12.0 * (np.sin(np.pi * (xm - 3.0)) ** 2)
        return np.where(xm < 2.0, y_lift, np.where(xm < 3.0, y_drop, y_loop))

    def render_lift_drop_loop_synth(self, duration_sec: float, mode: str = "phrygian") -> tuple[np.ndarray, np.ndarray]:
        """Synthesizes the pwdQ_4k7HUM lift-drop-loop hook with FM + PWM bite."""
        n = max(1, int(round(duration_sec * self.sr)))
        t = np.arange(n, dtype=np.float64) / self.sr
        x_beats = t * (self.bpm / 60.0)
        y_semi = self.eval_lift_drop_loop_curve(x_beats, mode=mode)
        f_inst = (self.f_root_hz * 4.0) * (2.0 ** (y_semi / 12.0))
        phase = 2.0 * np.pi * np.cumsum(f_inst) / self.sr
        xm = np.mod(x_beats, 4.0)
        step_phase = np.mod(4.0 * xm, 1.0)
        env = np.where(xm < 2.0, np.exp(-3.2 * step_phase), 0.92)
        mod_index = np.where(xm < 2.0, 2.2 * np.exp(-6.0 * step_phase), 1.4)
        sig = env * np.sin(phase + mod_index * np.sin(2.0 * phase))
        return np.tanh(1.6 * sig), y_semi

    def render_dx7_fm_bell(self, freqs_hz: np.ndarray, note_dur_sec: float, ratio: float = 2.0, mod_index: float = 4.5) -> np.ndarray:
        """EatP2sg5Rw4 #5: y = sin(2*pi*f*t + I*exp(-t/tau)*sin(2*pi*f*ratio*t))."""
        n_note = max(1, int(round(note_dur_sec * self.sr)))
        out = []
        for f_c in freqs_hz:
            t = np.arange(n_note, dtype=np.float64) / self.sr
            env_c = (1.0 - np.exp(-t / 0.003)) * np.exp(-t / (0.45 * note_dur_sec + 0.08))
            env_m = mod_index * np.exp(-t / (0.18 * note_dur_sec + 0.03))
            wave = env_c * np.sin(2.0 * np.pi * f_c * t + env_m * np.sin(2.0 * np.pi * (f_c * ratio) * t))
            out.append(wave)
        return np.concatenate(out) if out else np.zeros(0, dtype=np.float64)

    def render_exp_octave_wobble(self, duration_sec: float, wobbles_per_beat: float = 2.0, f0_hz: float = 70.0, alpha: float = 5.5) -> tuple[np.ndarray, np.ndarray]:
        """EatP2sg5Rw4 #4: fc(t) = 70 * 2^(5.5 * sin^2(pi * r * t))."""
        n = max(1, int(round(duration_sec * self.sr)))
        t = np.arange(n, dtype=np.float64) / self.sr
        x_beats = t * (self.bpm / 60.0)
        sin2 = np.sin(np.pi * wobbles_per_beat * x_beats) ** 2
        fc_hz = f0_hz * (2.0 ** (alpha * sin2))
        p1 = np.mod(self.f_root_hz * t, 1.0) * 2.0 - 1.0
        p2 = np.mod(self.f_root_hz * 1.006 * t + 0.25, 1.0) * 2.0 - 1.0
        pwm = np.sign(np.sin(2.0 * np.pi * (self.f_root_hz * 2.0) * t) - np.cos(np.pi * (0.5 + 0.35 * np.sin(2.0 * np.pi * 1.5 * t))))
        raw = 0.45 * (p1 + p2) + 0.30 * pwm
        out = np.zeros_like(raw)
        ic1eq = 0.0
        ic2eq = 0.0
        k_res = 0.65
        for i in range(n):
            g = np.tan(np.pi * min(fc_hz[i], 0.42 * self.sr) / self.sr)
            a1 = 1.0 / (1.0 + g * (g + k_res))
            a2 = g * a1
            v3 = raw[i] - ic2eq
            v1 = a1 * ic1eq + a2 * v3
            v2 = ic2eq + g * v1
            ic1eq = 2.0 * v1 - ic1eq
            ic2eq = 2.0 * v2 - ic2eq
            out[i] = v2 + 0.35 * v1
        return np.tanh(1.5 * out), fc_hz

    @staticmethod
    def eval_planck_chord_curve(x_beats: np.ndarray) -> np.ndarray:
        """GVVuMNPhoV4 equation: B(u) = 8*u^3 / (exp(2*u) - 1), u = mod(x, 4), n(x) = floor(6*B(u))."""
        u = np.clip(np.mod(x_beats, 4.0), 1e-4, 4.0)
        b_u = (8.0 * (u ** 3)) / (np.exp(2.0 * u) - 1.0)
        return np.floor(6.0 * b_u)

    @staticmethod
    def eval_gravity_rod_drop_curve(x_beats: np.ndarray) -> np.ndarray:
        """bBGPBCWVl-M equation: s(t) = 1/2 g t^2 => y = -floor(2 * mod(x, 2)^2)."""
        xm = np.mod(x_beats, 2.0)
        return -np.floor(2.0 * (xm ** 2))

    @staticmethod
    def apply_quadratic_tape_stop(audio: np.ndarray, sr: int, stop_duration_sec: float = 0.68) -> np.ndarray:
        """EatP2sg5Rw4 #1: speed(t) = (1 - t/T)^2 phase-warped resampling."""
        n_stop = min(audio.shape[-1], int(round(stop_duration_sec * sr)))
        if n_stop < 32:
            return audio
        out = audio.copy()
        t = np.linspace(0.0, 1.0, n_stop, dtype=np.float64)
        src_idx = (t - (t ** 2) + (t ** 3) / 3.0) * (n_stop - 1)
        idx_floor = np.clip(np.floor(src_idx).astype(int), 0, n_stop - 2)
        frac = src_idx - idx_floor
        if out.ndim == 2:
            tail = out[:, -n_stop:]
            warped = (1.0 - frac[None, :]) * tail[:, idx_floor] + frac[None, :] * tail[:, idx_floor + 1]
            env = (np.linspace(1.0, 0.0, n_stop) ** 0.5)[None, :]
            out[:, -n_stop:] = warped * env
        else:
            tail = out[-n_stop:]
            warped = (1.0 - frac) * tail[idx_floor] + frac * tail[idx_floor + 1]
            env = np.linspace(1.0, 0.0, n_stop) ** 0.5
            out[-n_stop:] = warped * env
        return out

    @classmethod
    def build_bar_math_telemetry(cls, bar_idx: int, total_bars: int, is_drop: bool, is_breakdown: bool, double_time: bool = False) -> dict:
        """Constructs per-bar symbolic math telemetry for live HUD and Shorts rendering."""
        if bar_idx < 2:
            st = cls.STAGE_MATRIX[0]
            voices = ["K"]
            pol = "ivory_paper"
            sec = "1. THE SUB KICK"
        elif bar_idx < 4:
            st = cls.STAGE_MATRIX[2]
            voices = ["K", "H"]
            pol = "ivory_paper"
            sec = "+ HI-HAT & BREAK"
        elif is_breakdown:
            st = cls.STAGE_MATRIX[6] if (bar_idx % 4 == 3) else cls.STAGE_MATRIX[3]
            voices = ["C", "L"]
            pol = "ivory_paper"
            sec = "HARMONIC QUBO BREAKDOWN"
        elif is_drop and double_time:
            st = cls.STAGE_MATRIX[9]
            voices = ["K", "H", "C", "L", "L_oct"]
            pol = "dark_neon"
            sec = "FINAL DROP (2X CLIMAX)"
        elif is_drop:
            st = cls.STAGE_MATRIX[8] if (bar_idx % 2 == 1) else cls.STAGE_MATRIX[7]
            voices = ["K", "H", "C", "L"]
            pol = "dark_neon"
            sec = "THE DROP"
        else:
            st = cls.STAGE_MATRIX[5]
            voices = ["K", "H", "C"]
            pol = "dark_neon"
            sec = "OCTAVE WOBBLE"

        return {
            "bar_index": int(bar_idx),
            "total_bars": int(total_bars),
            "section": sec,
            "polarity": pol,
            "active_voices": voices,
            "stage_label": st[0],
            "latex_formula": st[1],
            "subtitle": st[2],
            "wobble_rate": float(1 + (bar_idx % 4)),
            "double_time": bool(double_time),
        }

