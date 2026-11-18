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


def clic():
    """Clic de souris : deux petits claquements secs."""
    n = int(0.12 * SR); x = np.zeros(n); t = np.arange(300) / SR
    for off, g in [(0, 1.0), (int(0.045 * SR), 0.6)]:
        burst = rng.standard_normal(300) * np.exp(-t * 900) + np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 600)
        x[off:off + 300] += g * burst
    return x


def beat(bpm=140, bars=8):
    """Instru type phonk/trap : 808, charley, clap, nappe sombre (boucle)."""
    spb = 60 / bpm; step = spb / 4; n = int(bars * 16 * step * SR)
    out = np.zeros(n)
    def put(sig, t0, g=1.0):
        i = int(t0 * SR); j = min(n, i + len(sig)); out[i:j] += g * sig[:j - i]
    tt = lambda d: np.arange(int(d * SR)) / SR
    def kick808(f=48, d=0.9):
        t = tt(d); fr = f + 120 * np.exp(-t * 40)
        return np.tanh(2.2 * np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 3))
    def hat(d=0.05):
        t = tt(d); x = rng.standard_normal(len(t)); x = x - lowpass(x, np.full(len(t), 0.4))
        return x * np.exp(-t * 90)
    def clap(d=0.25):
        t = tt(d); x = lowpass(rng.standard_normal(len(t)), np.full(len(t), 0.35))
        e = sum(np.exp(-np.clip(t - o, 0, None) * 60) * (t >= o) for o in (0, 0.012, 0.024))
        return x * e
    def cowbell(f, d=0.35):
        t = tt(d)
        return (np.sign(np.sin(2 * np.pi * f * t)) + np.sign(np.sin(2 * np.pi * f * 1.48 * t))) * np.exp(-t * 9) * 0.5
    notes = [0, 0, 3, 0, 7, 5, 3, 2]       # mélodie mineure (demi-tons)
    root = 554.37                          # C#5
    kick_pat = [0, 6, 10]                  # pas sur 16
    for b in range(bars):
        base = b * 16 * step
        for k in kick_pat:
            put(kick808(46 if b % 4 < 2 else 41), base + k * step, 0.9)
        put(clap(), base + 4 * step, 0.5); put(clap(), base + 12 * step, 0.5)
        for h in range(16):
            put(hat(), base + h * step, 0.18 if h % 2 else 0.25)
        if b % 2 == 1:
            for r in range(4):
                put(hat(0.03), base + 14 * step + r * step / 2, 0.15)
        for q in range(4):
            semi = notes[(b * 4 + q) % len(notes)]
            put(cowbell(root * 2 ** (semi / 12)), base + q * 4 * step + (2 * step if q % 2 else 0), 0.22)
    return np.tanh(out * 1.2)


def save(name, x, gain=0.8):
    x = x / (np.max(np.abs(x)) + 1e-9) * gain
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + ".wav"), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in [("whoosh", whoosh), ("swipe", swipe), ("pop", pop), ("boom", boom),
                     ("ding", ding), ("cash", cash), ("clic", clic)]:
        path = os.path.join(OUT, name + ".wav")
        if os.path.exists(path):
            print("garde", path); continue
        save(name, fn()); print("créé", path)
    mus = os.path.join(os.path.dirname(OUT), "musique")
    os.makedirs(mus, exist_ok=True)
    if not os.path.exists(os.path.join(mus, "beat_lsmx.wav")):
        OUT_SAVE = OUT
        globals()["OUT"] = mus; save("beat_lsmx", beat(), 0.7); globals()["OUT"] = OUT_SAVE
        print("créé", os.path.join(mus, "beat_lsmx.wav"))
