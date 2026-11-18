#!/usr/bin/env python3
"""Génère les effets sonores de base dans montage/sfx/.

Pour utiliser tes propres sons tendance TikTok, remplace simplement un fichier
par le tien en gardant le même nom (whoosh.wav, pop.wav, boom.wav, ding.wav,
cash.wav, swipe.wav), ou ajoute-en de nouveaux et cite-les dans effets.json.
"""
import os, wave
import numpy as np

SR = 48000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sfx")
rng = np.random.default_rng(7)


def env(n, a, r):
    e = np.ones(n)
    a, r = int(a * SR), int(r * SR)
    e[:a] = np.linspace(0, 1, a)
    e[-r:] *= np.linspace(1, 0, r) ** 2
    return e


def lowpass(x, alpha):
    y = np.zeros_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc += alpha[i] * (v - acc); y[i] = acc
    return y


def whoosh(d=0.55):
    n = int(d * SR); t = np.linspace(0, 1, n)
    sweep = 0.02 + 0.25 * np.sin(np.pi * t) ** 2
    x = lowpass(rng.standard_normal(n), sweep)
    return x * np.sin(np.pi * t) ** 1.5


def swipe(d=0.25):
    n = int(d * SR); t = np.linspace(0, 1, n)
    x = lowpass(rng.standard_normal(n), 0.05 + 0.5 * t)
    return x * env(n, 0.01, 0.15)


def pop(d=0.12):
    n = int(d * SR); t = np.arange(n) / SR
    f = 900 * np.exp(-t * 30) + 250
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 35)


def boom(d=1.2):
    n = int(d * SR); t = np.arange(n) / SR
    f = 110 * np.exp(-t * 3) + 38
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.8)
    hit = lowpass(rng.standard_normal(n), np.full(n, 0.08)) * np.exp(-t * 25)
    return np.tanh(1.8 * (body + 0.8 * hit))


def ding(d=1.0, f0=1568):
    t = np.arange(int(d * SR)) / SR
    x = sum(a * np.sin(2 * np.pi * f0 * m * t) * np.exp(-t * k)
            for a, m, k in [(1, 1, 4), (0.5, 2.76, 6), (0.25, 5.4, 9)])
    return x


def cash():
    click = np.zeros(int(0.08 * SR)); click[:300] = rng.standard_normal(300) * np.linspace(1, 0, 300)
    gap = np.zeros(int(0.04 * SR))
    b1, b2 = ding(0.9, 2093), ding(0.9, 2637)
    tail = np.zeros(len(b1) + int(0.07 * SR))
    tail[:len(b1)] += b1; tail[int(0.07 * SR):] += b2 * 0.9
    return np.concatenate([click, gap, tail])


def save(name, x, gain=0.8):
    x = x / (np.max(np.abs(x)) + 1e-9) * gain
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + ".wav"), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in [("whoosh", whoosh), ("swipe", swipe), ("pop", pop), ("boom", boom),
                     ("ding", ding), ("cash", cash)]:
        path = os.path.join(OUT, name + ".wav")
        if os.path.exists(path):
            print("garde", path); continue
        save(name, fn()); print("créé", path)
