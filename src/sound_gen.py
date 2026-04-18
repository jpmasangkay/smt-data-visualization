"""Procedural audio generator for Persona 4 Data Explorer.

Generates atmospheric ambient music and UI sound effects using numpy,
saved as WAV files in assets/sounds/.
"""
from __future__ import annotations

import os
import struct
import wave

import numpy as np


SAMPLE_RATE = 44100


def _save_wav(path: str, samples: np.ndarray, sr: int = SAMPLE_RATE) -> None:
    """Save a float32 array [-1, 1] as a 16-bit stereo WAV."""
    # Clamp and convert to int16
    samples = np.clip(samples, -1.0, 1.0)
    int_samples = (samples * 32767).astype(np.int16)
    with wave.open(path, "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int_samples.tobytes())


def _generate_ambient(duration: float = 45.0) -> np.ndarray:
    """Generate a dark, atmospheric ambient loop.

    Mix of:
    - Deep sub-bass drone (40-60 Hz)
    - Eerie mid-range pad with slow filter sweep
    - Distant wind/noise texture
    - Sparse high-pitched tones (like distant bells)
    """
    sr = SAMPLE_RATE
    n = int(duration * sr)
    t = np.linspace(0, duration, n, dtype=np.float32)

    # ── Sub-bass drone (40Hz fundamental + 60Hz harmonic) ──
    drone_freq = 40.0 + 5.0 * np.sin(2 * np.pi * 0.03 * t)  # slow wobble
    drone_phase = np.cumsum(2 * np.pi * drone_freq / sr)
    drone = 0.15 * np.sin(drone_phase)
    drone += 0.08 * np.sin(drone_phase * 1.5)  # 60Hz harmonic
    drone += 0.04 * np.sin(drone_phase * 2.0)  # 80Hz harmonic

    # ── Eerie pad (layered detuned oscillators around 120-180 Hz) ──
    pad_freqs = [110, 113, 165, 168, 220, 223]
    pad = np.zeros(n, dtype=np.float32)
    for i, f in enumerate(pad_freqs):
        # Each voice has slow vibrato
        vib = 1.0 + 0.003 * np.sin(2 * np.pi * (0.1 + i * 0.02) * t)
        phase = np.cumsum(2 * np.pi * f * vib / sr)
        # Slow amplitude envelope using sine
        amp_env = 0.5 + 0.5 * np.sin(2 * np.pi * (0.05 + i * 0.01) * t + i)
        pad += 0.025 * amp_env * np.sin(phase)

    # ── Wind texture (shaped noise) ──
    rng = np.random.RandomState(42)
    noise = rng.normal(0, 1, n).astype(np.float32)
    # Simple low-pass filter via running average
    kernel_size = 200
    kernel = np.ones(kernel_size) / kernel_size
    wind_raw = np.convolve(noise, kernel, mode="same")
    # Amplitude modulation for gusts
    wind_env = 0.4 + 0.6 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * t)) * \
                              (0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t + 1.5))
    wind = 0.06 * wind_raw * wind_env

    # ── Ethereal high tones (sparse bells / chimes) ──
    bells = np.zeros(n, dtype=np.float32)
    bell_times = [3.5, 8.2, 15.0, 21.5, 28.0, 35.0, 40.0]
    bell_freqs = [880, 1320, 660, 1100, 990, 770, 1210]
    for bt, bf in zip(bell_times, bell_freqs):
        start = int(bt * sr)
        bell_dur = int(3.0 * sr)
        if start + bell_dur > n:
            bell_dur = n - start
        bt_t = np.arange(bell_dur, dtype=np.float32) / sr
        # Exponential decay
        envelope = np.exp(-bt_t * 1.5) * 0.03
        bell_signal = envelope * np.sin(2 * np.pi * bf * bt_t)
        bell_signal += envelope * 0.3 * np.sin(2 * np.pi * bf * 2.01 * bt_t)
        bells[start:start + bell_dur] += bell_signal

    # ── Reverse reverb sweeps (rising swells) ──
    sweeps = np.zeros(n, dtype=np.float32)
    sweep_times = [6.0, 18.0, 30.0, 42.0]
    for st in sweep_times:
        start = int(st * sr)
        sweep_dur = int(2.5 * sr)
        if start + sweep_dur > n:
            sweep_dur = n - start
        if sweep_dur <= 0:
            continue
        st_t = np.arange(sweep_dur, dtype=np.float32) / sr
        # Rising envelope
        rise = (st_t / (sweep_dur / sr)) ** 2
        fade = np.exp(-st_t * 0.8)
        env = rise * fade * 0.03
        sweep_sig = env * np.sin(2 * np.pi * 220 * st_t)
        sweeps[start:start + sweep_dur] += sweep_sig

    # ── Mix all layers ──
    mono = drone + pad + wind + bells + sweeps

    # Fade in/out (2 seconds each)
    fade_samples = int(2.0 * sr)
    fade_in = np.linspace(0, 1, fade_samples, dtype=np.float32)
    fade_out = np.linspace(1, 0, fade_samples, dtype=np.float32)
    mono[:fade_samples] *= fade_in
    mono[-fade_samples:] *= fade_out

    # Make it loop-friendly: crossfade last 2s with first 2s
    xfade = int(2.0 * sr)
    for i in range(xfade):
        blend = i / xfade
        mono[i] = mono[i] * blend + mono[-(xfade - i)] * (1 - blend)

    # Stereo with subtle spatial widening
    mono2 = np.roll(mono, int(0.015 * sr))  # ~15ms delay for width
    left = mono * 0.8 + mono2 * 0.2
    right = mono2 * 0.8 + mono * 0.2

    # Interleave stereo channels
    stereo = np.empty(n * 2, dtype=np.float32)
    stereo[0::2] = left
    stereo[1::2] = right

    return stereo


def _generate_tone(
    freq: float,
    duration: float,
    attack: float = 0.01,
    decay: float = 0.3,
    volume: float = 0.3,
    harmonics: list[tuple[float, float]] | None = None,
) -> np.ndarray:
    """Generate a simple tonal sound effect."""
    sr = SAMPLE_RATE
    n = int(duration * sr)
    t = np.arange(n, dtype=np.float32) / sr

    # Main oscillator
    sig = np.sin(2 * np.pi * freq * t)

    # Add harmonics
    if harmonics:
        for h_ratio, h_amp in harmonics:
            sig += h_amp * np.sin(2 * np.pi * freq * h_ratio * t)

    # ADSR envelope
    attack_n = int(attack * sr)
    decay_n = int(decay * sr)
    env = np.ones(n, dtype=np.float32)
    if attack_n > 0:
        env[:attack_n] = np.linspace(0, 1, attack_n)
    if decay_n > 0 and decay_n < n:
        env[-decay_n:] = np.linspace(1, 0, decay_n)

    mono = sig * env * volume

    # Stereo
    stereo = np.empty(n * 2, dtype=np.float32)
    stereo[0::2] = mono
    stereo[1::2] = mono
    return stereo


def _generate_panel_open() -> np.ndarray:
    """Rising chime — two quick ascending tones."""
    sr = SAMPLE_RATE
    dur = 0.35
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr

    # Two ascending tones (C5 → E5)
    freq1 = 523.25  # C5
    freq2 = 659.25  # E5
    split = n // 2

    sig = np.zeros(n, dtype=np.float32)
    # First tone
    t1 = np.arange(split, dtype=np.float32) / sr
    env1 = np.exp(-t1 * 8) * 0.25
    sig[:split] += env1 * np.sin(2 * np.pi * freq1 * t1)
    # Second tone
    t2 = np.arange(n - split, dtype=np.float32) / sr
    env2 = np.exp(-t2 * 6) * 0.3
    sig[split:] += env2 * np.sin(2 * np.pi * freq2 * t2)
    sig[split:] += env2 * 0.3 * np.sin(2 * np.pi * freq2 * 2.0 * t2)

    stereo = np.empty(n * 2, dtype=np.float32)
    stereo[0::2] = sig
    stereo[1::2] = sig
    return stereo


def _generate_panel_close() -> np.ndarray:
    """Descending soft tone — E5 → C5."""
    sr = SAMPLE_RATE
    dur = 0.3
    n = int(dur * sr)

    # Descending sweep
    t = np.arange(n, dtype=np.float32) / sr
    freq = 659.25 - (659.25 - 392.0) * (t / dur)  # E5 → G4
    phase = np.cumsum(2 * np.pi * freq / sr)
    env = np.exp(-t * 5) * 0.2
    sig = env * np.sin(phase)

    stereo = np.empty(n * 2, dtype=np.float32)
    stereo[0::2] = sig
    stereo[1::2] = sig
    return stereo


def _generate_interact() -> np.ndarray:
    """Gentle bell chime for building interaction."""
    sr = SAMPLE_RATE
    dur = 0.5
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float32) / sr

    freq = 880.0  # A5
    env = np.exp(-t * 4) * 0.25
    sig = env * np.sin(2 * np.pi * freq * t)
    sig += env * 0.4 * np.sin(2 * np.pi * freq * 2.003 * t)  # detuned harmonic
    sig += env * 0.2 * np.sin(2 * np.pi * freq * 3.01 * t)
    sig += env * 0.1 * np.sin(2 * np.pi * freq * 5.02 * t)

    stereo = np.empty(n * 2, dtype=np.float32)
    stereo[0::2] = sig
    stereo[1::2] = sig
    return stereo


def generate_all_sounds(output_dir: str) -> dict[str, str]:
    """Generate all sound files and return a map of name → path."""
    os.makedirs(output_dir, exist_ok=True)
    files: dict[str, str] = {}

    print("  Generating ambient drone (~45s loop)...")
    ambient = _generate_ambient(45.0)
    path = os.path.join(output_dir, "ambient.wav")
    _save_wav(path, ambient)
    files["ambient"] = path

    print("  Generating panel open chime...")
    panel_open = _generate_panel_open()
    path = os.path.join(output_dir, "panel_open.wav")
    _save_wav(path, panel_open)
    files["panel_open"] = path

    print("  Generating panel close tone...")
    panel_close = _generate_panel_close()
    path = os.path.join(output_dir, "panel_close.wav")
    _save_wav(path, panel_close)
    files["panel_close"] = path

    print("  Generating interact chime...")
    interact = _generate_interact()
    path = os.path.join(output_dir, "interact.wav")
    _save_wav(path, interact)
    files["interact"] = path

    print(f"  ✓ All sounds saved to {output_dir}")
    return files


if __name__ == "__main__":
    from .constants import ASSETS_DIR
    sounds_dir = os.path.join(ASSETS_DIR, "sounds")
    generate_all_sounds(sounds_dir)
