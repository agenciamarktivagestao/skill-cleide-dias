"""Trilha e efeitos sintetizados (sem problema de licença). Padrão Cleide: trilha "calm", efeitos suaves."""
import numpy as np

SR = 48000


def _note(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _env(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def _pluck(f, dur, bright=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) + 0.35 * bright * np.sin(4 * np.pi * f * t) + 0.12 * bright * np.sin(6 * np.pi * f * t)
    return y * np.exp(-t * 5.5) * _env(n, 0.004, 0.05)


def _pad(freqs, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f in freqs:
        for det in (-0.6, 0.6):
            ff = f * (1 + det / 1200 * 8)
            y += np.sin(2 * np.pi * ff * t) + 0.25 * np.sin(4 * np.pi * ff * t + 0.3)
    y *= (1 + 0.15 * np.sin(2 * np.pi * 0.25 * t))
    return y / (len(freqs) * 2) * _env(n, min(0.8, dur / 3), min(0.8, dur / 3))


def music(dur, style="calm", seed=1):
    rng = np.random.default_rng(seed)
    bpm = 82 if style == "calm" else 112
    beat = 60 / bpm
    bar = beat * 4
    # Ré maior: D – A – Bm – G
    prog = [[62, 66, 69], [57, 61, 64], [59, 62, 66], [55, 59, 62]]
    n = int((dur + 1) * SR)
    out = np.zeros((n, 2))
    t0, k = 0.0, 0
    while t0 < dur + 0.5:
        ch = prog[k % 4]
        L = bar * (2 if style == "calm" else 1)
        p = _pad([_note(m) for m in ch], L + 0.6) * (0.55 if style == "calm" else 0.35)
        i0 = int(t0 * SR)
        seg = p[: max(0, min(len(p), n - i0))]
        out[i0:i0 + len(seg)] += seg[:, None]
        # baixo
        b = _pluck(_note(ch[0] - 24), L * 0.9, bright=0.3) * 0.5
        seg = b[: max(0, min(len(b), n - i0))]
        out[i0:i0 + len(seg)] += seg[:, None]
        # arpejo
        step = beat / 2
        arp = ch + [ch[0] + 12, ch[1] + 12]
        j = 0
        tt = t0
        while tt < t0 + L - 1e-6:
            m = arp[j % len(arp)] + 12
            if style == "calm" and j % 2 == 1 and rng.random() < 0.5:
                j += 1
                tt += step
                continue
            pl = _pluck(_note(m), 0.6) * (0.22 if style == "calm" else 0.28)
            pan = 0.5 + 0.35 * np.sin(j * 1.3)
            i = int(tt * SR)
            seg = pl[: max(0, min(len(pl), n - i))]
            out[i:i + len(seg), 0] += seg * (1 - pan)
            out[i:i + len(seg), 1] += seg * pan
            j += 1
            tt += step
        if style == "upbeat":
            for q in range(int(L / beat)):
                i = int((t0 + q * beat) * SR)
                kk = _kick()
                seg = kk[: max(0, min(len(kk), n - i))]
                out[i:i + len(seg)] += seg[:, None] * 0.45
                i2 = int((t0 + q * beat + beat / 2) * SR)
                sh = _shaker(rng)
                seg = sh[: max(0, min(len(sh), n - i2))]
                out[i2:i2 + len(seg)] += seg[:, None] * 0.12
        t0 += L
        k += 1
    out = out[: int(dur * SR)]
    fade = int(min(1.5, dur / 4) * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return out


def _kick():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    f = 120 * np.exp(-t * 18) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)


def _shaker(rng):
    n = int(0.06 * SR)
    x = rng.standard_normal(n)
    x = np.diff(x, prepend=0)
    return x * np.exp(-np.arange(n) / SR * 60) * 0.5


def _lp(x, k):
    return np.convolve(x, np.ones(k) / k, mode="same")


def sfx(kind, seed=0):
    rng = np.random.default_rng(seed)
    if kind == "softpop":
        n = int(0.09 * SR)
        t = np.arange(n) / SR
        f = 300 + 700 * np.exp(-t * 45)
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38)
    elif kind == "tap":
        n = int(0.05 * SR)
        t = np.arange(n) / SR
        y = 0.6 * np.sin(2 * np.pi * 1700 * t) * np.exp(-t * 120) + 0.4 * rng.standard_normal(n) * np.exp(-t * 200)
    elif kind == "air":
        n = int(0.5 * SR)
        t = np.arange(n) / SR
        x = _lp(rng.standard_normal(n), 9) - _lp(rng.standard_normal(n), 60) * 0.5
        y = x * np.sin(np.pi * np.clip(t / 0.5, 0, 1)) ** 2 * 0.8
    elif kind == "paper":
        n = int(0.14 * SR)
        x = np.diff(rng.standard_normal(n), prepend=0)
        y = x * (rng.random(n) < 0.35) * np.exp(-np.arange(n) / SR * 25) * 0.6
    elif kind == "chime":
        n = int(1.4 * SR)
        t = np.arange(n) / SR
        f = 1318.5
        y = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d) for a, r, d in
                [(1, 1, 3.2), (0.45, 2.76, 5), (0.25, 5.4, 8), (0.3, 0.5, 2.5)])
        y *= _env(n, 0.003, 0.2) * 0.5
    elif kind == "cash":                       # dinheiro: "ka" (trava da caixa) + "ching" (sino) + moedas
        n = int(1.1 * SR)
        t = np.arange(n) / SR
        y = np.zeros(n)
        k = int(0.035 * SR)
        y[:k] += (np.diff(rng.standard_normal(k), prepend=0) * 0.5 + np.sin(2 * np.pi * 160 * t[:k])) \
            * np.exp(-t[:k] * 90) * 0.6
        i0 = int(0.05 * SR)
        tb = t[: n - i0]
        bell = sum(a * (np.sin(2 * np.pi * 2637 * r * tb) + np.sin(2 * np.pi * 2650 * r * tb + 1.0)) * np.exp(-tb * d)
                   for a, r, d in [(1, 1, 4.5), (0.5, 2.32, 7), (0.3, 4.25, 11), (0.15, 6.63, 16)])
        y[i0:] += bell * 0.5 * _env(len(tb), 0.002, 0.1)
        for _ in range(7):                     # moedas tilintando logo depois
            tc = rng.uniform(0.09, 0.42)
            ic, m = int(tc * SR), int(0.05 * SR)
            tt = np.arange(m) / SR
            f = rng.uniform(4200, 7800)
            c = (np.sin(2 * np.pi * f * tt) + 0.6 * np.sin(2 * np.pi * f * 1.47 * tt)) \
                * np.exp(-tt * rng.uniform(70, 120)) * rng.uniform(0.15, 0.35) * (1 - tc)
            y[ic:ic + m] += c[: max(0, min(m, n - ic))]
    elif kind == "click":                      # clique de mouse (aperta + solta)
        n = int(0.11 * SR)
        y = np.zeros(n)
        for t0, a in ((0.0, 1.0), (0.075, 0.55)):
            i, m = int(t0 * SR), int(0.012 * SR)
            tt = np.arange(m) / SR
            c = (np.diff(rng.standard_normal(m), prepend=0) * 0.7 + np.sin(2 * np.pi * 3100 * tt)) * np.exp(-tt * 420) * a
            y[i:i + m] += c[: n - i]
    elif kind == "correct":
        y = np.concatenate([_pluck(_note(88), 0.12), _pluck(_note(93), 0.5)])
    elif kind == "wrong":
        n = int(0.4 * SR)
        t = np.arange(n) / SR
        y = 0.5 * np.sign(np.sin(2 * np.pi * (180 - 60 * t) * t)) * np.exp(-t * 6)
        y = _lp(y, 20)
    elif kind == "whoosh":                     # passagem de ar: ruído filtrado que abre e fecha (0,5 s)
        n = int(0.5 * SR)
        t = np.arange(n) / SR
        x = rng.standard_normal(n)
        al = 0.012 + 0.11 * np.sin(np.pi * t / 0.5) ** 2    # corte do filtro ~100 Hz → ~1 kHz → ~100 Hz
        y = np.zeros(n)
        acc = acc2 = 0.0
        for i in range(n):                         # passa-baixa de 2 polos com corte variável
            acc += al[i] * (x[i] - acc)
            acc2 += al[i] * (acc - acc2)
            y[i] = acc2
        y = y - _lp(y, 160)                        # tira o grave abaixo de ~150 Hz
        y *= np.sin(np.pi * np.clip(t / 0.5, 0, 1)) ** 1.5
    elif kind == "pop":                        # "pop" de elemento entrando (mais corpo que o softpop)
        n = int(0.14 * SR)
        t = np.arange(n) / SR
        f = 180 + 900 * np.exp(-t * 38)
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30)
        y[: int(0.004 * SR)] += rng.standard_normal(int(0.004 * SR)) * 0.4
    elif kind == "engine":                     # caminhão chegando: ronco diesel (rotação cai na freada) e marcha lenta
        dur = 2.1
        n = int(dur * SR)
        t = np.arange(n) / SR
        rpm = np.interp(t, [0, 0.6, 1.15, 1.5, dur], [1.0, 0.95, 0.55, 0.45, 0.45])
        f0 = 38 * rpm + 10                         # pulsos de combustão
        ph = 2 * np.pi * np.cumsum(f0) / SR
        y = sum(np.sin(h * ph + 0.7 * h) / h ** 0.75 for h in range(1, 26))   # harmônicos até ~1 kHz: lê no celular
        fire = np.clip(np.sin(ph / 2), 0, 1) ** 3                              # batida dos cilindros
        clatter = (_lp(rng.standard_normal(n), 8) - _lp(rng.standard_normal(n), 40)) * fire * 3.0
        y = y * (0.55 + 0.45 * fire) + clatter + _lp(rng.standard_normal(n), 50) * 1.5
        y *= np.interp(t, [0, 0.15, 0.9, 1.2, 1.6, dur], [0.0, 0.55, 1.0, 0.8, 0.45, 0.0])   # chega, freia, some
    elif kind == "airbrake":                   # freio a ar do caminhão: estalo de válvula + "tssss" (1–8 kHz)
        n = int(0.75 * SR)
        t = np.arange(n) / SR
        x = rng.standard_normal(n)
        x = _lp(x, 3) - _lp(x, 30)                 # faixa ~1–8 kHz
        y = x * np.interp(t, [0, 0.015, 0.12, 0.75], [0, 1, 0.75, 0]) ** 1.3
        y += 0.35 * np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 40)          # estalo da válvula
    elif kind == "thud":                       # baque surdo (suspensão assentando), com corpo audível no celular
        n = int(0.28 * SR)
        t = np.arange(n) / SR
        f = 90 + 120 * np.exp(-t * 25)
        y = 0.6 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18)
        y += 1.1 * np.sin(2 * np.pi * np.cumsum(f * 2.6) / SR) * np.exp(-t * 22)
        y += 0.7 * np.sin(2 * np.pi * np.cumsum(f * 4.3) / SR) * np.exp(-t * 34)
        y += (_lp(rng.standard_normal(n), 6) - _lp(rng.standard_normal(n), 30)) * np.exp(-t * 60) * 2.6
    elif kind == "scribble":                   # caneta riscando o círculo (~0,35 s)
        n = int(0.38 * SR)
        t = np.arange(n) / SR
        x = rng.standard_normal(n)
        x = _lp(x, 5) - _lp(x, 22)                 # faixa ~2–8 kHz
        strokes = 0.55 + 0.45 * np.sin(2 * np.pi * 7.5 * t) ** 2
        y = x * strokes * np.interp(t, [0, 0.03, 0.3, 0.38], [0, 1, 0.8, 0])
    elif kind == "shimmer":                    # brilho suave (festa/decoração): 5 sininhos subindo + poeira
        n = int(1.0 * SR)
        t = np.arange(n) / SR
        y = np.zeros(n)
        for k, m in enumerate([84, 88, 91, 93, 96]):          # dó–mi–sol–lá–dó (pentatônica)
            i0 = int(k * 0.045 * SR)
            tt = t[: n - i0]
            f = _note(m)
            b = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * f * 2.76 * tt)) * np.exp(-tt * (9 + k))
            y[i0:] += b * (0.55 + 0.1 * k) * _env(len(tt), 0.002, 0.05)
        dust = rng.standard_normal(n)
        dust = dust - _lp(dust, 6)                             # só o agudo (~3 kHz para cima)
        y += dust * np.interp(t, [0, 0.05, 0.35, 1.0], [0, 0.25, 0.08, 0])
        y *= _env(n, 0.003, 0.25)
    elif kind == "pling":                      # notificação curtinha (comentário)
        y = np.concatenate([_pluck(_note(88), 0.09, 1.4), _pluck(_note(95), 0.45, 1.4)])
    elif kind == "impact":                     # impacto grave e curto (gancho), com ataque audível no celular
        n = int(0.7 * SR)
        t = np.arange(n) / SR
        f = 60 + 110 * np.exp(-t * 16)
        y = 0.55 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)       # peso (fone)
        y += 1.0 * np.sin(2 * np.pi * np.cumsum(f * 3.1) / SR) * np.exp(-t * 8)   # corpo (celular)
        y += 0.7 * np.sin(2 * np.pi * np.cumsum(f * 5.2) / SR) * np.exp(-t * 12)
        y += (_lp(rng.standard_normal(n), 4) - _lp(rng.standard_normal(n), 20)) * np.exp(-t * 40) * 2.2
    else:
        raise ValueError(kind)
    y = np.asarray(y, dtype=float)
    return y / (np.max(np.abs(y)) + 1e-9)
