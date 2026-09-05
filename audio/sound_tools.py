"""sound_tools.py — a tiny, dependency-free WAV sound effect synthesizer.

Generates short one-shot sound effects as plain PCM .wav files using only the
standard library (no numpy, no audio assets to source). Run this file
directly to (re)generate the game's sound effects.
"""

import array
import math
import random
import wave

SAMPLE_RATE = 44100


def _envelope(i, n_samples, curve):
    """A simple decaying envelope: loud at i=0, fading to 0 by i=n_samples."""
    t = i / n_samples
    return max(0.0, (1 - t) ** curve)


def _write_wav(path, samples):
    clipped = array.array("h", (max(-32767, min(32767, s)) for s in samples))
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(clipped.tobytes())


def synthesize_footstep(path, duration=0.09, volume=0.5, seed=1):
    """A soft crunch: filtered noise with a fast decay, like a twig underfoot."""
    rng = random.Random(seed)
    n_samples = int(SAMPLE_RATE * duration)
    samples = []
    filtered = 0.0
    alpha = 0.35  # low-pass smoothing so the noise sounds crunchy, not harsh
    for i in range(n_samples):
        raw = rng.uniform(-1, 1)
        filtered = alpha * raw + (1 - alpha) * filtered
        sample = filtered * _envelope(i, n_samples, curve=2.2) * volume
        samples.append(int(sample * 32767))
    _write_wav(path, samples)


def synthesize_bump(path, duration=0.16, frequency=110, volume=0.6, seed=2):
    """A gentle low thud: a soft tone plus a touch of noise, decaying quickly."""
    rng = random.Random(seed)
    n_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        tone = math.sin(2 * math.pi * frequency * t)
        noise = rng.uniform(-1, 1) * 0.15
        sample = (tone + noise) * _envelope(i, n_samples, curve=3.5) * volume
        samples.append(int(sample * 32767))
    _write_wav(path, samples)


def synthesize_engine_rumble(path, duration=0.08, frequency=70, volume=0.6, seed=3):
    """A rounded low chug: a low tone plus filtered noise, decaying gently
    (no sharp snap like the bump sound). Triggered rapidly via the same
    footstep-cadence mechanism (just a much shorter interval while riding),
    so many of these back-to-back read as a continuous engine rumble."""
    rng = random.Random(seed)
    n_samples = int(SAMPLE_RATE * duration)
    samples = []
    filtered_noise = 0.0
    alpha = 0.5
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        tone = math.sin(2 * math.pi * frequency * t)
        raw_noise = rng.uniform(-1, 1)
        filtered_noise = alpha * raw_noise + (1 - alpha) * filtered_noise
        sample = (tone * 0.75 + filtered_noise * 0.35) * _envelope(i, n_samples, curve=1.6) * volume
        samples.append(int(sample * 32767))
    _write_wav(path, samples)


def synthesize_laser_shot(path, duration=0.12, start_freq=1200, end_freq=300, volume=0.5, seed=4):
    """The player's laser: a bright tone sweeping quickly downward in pitch
    (a classic "pew"), fast decay."""
    n_samples = int(SAMPLE_RATE * duration)
    samples = []
    phase = 0.0
    for i in range(n_samples):
        t = i / n_samples
        freq = start_freq + (end_freq - start_freq) * t
        phase += 2 * math.pi * freq / SAMPLE_RATE
        tone = math.sin(phase)
        sample = tone * _envelope(i, n_samples, curve=1.8) * volume
        samples.append(int(sample * 32767))
    _write_wav(path, samples)


def synthesize_enemy_laser_shot(path, duration=0.14, start_freq=700, end_freq=150, volume=0.5, seed=5):
    """The Swarm's laser: the same descending-sweep idea as the player's,
    pitched lower with a touch of noise mixed in so it reads as a
    different, more menacing weapon rather than just a recolor."""
    rng = random.Random(seed)
    n_samples = int(SAMPLE_RATE * duration)
    samples = []
    phase = 0.0
    for i in range(n_samples):
        t = i / n_samples
        freq = start_freq + (end_freq - start_freq) * t
        phase += 2 * math.pi * freq / SAMPLE_RATE
        tone = math.sin(phase)
        noise = rng.uniform(-1, 1) * 0.2
        sample = (tone * 0.85 + noise) * _envelope(i, n_samples, curve=1.8) * volume
        samples.append(int(sample * 32767))
    _write_wav(path, samples)


def synthesize_explosion(path, duration=0.35, volume=0.7, seed=6):
    """A ship exploding: filtered noise whose low-pass tightens as it
    decays (a bright crack at impact, a duller rumble as it fades) —
    bigger and longer than the bump sound."""
    rng = random.Random(seed)
    n_samples = int(SAMPLE_RATE * duration)
    samples = []
    filtered = 0.0
    for i in range(n_samples):
        t = i / n_samples
        alpha = 0.6 - 0.4 * t  # starts brighter, gets duller as the low-pass tightens
        raw = rng.uniform(-1, 1)
        filtered = alpha * raw + (1 - alpha) * filtered
        sample = filtered * _envelope(i, n_samples, curve=2.0) * volume
        samples.append(int(sample * 32767))
    _write_wav(path, samples)


if __name__ == "__main__":
    synthesize_footstep("footstep.wav")
    synthesize_bump("bump.wav")
    synthesize_engine_rumble("engine.wav")
    synthesize_laser_shot("laser.wav")
    synthesize_enemy_laser_shot("enemy_laser.wav")
    synthesize_explosion("explosion.wav")
    print("Wrote footstep.wav, bump.wav, engine.wav, laser.wav, enemy_laser.wav, and explosion.wav")
