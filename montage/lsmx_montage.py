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
            if words and re.fullmatch(r"[?!.,;:…]+", t):
                words[-1]["w"] += t if t not in "?!" else " " + t
                continue
            if words and (t[0] in "'’-." or words[-1]["w"].endswith(("'", "’"))):
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


def apply_corrections(words, corr):
    """Remplace des suites de mots mal comprises : {"on du nez": "venez"}."""
    key = lambda w: re.sub(r"[^\w.'-]", "", w.lower())
    for wrong, right in corr.items():
        seq = wrong.lower().split(); n = len(seq); i = 0
        while i + n <= len(words):
            if [key(w["w"]) for w in words[i:i + n]] == [key(x) for x in seq]:
                punct = re.search(r"[.,!?;:]*$", words[i + n - 1]["w"]).group()
                words[i:i + n] = [{"w": right + punct, "s": words[i]["s"], "e": words[i + n - 1]["e"]}]
            i += 1
    return words


def map_time(P, ranges):
    acc = 0.0
    for a, b in ranges:
        if P <= b:
            return acc + max(P - a, 0)
        acc += b - a
    return acc


# ---------------------------------------------------------------- pause + souris
def pause_assets(tmp):
    from PIL import Image, ImageDraw
    S = 4  # supersampling
    def icon(kind):
        im = Image.new("RGBA", (300 * S, 300 * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse([0, 0, 300 * S - 1, 300 * S - 1], fill=(0, 0, 0, 150), outline=(255, 255, 255, 235), width=8 * S)
        if kind == "pause":
            for x in (100, 172):
                d.rounded_rectangle([x * S, 85 * S, (x + 30) * S, 215 * S], radius=8 * S, fill="white")
        else:
            d.polygon([(115 * S, 80 * S), (115 * S, 220 * S), (225 * S, 150 * S)], fill="white")
        return im.resize((300, 300), Image.LANCZOS)
    def cursor(scale=1.0):
        pts = [(0, 0), (0, 92), (24, 70), (42, 110), (58, 103), (40, 64), (72, 64)]
        W = int(90 * S * scale); im = Image.new("RGBA", (W, int(125 * S * scale)), (0, 0, 0, 0))
        d = ImageDraw.Draw(im); k = S * scale * 1.05
        poly = [(6 * S + x * k, 6 * S + y * k) for x, y in pts]
        d.polygon(poly, fill="white", outline="black", width=int(6 * S * scale))
        return im.resize((im.width // S, im.height // S), Image.LANCZOS)
    paths = {}
    for name, im in [("pause", icon("pause")), ("play", icon("play")),
                     ("cur", cursor(1.5)), ("curc", cursor(1.3))]:
        paths[name] = os.path.join(tmp, f"{name}.png"); im.save(paths[name])
    return paths


def insert_pause(src, out, P, D, tmp, Pa=None):
    """Fige l'image à P pendant D s : icône pause, la souris arrive et clique, icône play.
    La voix continue jusqu'à Pa (fin du mot en cours, ex. « pause »), puis silence."""
    Pa = P if Pa is None else Pa
    a = pause_assets(tmp)
    cx, cy = 540, 860                        # centre de l'icône
    t0, t1, tc = P + 0.15, P + 0.75, P + 0.85  # souris : départ, arrivée, clic
    ease = f"(1-pow(1-min(1,max(0,(t-{t0})/{t1 - t0})),3))"
    x = f"'{cx + 330}+({cx - 4}-{cx + 330})*{ease}'"
    y = f"'{cy + 620}+({cy + 6}-{cy + 620})*{ease}'"
    fc = (
        f"[0:v]split[va][vb];"
        f"[va]trim=0:{P},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={D},trim=0:{P + D},"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.30:t=fill:enable='gte(t,{P})'[f0];"
        f"[1:v]format=rgba[ip];[2:v]format=rgba[iq];[3:v]format=rgba,split[ic][ic2];[4:v]format=rgba[id];"
        f"[f0][ip]overlay=x={cx - 150}:y={cy - 150}:enable='between(t,{P + 0.03},{tc})'[f1];"
        f"[f1][iq]overlay=x={cx - 150}:y={cy - 150}:enable='between(t,{tc},{P + D - 0.12})'[f2];"
        f"[f2][ic]overlay=x={x}:y={y}:enable='between(t,{t0},{tc - 0.01})'[f3];"
        f"[f3][id]overlay=x={cx - 1}:y={cy + 9}:enable='between(t,{tc},{tc + 0.12})'[f4];"
        f"[f4][ic2]overlay=x={cx - 4}:y={cy + 6}:enable='between(t,{tc + 0.12},{P + D - 0.12})',trim=0:{P + D}[vf];"
        f"[vb]trim=start={Pa},setpts=PTS-STARTPTS[vr];"
        f"[0:a]asplit[aa][ab];[aa]atrim=0:{Pa},asetpts=PTS-STARTPTS,apad=pad_dur={P + D - Pa}[af];"
        f"[ab]atrim=start={Pa},asetpts=PTS-STARTPTS[ar];"
        f"[vf][af][vr][ar]concat=n=2:v=1:a=1[v][a]"
    )
    loop = lambda p: ["-loop", "1", "-framerate", "30", "-t", f"{P + D + 0.5:.2f}", "-i", p]
    run(["ffmpeg", "-y", "-v", "error", "-i", src, *loop(a["pause"]), *loop(a["play"]),
         *loop(a["cur"]), *loop(a["curc"]), "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-c:a", "pcm_s16le", out])
    return tc


# ---------------------------------------------------------------- effets
HERE = os.path.dirname(os.path.abspath(__file__))
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def norm(t):
    return re.sub(r"[^\w€' -]", "", t.lower()).strip()


def emoji_png(ch, folder, size=240):
    from PIL import Image, ImageDraw, ImageFont
    path = os.path.join(folder, f"emoji_{ord(ch[0]):x}.png")
    if not os.path.exists(path):
        font = ImageFont.truetype(EMOJI_FONT, 109)
        im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((80, 80), ch, font=font, embedded_color=True, anchor="mm")
        im = im.crop(im.getbbox()).resize((size, size), Image.LANCZOS)
        im.save(path)
    return path


def plan_effects(words, cut_times, hook, tmp, cfg_path):
    cfg = json.load(open(cfg_path))
    gap = cfg.get("ecart_min_secondes", 2.5)
    sfx = lambda n: os.path.join(HERE, "sfx", n + ".wav") if n else None
    fx = []
    if hook:
        fx.append({"t": 0.05, "son": sfx("whoosh"), "vol": 0.5})
    start_after = 2.6 if hook else 0.4
    last = -99.0
    toks = [norm(w["w"]) for w in words]
    for i, w in enumerate(words):
        if w["s"] < start_after or w["s"] - last < gap:
            continue
        for r in cfg["regles"]:
            hit = any((" ".join(toks[i:i + len(m.split())]) == m) for m in map(str.lower, r["mots"]))
            if hit:
                img = r.get("image")
                img = os.path.join(HERE, img) if img else (emoji_png(r["emoji"], tmp) if r.get("emoji") else None)
                fx.append({"t": w["s"], "son": sfx(r.get("son")), "img": img, "vol": 0.6})
                last = w["s"]
                break
    cut_sound = cfg.get("son_coupes")
    if cut_sound:
        lastc = -99.0
        for t in cut_times:
            if t - lastc >= 4 and all(abs(t - e["t"]) > 1.0 for e in fx):
                fx.append({"t": t, "son": sfx(cut_sound), "vol": 0.25}); lastc = t
    return sorted(fx, key=lambda e: e["t"])


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
Style: Hook,{FONT},84,&H00FFFFFF,&H00FFFFFF,{RED},{RED},1,0,0,0,100,100,0,-2,3,18,0,8,60,60,330,1
Style: Sub,{FONT},58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,3,8,60,60,560,1
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
def render(src, out, ass, dur, end_start, music, hold, fx=(), music_start=0.0):
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
        f"ass='{ass}'[v0]"
    )
    extra, vchain, sfx_labels, last, idx = [], [], [], "v0", 1 + (1 if music else 0)
    for n, e in enumerate(fx):
        T = e["t"]
        if e.get("img"):
            extra += ["-loop", "1", "-t", f"{d:.3f}", "-i", e["img"]]
            vchain.append(
                f"[{idx}:v]format=rgba,fade=in:st={T:.2f}:d=0.12:alpha=1,"
                f"fade=out:st={T + 1.0:.2f}:d=0.2:alpha=1[i{n}];"
                f"[{last}][i{n}]overlay=x=(W-w)/2:y='430-90*max(0,1-(t-{T:.2f})*7)':"
                f"enable='between(t,{T:.2f},{T + 1.25:.2f})'[w{n}]")
            last, idx = f"w{n}", idx + 1
        if e.get("son"):
            extra += ["-i", e["son"]]
            ms = int(T * 1000)
            vchain.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,"
                          f"volume={e.get('vol', 0.6)},adelay={ms}|{ms}[s{n}]")
            sfx_labels.append(f"[s{n}]"); idx += 1
    v += "".join(";" + c for c in vchain) + f";[{last}]null[v]"
    a0 = f"[0:a]apad=pad_dur={hold}" if hold else "[0:a]anull"
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src]
    if music:
        cmd += ["-stream_loop", "-1", "-i", music]
        aud = (f"{a0},asplit[o][sc];"
               f"[1:a]aresample=48000,aformat=channel_layouts=stereo,volume=0.30,"
               f"adelay={int(music_start * 1000)}|{int(music_start * 1000)}[m];"
               "[m][sc]sidechaincompress=threshold=0.03:ratio=10:attack=20:release=400[md];"
               "[o][md]amix=inputs=2:duration=first:normalize=0[mix]")
    else:
        aud = f"{a0}[mix]"
    if sfx_labels:
        aud += f";[mix]{''.join(sfx_labels)}amix=inputs={1 + len(sfx_labels)}:duration=first:normalize=0[mx2]"
        aud += ";[mx2]loudnorm=I=-14:TP=-1.5[a]"
    else:
        aud += ";[mix]loudnorm=I=-14:TP=-1.5[a]"
    cmd += extra + ["-filter_complex", v + ";" + aud, "-map", "[v]", "-map", "[a]", "-t", f"{d:.3f}",
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
    p.add_argument("--effets", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "effets.json"))
    p.add_argument("--sans-effets", action="store_true")
    p.add_argument("--pause", type=float, help="seconde (dans le rush) où figer l'image avec pause + clic souris")
    p.add_argument("--pause-duree", type=float, default=1.5)
    p.add_argument("--corrections", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "corrections.json"))
    a = p.parse_args()
    if not os.path.exists(os.path.join(HERE, "sfx", "whoosh.wav")):
        subprocess.run(["python3", os.path.join(HERE, "generer_sfx.py")], check=True)

    tmp = tempfile.mkdtemp(prefix="lsmx_")
    prep = os.path.join(tmp, "prep.mkv")
    print("1/4 Préparation des rushs…"); prepare(a.rushs, prep)

    captions, src, hold, fx, cut_times = [], prep, 0.0, [], []
    rng, music_start, pause_fx = None, 0.0, []
    if a.voix:
        print("2/4 Transcription de la voix…")
        words = transcribe(prep, a.modele)
        if os.path.exists(a.corrections):
            words = apply_corrections(words, json.load(open(a.corrections)))
        json.dump(words, open(os.path.join(tmp, "mots.json"), "w"), ensure_ascii=False, indent=1)
        print("   ", " ".join(w["w"] for w in words)[:300], "…")
        if not a.garder_silences and words:
            print("3/4 Coupe des silences…")
            rng = keep_ranges(words, duration(prep))
            src = os.path.join(tmp, "cut.mkv"); cut(prep, src, rng)
            words = remap(words, rng)
            acc = 0.0
            for a0, b0 in rng:
                cut_times.append(acc); acc += b0 - a0
            cut_times = cut_times[1:]
    if a.pause is not None:
        P = map_time(a.pause, rng) if rng else a.pause
        D = a.pause_duree
        Pa = P
        if a.voix:  # laisse finir le mot prononcé juste au moment de la pause
            for w in words:
                if P - 0.1 <= w["s"] <= P + 0.6:
                    Pa = max(Pa, w["e"] + 0.06)
            Pa = min(Pa, P + D - 0.9)
        print(f"   pause à {P:.2f}s pendant {D}s (voix jusqu'à {Pa:.2f}s)")
        paused = os.path.join(tmp, "pause.mkv")
        tc = insert_pause(src, paused, P, D, tmp, Pa); src = paused
        sh = P + D - Pa
        if a.voix:
            words = [dict(w, s=w["s"] + sh, e=w["e"] + sh) if w["s"] >= Pa - 0.05 else w for w in words]
        cut_times = [t + sh if t >= Pa else t for t in cut_times]
        music_start = P + D
        pause_fx = [{"t": tc, "son": os.path.join(HERE, "sfx", "clic.wav"), "vol": 0.9},
                    {"t": P + D - 0.05, "son": os.path.join(HERE, "sfx", "whoosh.wav"), "vol": 0.45}]
    if a.voix:
        captions = caption_events(words)
        hold = END_DUR  # carte de fin après la dernière phrase
        if not a.sans_effets:
            fx = plan_effects(words, cut_times, a.hook, tmp, a.effets)
            if pause_fx:  # pas d'autre effet pendant la pause
                fx = [e for e in fx if not (P - 0.3 <= e["t"] <= P + D + 0.6)] + pause_fx
                fx.sort(key=lambda e: e["t"])
            for e in fx:
                print(f"    effet {e['t']:6.2f}s  {os.path.basename(e.get('son') or '-'):11s} "
                      f"{'image' if e.get('img') else ''}")
    elif a.hook and not a.sans_effets:
        fx = [{"t": 0.05, "son": os.path.join(HERE, "sfx", "whoosh.wav"), "vol": 0.5}]
    dur = duration(src) + hold
    end_start = dur - END_DUR if hold else max(dur - 2.8, 3.0)
    ass = os.path.join(tmp, "titres.ass")
    open(ass, "w").write(build_ass(dur, a.hook, a.sub, a.cta, captions, end_start))
    print("4/4 Rendu final…"); render(src, a.out, ass, dur, end_start, a.music, hold, fx, music_start)
    print(f"OK -> {a.out}  ({dur:.1f} s)  fichiers de travail : {tmp}")


if __name__ == "__main__":
    main()
