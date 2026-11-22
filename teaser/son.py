#!/usr/bin/env python3
"""Bande son 100 % générée (numpy) calée sur la timeline de config.js.
- montée de régime 2-temps sur le hook, impact au « STOP. »
- pulsation basse / kick 140 BPM pendant tout le corps
- whoosh sur chaque transition, griffe, compteur qui tique, impact grave sur le -20 %
"""
import json, sys, wave
import numpy as np

SR = 48000
cfg = json.load(open(sys.argv[1])); out = sys.argv[2]
T = cfg["timeline"]; DUR = cfg["duree"]; BEAT = 60 / cfg["bpm"]
N = int(DUR * SR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(3)


def tt(d): return np.arange(int(d * SR)) / SR


def put(sig, t0, g=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N: return
    j = min(N, i + len(sig)); s = sig[:j - i] * g
    L[i:j] += s * (1 - max(0, pan)); R[i:j] += s * (1 + min(0, pan))


def onepole(x, a):
    y = np.empty_like(x); acc = 0.0
    a = np.broadcast_to(a, x.shape)
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc); y[i] = acc
    return y


def env(n, att, rel):
    e = np.ones(n); a = max(1, int(att * SR)); r = max(1, int(rel * SR))
    e[:a] = np.linspace(0, 1, a); e[-r:] *= np.linspace(1, 0, r) ** 2
    return e


# --- montée 2-temps : impulsions d'allumage à fréquence croissante, résonance d'échappement
def deux_temps(d):
    t = tt(d); f = 55 + 260 * (t / d) ** 1.6                  # régime qui monte
    ph = np.cumsum(f) / SR
    pulses = np.exp(-((ph % 1.0) * 9))                       # « brap »
    body = np.sin(2 * np.pi * ph * 2) * 0.6 + np.sin(2 * np.pi * ph * 3.01) * 0.3
    noise = onepole(rng.standard_normal(len(t)), 0.25) * 0.5
    x = (body + noise) * pulses
    x = np.tanh(3.0 * x)                                      # saturation
    return x * env(len(t), 0.03, 0.04) * np.linspace(0.6, 1, len(t))


def kick(d=0.45, f0=150, f1=42):
    t = tt(d); f = f1 + (f0 - f1) * np.exp(-t * 35)
    return np.tanh(1.8 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7))


def sub(d, f=41.2):
    t = tt(d); return np.sin(2 * np.pi * f * t) * env(len(t), 0.005, d * 0.8)


def hat(d=0.04):
    t = tt(d); x = rng.standard_normal(len(t)); x = x - onepole(x, 0.5)
    return x * np.exp(-t * 110)


def whoosh(d=0.45, up=True):
    t = tt(d); k = t / d
    a = (0.02 + 0.45 * (k if up else 1 - k) ** 2)
    x = onepole(rng.standard_normal(len(t)), a)
    return x * np.sin(np.pi * k) ** 1.3 * 2.2


def impact(d=1.6, deep=True):
    t = tt(d); f = (34 if deep else 55) + 140 * np.exp(-t * 18)
    b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (2.2 if deep else 4))
    n = onepole(rng.standard_normal(len(t)), 0.3) * np.exp(-t * 14)
    return np.tanh(2.2 * (b + 0.7 * n))


def griffe(d=0.22):
    t = tt(d); x = rng.standard_normal(len(t)); x = x - onepole(x, 0.08)
    return x * np.exp(-t * 18) * (1 + 0.6 * np.sin(2 * np.pi * 60 * t))


def tick(f=2600, d=0.03):
    t = tt(d); return np.sin(2 * np.pi * f * t) * np.exp(-t * 160)


def riser(d):
    t = tt(d); f = 200 + 1800 * (t / d) ** 2
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3 + onepole(rng.standard_normal(len(t)), 0.05 + 0.5 * t / d)) * (t / d) ** 2


# --- HOOK
put(deux_temps(T["impactHook"] + 0.05), 0.0, 0.8)
put(impact(1.4), T["impactHook"], 1.0)
put(rng.standard_normal(int(0.25 * SR)) * np.exp(-tt(0.25) * 16), T["impactHook"], 0.5)
put(impact(0.6, deep=False), T["ligne2Hook"], 0.55)
put(impact(0.5, deep=False), T["ligne2Hook"] + 0.14, 0.45)
put(whoosh(0.5), T["tension"] - 0.42, 0.5)

# --- pulsation 140 BPM (de la tension à l'arrivée du titre final)
beat_end = T["fige"] - 0.2
b = T["tension"]; i = 0
while b < beat_end:
    quiet = T["badge"] - 0.35 <= b < T["badge"]              # micro-blanc avant le -20 %
    if not quiet:
        put(kick(), b, 0.85)
        put(sub(BEAT * 0.9), b, 0.35)
        put(hat(), b + BEAT / 2, 0.22, pan=0.3 if i % 2 else -0.3)
        if i % 2 == 1: put(onepole(rng.standard_normal(int(0.18 * SR)), 0.35) * np.exp(-tt(0.18) * 22), b, 0.4)  # clap
    b += BEAT; i += 1

# --- tension : whoosh à chaque cut de pièce
for k in range(8):
    put(whoosh(0.22, up=False), T["tension"] + k * BEAT, 0.28, pan=-0.4 if k % 2 else 0.4)

# --- révélation
put(whoosh(0.4), T["revelation"] - 0.05, 0.45)
put(griffe(), T["griffe"], 0.9)
c0, c1 = T["compteur"]
n = 18
for k in range(n):
    tk = c0 + (c1 - c0) * (1 - (1 - k / n) ** 2.2)
    put(tick(2200 + 40 * k), tk, 0.35)
put(riser(0.55), T["badge"] - 0.55, 0.5)
put(impact(2.0), T["badge"], 1.1)
put(impact(0.6, deep=False), T["surTout"], 0.4)

# --- urgence : tic du compte à rebours chaque seconde
put(whoosh(0.4), T["urgence"] - 0.2, 0.45)
s = T["urgence"] + 1
while s < T["fin"]:
    put(tick(1500, 0.05), s, 0.5); s += 1
put(impact(0.7, deep=False), T["dates"], 0.45)
put(impact(0.9), T["jours"], 0.6)

# --- fin
put(riser(0.6), T["fin"] - 0.6, 0.45)
put(impact(2.2), T["fin"], 1.1)
put(impact(0.8, deep=False), T["fin"] + 0.16, 0.6)
put(whoosh(0.5), T["fin"] + 1.5, 0.35)                     # reflet sur le site
put(impact(1.8), T["fige"] - 0.2, 0.55)                    # dernier coup, puis résonance

mix = np.stack([L, R], 1)
fade = int(0.6 * SR); mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.9
pcm = (mix * 32767).astype(np.int16)
with wave.open(out, "w") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("Son :", out)
