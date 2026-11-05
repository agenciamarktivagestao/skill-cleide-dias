"""Gera um edl.json inicial: corta as pausas longas e distribui poucos enquadramentos.

Uso:  python make_cuts.py ../IMG_xxxx.MOV [--transcript transcript.json] [--out edl.json]

Ajuste as constantes abaixo para cada vídeo (não copie números de outro projeto).
Depois do rascunho, SEMPRE olhar os quadros e acertar "headroom" (alto da cabeça no bruto,
em 1080×1920 de zoom 1) e os zooms: close nas falas fortes, sem "teto" em cima da cabeça.
"""
import argparse
import json
import os
import re
import subprocess

# ----- constantes do estilo (ESTILO.md) -----
MIN_PAUSE = 0.30        # silêncio ≥ isso vira corte
PAD_IN = 0.06           # respiro antes da fala
PAD_OUT = 0.08          # respiro depois da fala
MIN_KEEP = 0.25         # trecho menor que isso é descartado (ruído)
SHOT_LEN = 3.5          # um movimento de zoom a cada ~3–5 s (frase a frase)
# zoom in / zoom out suaves: cada tomada desliza de um valor para o outro (padrão Cleide, 04/11)
MOVES = [(1.15, 1.28), (1.32, 1.18), (1.18, 1.12), (1.22, 1.32), (1.35, 1.2), (1.2, 1.3)]
HEADROOM = {"head_src": 330, "head_out": 150, "x": 555}   # alto da cabeça no bruto (1080×1920, zoom 1) → no vídeo
SILENCE_DB = -35        # para quando não há transcrição
HOLD = 0.0              # sem card final (05/11): o vídeo acaba ~0,4 s depois da última palavra


def probe_duration(src):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", src], capture_output=True, text=True).stdout
    return float(out.strip())


def speech_from_words(words):
    rng = []
    for w in words:
        if rng and w["start"] - rng[-1][1] < MIN_PAUSE:
            rng[-1][1] = max(rng[-1][1], w["end"])
        else:
            rng.append([w["start"], w["end"]])
    return rng


def speech_from_silence(src, dur):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-vn", "-af",
                        f"silencedetect=noise={SILENCE_DB}dB:d={MIN_PAUSE}", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r)]
    sil = list(zip(starts, ends + [dur] * (len(starts) - len(ends))))
    rng, t = [], 0.0
    for a, b in sil:
        if a > t:
            rng.append([t, a])
        t = b
    if t < dur:
        rng.append([t, dur])
    return rng


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--transcript", default="transcript.json")
    ap.add_argument("--out", default="edl.json")
    a = ap.parse_args()

    dur = probe_duration(a.source)
    if os.path.exists(a.transcript):
        with open(a.transcript, encoding="utf-8") as f:
            words = json.load(f)["words"]
        speech = speech_from_words(words)
        how = "transcrição"
    else:
        speech = speech_from_silence(a.source, dur)
        how = "detecção de silêncio"

    segs = []
    for i, (s, e) in enumerate(speech):
        prev_end = speech[i - 1][1] if i else 0.0
        next_start = speech[i + 1][0] if i + 1 < len(speech) else dur
        s2 = max(prev_end + (s - prev_end) / 2 if i else 0.0, s - PAD_IN)
        e2 = min(e + (next_start - e) / 2, e + PAD_OUT, dur)
        if e2 - s2 >= MIN_KEEP:
            segs.append([round(s2, 3), round(e2, 3)])

    out, t_out, since, k = [], 0.0, 0.0, 0
    for s, e in segs:
        if since >= SHOT_LEN:
            k += 1
            since = 0.0
        z0, z1 = MOVES[k % len(MOVES)]
        out.append({"start": s, "end": e, "zoom": z0, "zoom_to": z1, "trans_in": "blur" if out else None})
        since += e - s
        t_out += e - s

    for sg in out:
        if not sg.get("trans_in"):
            sg.pop("trans_in", None)
    edl = {
        "source": os.path.abspath(a.source),
        "hdr": "auto",
        "headroom": HEADROOM,
        "segments": out,
        "hold": HOLD,
        "captions": {"style": "CLD", "hook_end": 0, "script": [], "bold": [], "pills": [], "underline": [],
                     "fix": {}, "keep_case": ["WhatsApp"], "words_file": "transcript.json"},
        "cards": [],
        "music": {"file": "../../../REFERENCIAS/trilha_6A5B.MOV", "db": -20, "end_boost_db": 6},
        "sfx": "auto",
        "logo": False,
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(edl, f, ensure_ascii=False, indent=1)
    print(f"Base: {how}. Original {dur:.1f}s → {t_out:.1f}s em {len(out)} trechos "
          f"({len(out) - 1} cortes de pausa, zoom suave em cada tomada). → {a.out}")


if __name__ == "__main__":
    main()
