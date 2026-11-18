#!/usr/bin/env python3
"""LSMX — montage automatique TikTok (style "trouvaille / sortie de grange").

Usage :
  python3 montage/lsmx_montage.py RUSH.mp4 SORTIE.mp4 \
      --hook "SORTIE DE GRANGE" --sub "YZ 250 de 1991" \
      [--music musique.mp3] [--cta "lsmx-pieces.com"]

Ce que fait le script :
  - 1080x1920 (9:16), upscale propre, couleurs + contraste + netteté
  - "punch zoom" léger et continu pour garder l'œil accroché
  - accroche animée dans les 2,5 premières secondes (la plus importante)
  - barre de progression rouge LSMX en haut
  - carte de fin avec appel à l'action
  - son normalisé à -14 LUFS (standard TikTok), musique mixée si fournie
"""
import argparse, json, os, subprocess, tempfile

RED = "&H0D00E8&"      # #e8000d en BGR pour ASS
FONT = "Inter ExtraBold"


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "json", path])
    return float(json.loads(out)["format"]["duration"])


def ts(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def build_ass(dur, hook, sub, cta):
    end_start = max(dur - 2.8, 3.0)
    pop = r"{\fscx40\fscy40\t(0,180,\fscx110\fscy110)\t(180,300,\fscx100\fscy100)}"
    lines = [
        # Accroche principale (bandeau rouge)
        (0.0, 2.6, "Hook", pop + hook.upper()),
        (0.25, 2.6, "Sub", r"{\fad(150,0)}" + sub),
        # Carte de fin
        (end_start, dur, "End", pop + "LSMX"),
        (end_start + 0.3, dur, "Site", r"{\fad(200,0)}" + cta),
        (end_start + 0.6, dur, "Cta", r"{\fad(200,0)}ABONNE-TOI POUR LA SUITE"),
    ]
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,{FONT},96,&H00FFFFFF,&H00FFFFFF,{RED},{RED},1,0,0,0,100,100,0,-2,3,18,0,8,60,60,330,1
Style: Sub,{FONT},58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,3,8,60,60,500,1
Style: End,{FONT},170,&H00FFFFFF,&H00FFFFFF,{RED},{RED},1,0,0,0,100,100,0,0,3,24,0,5,60,60,0,1
Style: Site,{FONT},64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,3,2,60,60,700,1
Style: Cta,{FONT},52,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,3,2,60,60,520,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "\n".join(f"Dialogue: 0,{ts(a)},{ts(b)},{st},,0,0,0,,{tx}" for a, b, st, tx in lines)
    return head + body + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src"); p.add_argument("out")
    p.add_argument("--hook", required=True); p.add_argument("--sub", default="")
    p.add_argument("--cta", default="lsmx-pieces.com")
    p.add_argument("--music")
    a = p.parse_args()

    dur = duration(a.src)
    end_start = max(dur - 2.8, 3.0)
    tmp = tempfile.mkdtemp()
    ass = os.path.join(tmp, "t.ass")
    open(ass, "w").write(build_ass(dur, a.hook, a.sub, a.cta))

    v = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,"
        "fps=30,"
        # zoom continu léger (1.00 -> 1.08) pour donner du mouvement
        "scale=w='1080*(1+0.08*t/{d})':h='1920*(1+0.08*t/{d})':eval=frame:flags=bicubic,"
        "crop=1080:1920,"
        "eq=contrast=1.10:saturation=1.30:brightness=0.02:gamma=0.97,"
        "unsharp=5:5:0.8:3:3:0.0,vignette=PI/5,"
        # flash d'entrée + assombrissement sur la carte de fin
        "fade=in:st=0:d=0.25:color=white,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.55:t=fill:enable='gte(t,{e})',"
        # barre de progression rouge
        "drawbox=x=0:y=0:w='iw*t/{d}':h=14:color=0xe8000d:t=fill,"
        "ass='{ass}'[v]"
    ).format(d=dur, e=end_start, ass=ass)

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.src]
    if a.music:
        cmd += ["-stream_loop", "-1", "-i", a.music]
        aud = ("[0:a]asplit[o][sc];[1:a]volume=0.35[m];"
               "[m][sc]sidechaincompress=threshold=0.05:ratio=8[md];"
               "[o][md]amix=inputs=2:duration=first,loudnorm=I=-14:TP=-1.5[a]")
    else:
        aud = "[0:a]loudnorm=I=-14:TP=-1.5[a]"
    cmd += ["-filter_complex", v + ";" + aud, "-map", "[v]", "-map", "[a]",
            "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out]
    subprocess.run(cmd, check=True)
    print("OK ->", a.out)


if __name__ == "__main__":
    main()
