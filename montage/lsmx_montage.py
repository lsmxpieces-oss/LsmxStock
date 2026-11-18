#!/usr/bin/env python3
"""LSMX — montage automatique TikTok.

Deux modes :

1) Sans parole (style "sortie de grange") :
   python3 montage/lsmx_montage.py RUSH.mp4 -o SORTIE.mp4 \
       --hook "SORTIE DE GRANGE" --sub "YZ 250 de 1991" [--music son.mp3]

2) Voix off / face caméra (--voix) :
   python3 montage/lsmx_montage.py RUSH1.mp4 RUSH2.mp4 ... -o SORTIE.mp4 --voix \
       [--hook "50 000 € DE STOCK KTM"] [--music son.mp3] [--garder-silences]
   -> transcription automatique (Whisper), sous-titres mot par mot animés,
      coupe des silences / hésitations, musique baissée sous la voix.

Commun : 1080x1920, couleurs + netteté, zoom léger continu, barre de progression
rouge, carte de fin LSMX, son normalisé à -14 LUFS (standard TikTok).
"""
import argparse, json, os, re, subprocess, tempfile

RED = "&H0D00E8&"      # #e8000d (ASS = BGR)
YELLOW = "&H00D6FF&"   # #ffd600
FONT = "Inter ExtraBold"
END_DUR = 2.6
VOCAB = ("LSMX, Maxence, lsmx-pieces.com, KTM, SX-F, Honda CR, CR 250, CR 500, Yamaha YZ, "
         "Kawasaki KX, Suzuki RM, motocross, deux-temps, kit déco, carter, échappement.")


def run(cmd):
    subprocess.run(cmd, check=True)


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "json", path])
    return float(json.loads(out)["format"]["duration"])


def ts(t):
    t = max(t, 0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


# ---------------------------------------------------------------- préparation
def prepare(srcs, out):
    """Met tous les rushs au même format (1080x1920, 30 i/s, 48 kHz) et les colle."""
    inputs, parts = [], []
    for i, s in enumerate(srcs):
        inputs += ["-i", s]
        parts.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop=1080:1920,fps=30,setsar=1,format=yuv420p[v{i}];"
            f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}];")
    cat = "".join(f"[v{i}][a{i}]" for i in range(len(srcs)))
    fc = "".join(parts) + f"{cat}concat=n={len(srcs)}:v=1:a=1[v][a]"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-c:a", "pcm_s16le", out])


# ---------------------------------------------------------------- voix
def transcribe(path, model_size):
    import numpy as np
    from faster_whisper import WhisperModel
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1",
                          "-ar", "16000", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(audio, language="fr", word_timestamps=True, vad_filter=True,
                               initial_prompt=VOCAB)
    words = []
    for s in segs:
        for w in s.words:
            t = w.word.strip()
            if not t:
                continue
            if words and (t[0] in "'’-" or words[-1]["w"].endswith(("'", "’"))):
                words[-1]["w"] = (words[-1]["w"] + t).replace(" '", "'")
                words[-1]["e"] = w.end
            else:
                words.append({"w": t, "s": w.start, "e": w.end})
    return words


def keep_ranges(words, dur, max_gap=0.35, pad_in=0.08, pad_out=0.18):
    """Garde la parole, supprime les blancs plus longs que max_gap."""
    rng = []
    for w in words:
        a, b = max(w["s"] - pad_in, 0), min(w["e"] + pad_out, dur)
        if rng and a - rng[-1][1] <= max_gap:
            rng[-1][1] = max(rng[-1][1], b)
        else:
            rng.append([a, b])
    return rng


def cut(src, out, ranges):
    expr = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in ranges)
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-filter_complex",
         f"[0:v]select='{expr}',setpts=N/FRAME_RATE/TB[v];[0:a]aselect='{expr}',asetpts=N/SR/TB[a]",
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
         "-c:a", "pcm_s16le", out])


def remap(words, ranges):
    """Recale les temps des mots après la coupe des silences."""
    out, offset, ri = [], 0.0, 0
    starts = []
    acc = 0.0
    for a, b in ranges:
        starts.append(acc); acc += b - a
    for w in words:
        for i, (a, b) in enumerate(ranges):
            if a <= w["s"] <= b:
                d = starts[i] - a
                out.append({"w": w["w"], "s": w["s"] + d, "e": min(w["e"], b) + d})
                break
    return out


def group_words(words, max_words=3, max_chars=18):
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        txt = " ".join(x["w"] for x in cur)
        if (nxt is None or len(cur) >= max_words or len(txt) >= max_chars
                or re.search(r"[.,!?;:]$", w["w"]) or nxt["s"] - w["e"] > 0.3):
            groups.append(cur); cur = []
    return groups


def caption_events(words):
    ev = []
    clean = lambda s: re.sub(r"[.,;:]+$", "", s).upper().replace("{", "").replace("}", "")
    for g in group_words(words):
        for j, w in enumerate(g):
            start = w["s"]
            end = g[j + 1]["s"] if j + 1 < len(g) else max(w["e"], start + 0.25)
            parts = []
            for k, x in enumerate(g):
                t = clean(x["w"])
                parts.append(r"{\c" + YELLOW + r"\fscx112\fscy112}" + t + r"{\c&HFFFFFF&\fscx100\fscy100}"
                             if k == j else t)
            pop = r"{\fscx85\fscy85\t(0,90,\fscx100\fscy100)}" if j == 0 else ""
            ev.append((start, end, "Cap", pop + " ".join(parts)))
    return ev


# ---------------------------------------------------------------- titres
def build_ass(dur, hook, sub, cta, captions, end_start):
    pop = r"{\fscx40\fscy40\t(0,180,\fscx110\fscy110)\t(180,300,\fscx100\fscy100)}"
    lines = []
    if hook:
        lines.append((0.0, 2.6, "Hook", pop + hook.upper()))
        if sub:
            lines.append((0.25, 2.6, "Sub", r"{\fad(150,0)}" + sub))
    lines += captions
    lines += [
        (end_start, dur, "End", pop + "LSMX"),
        (end_start + 0.3, dur, "Site", r"{\fad(200,0)}" + cta),
        (end_start + 0.6, dur, "Cta", r"{\fad(200,0)}ABONNE-TOI POUR LA SUITE"),
    ]
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,{FONT},96,&H00FFFFFF,&H00FFFFFF,{RED},{RED},1,0,0,0,100,100,0,-2,3,18,0,8,60,60,330,1
Style: Sub,{FONT},58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,3,8,60,60,500,1
Style: Cap,{FONT},88,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,1,8,4,2,70,70,560,1
Style: End,{FONT},170,&H00FFFFFF,&H00FFFFFF,{RED},{RED},1,0,0,0,100,100,0,0,3,24,0,5,60,60,0,1
Style: Site,{FONT},64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,3,2,60,60,700,1
Style: Cta,{FONT},52,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,3,2,60,60,520,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "\n".join(f"Dialogue: 0,{ts(a)},{ts(b)},{st},,0,0,0,,{tx}" for a, b, st, tx in lines)
    return head + body + "\n"


# ---------------------------------------------------------------- rendu final
def render(src, out, ass, dur, end_start, music, hold):
    d = dur
    v = "[0:v]"
    if hold:  # fige la dernière image pour la carte de fin
        v += f"tpad=stop_mode=clone:stop_duration={hold},"
    v += (
        f"scale=w='1080*(1+0.08*t/{d})':h='1920*(1+0.08*t/{d})':eval=frame:flags=bicubic,"
        "crop=1080:1920,"
        "eq=contrast=1.10:saturation=1.30:brightness=0.02:gamma=0.97,"
        "unsharp=5:5:0.8:3:3:0.0,vignette=PI/5,"
        "fade=in:st=0:d=0.25:color=white,"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.55:t=fill:enable='gte(t,{end_start})',"
        f"drawbox=x=0:y=0:w='iw*t/{d}':h=14:color=0xe8000d:t=fill,"
        f"ass='{ass}'[v]"
    )
    a0 = f"[0:a]apad=pad_dur={hold}" if hold else "[0:a]anull"
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src]
    if music:
        cmd += ["-stream_loop", "-1", "-i", music]
        aud = (f"{a0},asplit[o][sc];[1:a]aresample=48000,volume=0.30[m];"
               "[m][sc]sidechaincompress=threshold=0.03:ratio=10:attack=20:release=400[md];"
               "[o][md]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[a]")
    else:
        aud = f"{a0},loudnorm=I=-14:TP=-1.5[a]"
    cmd += ["-filter_complex", v + ";" + aud, "-map", "[v]", "-map", "[a]", "-t", f"{d:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out]
    run(cmd)


def main():
    p = argparse.ArgumentParser(description="Montage TikTok LSMX")
    p.add_argument("rushs", nargs="+", help="un ou plusieurs rushs, dans l'ordre")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--hook", default=""); p.add_argument("--sub", default="")
    p.add_argument("--cta", default="lsmx-pieces.com")
    p.add_argument("--music")
    p.add_argument("--voix", action="store_true", help="sous-titres + coupe des silences")
    p.add_argument("--garder-silences", action="store_true")
    p.add_argument("--modele", default="small", help="modèle Whisper: small / medium")
    a = p.parse_args()

    tmp = tempfile.mkdtemp(prefix="lsmx_")
    prep = os.path.join(tmp, "prep.mkv")
    print("1/4 Préparation des rushs…"); prepare(a.rushs, prep)

    captions, src, hold = [], prep, 0.0
    if a.voix:
        print("2/4 Transcription de la voix…")
        words = transcribe(prep, a.modele)
        json.dump(words, open(os.path.join(tmp, "mots.json"), "w"), ensure_ascii=False, indent=1)
        print("   ", " ".join(w["w"] for w in words)[:300], "…")
        if not a.garder_silences and words:
            print("3/4 Coupe des silences…")
            rng = keep_ranges(words, duration(prep))
            src = os.path.join(tmp, "cut.mkv"); cut(prep, src, rng)
            words = remap(words, rng)
        captions = caption_events(words)
        hold = END_DUR  # carte de fin après la dernière phrase
    dur = duration(src) + hold
    end_start = dur - END_DUR if hold else max(dur - 2.8, 3.0)
    ass = os.path.join(tmp, "titres.ass")
    open(ass, "w").write(build_ass(dur, a.hook, a.sub, a.cta, captions, end_start))
    print("4/4 Rendu final…"); render(src, a.out, ass, dur, end_start, a.music, hold)
    print(f"OK -> {a.out}  ({dur:.1f} s)  fichiers de travail : {tmp}")


if __name__ == "__main__":
    main()
