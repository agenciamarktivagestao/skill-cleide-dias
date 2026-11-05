"""Estende uma trilha até a duração do vídeo repetindo compassos, sem emenda audível.

Uso:  python music_extend.py <trilha ou vídeo com a trilha> <duração em s> [saída.wav]

Como funciona:
  1. Lê o áudio (48 kHz estéreo) e tira o silêncio do começo e do fim (o 6A5B tinha 3,7 s mudos no fim).
  2. Mede, a cada ~10 ms, a harmonia (12 notas), o timbre (32 faixas) e os ataques (onsets).
  3. Procura pares de pontos (de → para, voltando no tempo) em ataques de nota onde a música antes e
     depois é parecida (mesmo acorde, mesma textura). Pular de um para o outro repete um trecho.
  4. Escolhe 1 ou 2 pulos cuja soma dá a extensão que falta, mantendo o FINAL original da música
     (o fade/acorde final cai no fim do vídeo).
  5. Acerta cada emenda na amostra (correlação ±25 ms) e cruza 70 ms com potência constante.

Sem pulo bom o bastante, avisa (aí use uma trilha mais longa ou corte a música com fade).
Também serve como módulo: extend(path, dur) → (np.ndarray (n, 2) a 48 kHz, relatório).
"""
import json
import subprocess
import sys

import numpy as np
from scipy import signal

SR = 48000
HOP = 512
XFADE = 0.07             # s de crossfade em cada emenda
MIN_LAG = 2.0            # s: repetição mínima (≈ 1 compasso)
END_SLACK = 0.35         # s: a música pode acabar até isso antes do vídeo (o fim dela já é fade)


def read(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vn", "-ac", "2", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def trim_silence(x, db=-55):
    m = np.abs(x).max(1)
    blk = SR // 100
    e = np.array([m[i:i + blk].max() for i in range(0, len(m), blk)])
    on = np.flatnonzero(e > 10 ** (db / 20))
    if not len(on):
        return x, 0
    a, b = on[0] * blk, min(len(x), (on[-1] + 1) * blk)
    return x[a:b], a


def features(mono):
    win = 4096
    f, _, Z = signal.stft(mono, SR, nperseg=win, noverlap=win - HOP, boundary=None)
    mag = np.abs(Z)
    ok = (f > 60) & (f < 5000)
    cls = np.round(69 + 12 * np.log2(f[ok] / 440)).astype(int) % 12
    chroma = np.stack([mag[ok][cls == c].sum(0) for c in range(12)])
    edges = np.geomspace(60, 14000, 33)
    bands = np.log1p(30 * np.stack([mag[(f >= edges[i]) & (f < edges[i + 1])].sum(0) for i in range(32)]))
    flux = np.maximum(0, np.diff(np.log1p(100 * mag), axis=1)).sum(0)
    flux = np.r_[0, (flux - flux.mean()) / (flux.std() + 1e-9)]
    k = max(1, int(0.15 * SR / HOP))
    ker = np.ones(k) / k
    chroma = np.stack([np.convolve(c, ker, "same") for c in chroma])
    chroma /= np.linalg.norm(chroma, axis=0, keepdims=True) + 1e-9
    return chroma, bands, flux


def join_score(ch, bd, fl, i1, i2, w):
    """Parecido de [i−w, i+w] em volta de i1 (para onde volta) e de i2 (de onde pula)."""
    a1, b1, a2, b2 = i1 - w, i1 + w, i2 - w, i2 + w
    if a1 < 0 or a2 < 0 or b1 > ch.shape[1] or b2 > ch.shape[1]:
        return -1
    harm = float((ch[:, a1:b1] * ch[:, a2:b2]).sum(0).mean())
    u, v = bd[:, a1:b1].ravel(), bd[:, a2:b2].ravel()
    u, v = u - u.mean(), v - v.mean()
    timb = float(u @ v / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-9))
    p, q = fl[a1:b1] - fl[a1:b1].mean(), fl[a2:b2] - fl[a2:b2].mean()
    rhy = float(p @ q / (np.linalg.norm(p) * np.linalg.norm(q) + 1e-9))
    return harm + 0.5 * timb + 0.3 * rhy


def best_offset(x, s_to, s_from, rng=int(0.025 * SR), L=int(0.06 * SR)):
    """Desloca o ponto de volta (±25 ms) para a forma de onda casar com a do ponto de pulo."""
    ref = x[s_from - L:s_from].mean(1)
    best, bo = -9, 0
    for o in range(-rng, rng + 1, 8):
        a = s_to + o
        if a - L < 0:
            continue
        seg = x[a - L:a].mean(1)
        c = float(ref @ seg / (np.linalg.norm(ref) * np.linalg.norm(seg) + 1e-9))
        if c > best:
            best, bo = c, o
    return s_to + bo, best


def extend(path, dur):
    x, lead = trim_silence(read(path))
    n0 = len(x)
    need = dur - n0 / SR
    rep = {"source": path, "music_s": round(n0 / SR, 3), "target_s": round(dur, 3), "joins": []}
    if need <= 0:                                   # já é longa: corta com fade de 1,5 s no fim
        y = x[: int(dur * SR)].copy()
        f = min(len(y), int(1.5 * SR))
        y[-f:] *= np.linspace(1, 0, f)[:, None]
        rep["mode"] = "corte com fade"
        return y, rep
    ch, bd, fl = features(x.mean(1))
    fr = SR / HOP
    ons, _ = signal.find_peaks(fl, height=0.6, distance=int(0.12 * fr))
    end_guard = n0 / SR - 2.0                       # não pula de dentro do final da música
    w = int(0.8 * fr)
    # compasso: as melhores emendas curtas (1,5–4 s) caem a cada compasso; a mediana delas dá a duração
    short = sorted(((join_score(ch, bd, fl, i1, i2, w), (i2 - i1) / fr) for i2 in ons for i1 in ons
                    if 1.5 <= (i2 - i1) / fr <= 4.0 and i2 / fr <= end_guard), reverse=True)[:20]
    bar = float(np.median([lag for _, lag in short])) if short else 2.5
    rep["compasso_s"] = round(bar, 3)
    cands = []                                      # (qualidade, t1, t2, lag, nota, forma de onda)
    for i2 in ons:
        if i2 / fr > end_guard:
            continue
        for i1 in ons:
            lag = (i2 - i1) / fr
            nb = round(lag / bar)
            if nb < 1 or abs(lag - nb * bar) > 0.1 or lag > need + 0.05:
                continue
            sc = join_score(ch, bd, fl, i1, i2, w)
            if sc <= 0.9:
                continue
            _, corr = best_offset(x, int(i1 / fr * SR), int(i2 / fr * SR))
            cands.append((sc + 0.5 * corr, i1 / fr, i2 / fr, lag))
    cands.sort(reverse=True)
    cands = cands[:300]
    plans = []
    for q, t1, t2, lag in cands:                    # 1 pulo
        if need - END_SLACK <= lag <= need + 0.05:
            plans.append((q, [(t1, t2)]))
    for a in range(len(cands)):                     # 2 pulos: toca 0→t2a, volta a t1a, toca até t2b, volta a t1b
        qa, t1a, t2a, la = cands[a]
        for b in range(len(cands)):
            qb, t1b, t2b, lb = cands[b]
            if a == b or not (need - END_SLACK <= la + lb <= need + 0.05) or t2b <= t1a + 0.5:
                continue
            plans.append((min(qa, qb) - 0.05, [(t1a, t2a), (t1b, t2b)]))   # leve preferência por 1 pulo
    if not plans:
        raise SystemExit(f"music_extend: não achei emenda boa para estender {n0 / SR:.1f}s → {dur:.1f}s")
    plans.sort(key=lambda p: -p[0])
    score, joins = plans[0]
    # monta: segmentos [início, fim) na trilha original
    pos, segs = 0, []
    for t1, t2 in joins:
        s_from = int(t2 * SR)
        s_to, corr = best_offset(x, int(t1 * SR), s_from)
        segs.append((pos, s_from))
        rep["joins"].append({"de_s": round(t2, 3), "volta_para_s": round(s_to / SR, 3),
                             "repete_s": round((s_from - s_to) / SR, 3), "nota": round(score, 3),
                             "forma_de_onda": round(corr, 3)})
        pos = s_to
    segs.append((pos, n0))
    xf = int(XFADE * SR)
    th = np.linspace(0, np.pi / 2, xf)[:, None]
    y = x[segs[0][0]:segs[0][1]].copy()
    for (_, prev_end), (a, b) in zip(segs[:-1], segs[1:]):
        # no ponto de pulo, a música antiga continua 70 ms sumindo enquanto a nova entra (mesmo alinhamento)
        old_ = x[prev_end:prev_end + xf]
        if len(old_) < xf:
            old_ = np.pad(old_, ((0, xf - len(old_)), (0, 0)))
        y = np.concatenate([y, old_ * np.cos(th) + x[a:a + xf] * np.sin(th), x[a + xf:b]])
    rep["mode"] = f"{len(joins)} emenda(s)"
    rep["result_s"] = round(len(y) / SR, 3)
    rep["lead_silence_s"] = round(lead / SR, 3)
    return y, rep


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    y, rep = extend(sys.argv[1], float(sys.argv[2]))
    out = sys.argv[3] if len(sys.argv) > 3 else "trilha_estendida.wav"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "f64le", "-ac", "2", "-ar", str(SR), "-i", "-",
                          "-c:a", "pcm_s24le", out], stdin=subprocess.PIPE)
    p.stdin.write(y.astype(np.float64).tobytes())
    p.stdin.close()
    p.wait()
    print(json.dumps(rep, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
