"""Monta o vídeo a partir do edl.json (padrão Cleide Dias).

  python build.py --preview   → preview.mp4 (rápido, para revisar)
  python build.py             → final.mp4   (qualidade de entrega)

Etapas: base.mkv (cortes + zoom suave contínuo + desfoque nas transições + quadro congelado,
áudio da voz) → cards e legendas (re-renderiza se o EDL mudou) → mix de áudio (voz + trilha
+ efeitos, −14 LUFS) → composição final.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

import numpy as np

import brand as B
import sound as S

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd, **kw):
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        sys.exit(f"falhou: {' '.join(map(str, cmd))[:400]}")
    return r


def probe(src):
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
                          "-show_format", src], capture_output=True, text=True).stdout
    return json.loads(out)


def video_geom(info):
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) % 180 == 90:
        w, h = h, w
    hdr = v.get("color_transfer") in ("arib-std-b67", "smpte2084")
    return w, h, hdr, float(v.get("start_time", 0) or 0)


def even(x):
    return int(round(x / 2)) * 2


# Cor: o vídeo sai com a MESMA cor do bruto. Os quadros que passam por pipe (rawvideo) não levam etiqueta de cor;
# sem declarar a entrada, o ffmpeg 9 supunha BT.601 e convertia para BT.709 (imagem ~1 % mais escura e esverdeada,
# descoberto em 27/10). Por isso a entrada do pipe é declarada BT.709 e a saída leva as 3 etiquetas.
BT709 = ["-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
TAG709 = "setparams=range=tv:colorspace=bt709:color_primaries=bt709:color_trc=bt709"
RGBA_TO_YUV = "format=rgba,scale=out_color_matrix=bt709:out_range=tv:flags=bicubic+accurate_rnd,format=yuva420p"


def crop_for(c, sw, sh):
    """Recorte (largura, altura, x, y) no original para a janela 9:16 de um card broll:
    "zoom" ≥ 1 e "anchor" [x, y] no quadro 1080×1920 de zoom 1 (centro da janela)."""
    if sw / sh > 9 / 16:
        bw, bh = even(sh * 9 / 16), sh
    else:
        bw, bh = sw, even(sw * 16 / 9)
    bx, by = (sw - bw) / 2, (sh - bh) / 2
    z = max(1.0, float(c.get("zoom", 1.0)))
    cw, ch = even(bw / z), even(bh / z)
    ax, ay = c.get("anchor", [B.W / 2, B.H / 2])
    cx, cy = bx + ax / B.W * bw, by + ay / B.H * bh
    x = min(max(cx - cw / 2, bx), bx + bw - cw)
    y = min(max(cy - ch / 2, by), by + bh - ch)
    return cw, ch, even(x), even(y)


ZOOM_EASE = 0.5          # s: troca de enquadramento entre trechos vira um zoom suave, centrado na emenda
BLUR_DUR, BLUR_PEAK = 0.40, 16.0   # transição de desfoque: duração (s) e desfoque máximo (px, em 1080)


def ease_in_out(x):
    x = min(1.0, max(0.0, x))
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_sine(x):
    x = min(1.0, max(0.0, x))
    return 0.5 - 0.5 * np.cos(np.pi * x)


def framing(edl, s, z, which="anchor"):
    """Centro (x, y) da janela, no quadro 1080×1920 de zoom 1, para o zoom z no trecho s.
    Com "headroom" no EDL (padrão Cleide), o centro é calculado para o alto da cabeça ficar sempre
    em head_out px do topo: o zoom gira em torno da cabeça e não sobra "teto" em cima dela."""
    if which in s:
        return tuple(s[which])
    if which == "anchor_to" and "anchor" in s and "zoom_to" not in s:
        return tuple(s["anchor"])
    hr = edl.get("headroom")
    if hr and "anchor" not in s:
        return (float(hr.get("x", B.W / 2)), hr["head_src"] - hr["head_out"] / z + (B.H / 2) / z)
    return tuple(s.get("anchor", [B.W / 2, B.H / 2]))


def zoom_track(edl, nfr):
    """(zoom, u, v) de cada quadro de saída: u, v = centro da janela (0–1 da imagem 9:16 inteira).
    Dentro de um trecho o zoom desliza devagar de "zoom" para "zoom_to" (ease senoidal, escala log):
    é o zoom in / zoom out suave. Nas trocas entre trechos, se o enquadramento muda, ele desliza em
    ZOOM_EASE s centrado na emenda (trecho com "zoom_ease": 0 troca seco)."""
    segs = B.segments_out(edl)
    valid = [s for s in edl["segments"] if B.snap(s["end"]) > B.snap(s["start"])]

    def clamp(z, u, v):
        h = 0.5 / z
        return z, min(max(u, h), 1 - h), min(max(v, h), 1 - h)

    def state(j, t):
        s, (a, b, oa, ob) = valid[j], segs[j]
        z0 = max(1.0, float(s.get("zoom", 1.0)))
        z1 = max(1.0, float(s.get("zoom_to", z0)))
        w = float(ease_sine((t - oa) / max(1e-6, ob - oa)))
        z = float(np.exp(np.log(z0) + (np.log(z1) - np.log(z0)) * w))
        if "anchor" in s or not edl.get("headroom"):
            a0, a1 = framing(edl, s, z0), framing(edl, s, z1, "anchor_to")
            ax, ay = a0[0] + (a1[0] - a0[0]) * w, a0[1] + (a1[1] - a0[1]) * w
        else:
            ax, ay = framing(edl, s, z)
        return clamp(z, ax / B.W, ay / B.H)

    ease = float(edl.get("zoom_ease", ZOOM_EASE))
    trans = []                                   # (início, fim, j anterior, j seguinte)
    for j in range(1, len(segs)):
        b = segs[j][2]
        if ease > 0 and float(valid[j].get("zoom_ease", ease)) > 0:
            e0, s1 = state(j - 1, b - 1e-6), state(j, b)
            if max(abs(e0[0] - s1[0]), abs(e0[1] - s1[1]) * 2, abs(e0[2] - s1[2]) * 2) > 1e-3:
                h = min(ease / 2, 0.45 * (segs[j - 1][3] - segs[j - 1][2]), 0.45 * (segs[j][3] - segs[j][2]))
                trans.append((b - h, b + h, j - 1, j))
    out, j = [], 0
    for i in range(nfr):
        t = i / B.FPS
        while j + 1 < len(segs) and t >= segs[j + 1][2] - 1e-6:
            j += 1
        f = state(j, min(t, segs[j][3]))
        for a, b, j0, j1 in trans:
            if a <= t < b:
                f0, f1 = state(j0, a), state(j1, b)
                w = ease_in_out((t - a) / (b - a))
                z = float(np.exp(np.log(f0[0]) + (np.log(f1[0]) - np.log(f0[0])) * w))
                f = clamp(z, f0[1] + (f1[1] - f0[1]) * w, f0[2] + (f1[2] - f0[2]) * w)
                break
        out.append(f)
    return out


def transitions(edl, with_sfx=False):
    """[(t, dur, pico)] das transições de desfoque, no tempo final: trechos com "trans_in": "blur"
    (na emenda) e a lista "transitions" do EDL (ex.: entrada/saída de uma tela).
    "trans_in": {"type": "blur", "blur": 10, "dur": 0.4, "sfx": false} ajusta cada uma.
    with_sfx=True devolve só as que levam o sopro ("air"): por padrão, os cortes de verdade (o original
    pula) e as da lista; troca de tomada que já vem no bruto (b-roll emendado) fica muda."""
    segs = B.segments_out(edl)
    valid = [s for s in edl["segments"] if B.snap(s["end"]) > B.snap(s["start"])]
    out = []
    for j, ((a, b, oa, ob), s) in enumerate(zip(segs, valid)):
        tr = s.get("trans_in")
        if tr and oa > 0:
            tr = tr if isinstance(tr, dict) else {"type": tr}
            jump = a - segs[j - 1][1] > 0.01
            if not with_sfx or tr.get("sfx", jump):
                out.append((oa, float(tr.get("dur", BLUR_DUR)), float(tr.get("blur", BLUR_PEAK))))
    for tr in edl.get("transitions", []):
        if not with_sfx or tr.get("sfx", True):
            out.append((float(tr["t"]), float(tr.get("dur", BLUR_DUR)), float(tr.get("blur", BLUR_PEAK))))
    return sorted(out)


def blur_track(edl, nfr):
    """Desfoque (sigma em px) de cada quadro: sobe e desce em sino, com o pico na emenda."""
    sig = np.zeros(nfr)
    for t0, dur, peak in transitions(edl):
        h = dur / 2
        for i in range(max(0, int((t0 - h) * B.FPS) - 1), min(nfr, int((t0 + h) * B.FPS) + 2)):
            tc = (i + 0.5) / B.FPS                # meio do quadro: os dois quadros da emenda ficam iguais
            x = abs(tc - t0) / h
            if x < 1:
                sig[i] = max(sig[i], peak * np.cos(np.pi / 2 * x) ** 2)
    return sig


# Vídeo HDR do iPhone → SDR: só a conversão (tonemap mobius npl=203), sem ajuste de saturação/contraste
# (o "eq" herdado do modelo antigo saiu em 27/10: a cor fica a do bruto).
HDR_CHAIN = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,"
             "tonemap=tonemap=mobius:param=0.35:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def build_base(edl, src):
    """Cortes no grid de quadros (ffmpeg) numa tela de trabalho k × 1080×1920 sem zoom; o zoom de cada
    quadro é aplicado aqui com subpixel (cv2.warpAffine), para as trocas de enquadramento serem suaves."""
    import cv2
    info = probe(src)
    sw, sh, is_hdr, vst = video_geom(info)
    want_hdr = edl.get("hdr", "auto")
    hdr = is_hdr if want_hdr == "auto" else bool(want_hdr)
    segs = B.segments_out(edl)
    hold = B.snap(edl.get("hold", 0.0))
    total = B.total_duration(edl)
    nfr = B.total_frames(edl)
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    n = len(segs)
    if sw / sh > 9 / 16:                         # área 9:16 do original (zoom 1)
        bw, bh = even(sh * 9 / 16), sh
    else:
        bw, bh = sw, even(sw * 16 / 9)
    bx, by = even((sw - bw) / 2), even((sh - bh) / 2)
    track = zoom_track(edl, nfr)
    blur = blur_track(edl, nfr)
    # tela de trabalho: grande o bastante para o maior zoom sem ampliar além do original
    k = max(1.0, min(max(z for z, _, _ in track), bw / B.W))
    CW, CH = even(B.W * k), even(B.H * k)
    d_ = edl["_dir"]

    # 1) áudio da voz, cortado nos mesmos quadros (antes, para o encoder já ter o arquivo pronto)
    wav = os.path.join(d_, "base_audio.wav")
    fa = []
    if has_audio:
        fa.append(f"[0:a]asetpts=PTS-{vst}/TB,aresample={S.SR}:async=1:first_pts=0,asplit={n}" +
                  "".join(f"[a{i}]" for i in range(n)))
        for i, (a, b, oa, ob) in enumerate(segs):
            sf, ef = int(round(a * B.FPS)), int(round(b * B.FPS))
            d = (ef - sf) / B.FPS
            fa.append(f"[a{i}]atrim=start={sf / B.FPS:.6f}:end={ef / B.FPS:.6f},asetpts=PTS-STARTPTS,"
                      f"aresample={S.SR}:first_pts=0,apad=whole_dur={d:.6f},atrim=duration={d:.6f}[as{i}]")
        fa.append("".join(f"[as{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,"
                  f"apad=whole_dur={total:.6f},atrim=duration={total:.6f}[aout]")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-filter_complex", ";".join(fa), "-map", "[aout]",
             "-c:a", "pcm_s16le", "-ar", str(S.SR), "-ac", "2", wav])
    else:
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anullsrc=r={S.SR}:cl=stereo",
             "-t", f"{total:.6f}", "-c:a", "pcm_s16le", wav])

    # 2) vídeo: cortes + cor + congelado, sem zoom, em k × 1080×1920 → pipe
    f = [f"[0:v]setpts=PTS-{vst}/TB,fps={B.FPS},split={n}" + "".join(f"[v{i}]" for i in range(n))]
    for i, (a, b, oa, ob) in enumerate(segs):
        sf, ef = int(round(a * B.FPS)), int(round(b * B.FPS))
        f.append(f"[v{i}]trim=start_frame={sf}:end_frame={ef},setpts=PTS-STARTPTS,"
                 f"crop={bw}:{bh}:{bx}:{by},scale={CW}:{CH}:flags=lanczos,setsar=1[vs{i}]")
    f.append("".join(f"[vs{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vc]")
    post = HDR_CHAIN if hdr else "format=yuv420p"
    hold_f = f",tpad=stop_mode=clone:stop_duration={hold:.6f}" if hold > 0 else ""
    # o concat do ffmpeg 7 sai sem taxa de quadros e o tpad não gera o congelado: numera os quadros
    # (settb+setpts=N, sem arredondar emendas) e reafirma 30 fps — quadros idênticos aos do concat
    f.append(f"[vc]settb=1/{B.FPS},setpts=N,fps={B.FPS}:eof_action=pass,{post}{hold_f}[vout]")
    dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", src, "-filter_complex", ";".join(f),
                            "-map", "[vout]", "-frames:v", str(nfr), "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "yuv420p",
                            "-s", f"{B.W}x{B.H}", "-r", str(B.FPS), *BT709, "-i", "-", "-i", wav, "-map", "0:v",
                            "-map", "1:a", "-frames:v", str(nfr), "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
                            "-pix_fmt", "yuv420p", *BT709, "-c:a", "pcm_s16le", "-ar", str(S.SR), "-ac", "2",
                            os.path.join(d_, "base.mkv")], stdin=subprocess.PIPE)
    print(f"base: {n} trechos, {B.body_duration(edl):.2f}s + hold {hold:.2f}s, "
          f"{'HDR→SDR' if hdr else 'SDR (cor original)'}, zoom suave {edl.get('zoom_ease', ZOOM_EASE)}s "
          f"(tela {CW}×{CH}), {len(transitions(edl))} transições de desfoque")

    # 3) zoom quadro a quadro: saída (x, y) ← tela (cx + (x + ½ − W/2)·s − ½, …), s = k/zoom
    ysz, csz = CW * CH, (CW // 2) * (CH // 2)
    last, missing = None, 0
    for i in range(nfr):
        raw = dec.stdout.read(ysz + 2 * csz)
        if len(raw) == ysz + 2 * csz:
            last = raw
        elif last is None:
            sys.exit("base: o ffmpeg não entregou quadros")
        else:
            missing += 1
        buf = np.frombuffer(last, np.uint8)
        z, u, v = track[i]
        sx, sy = CW / (B.W * z), CH / (B.H * z)
        planes = []
        for pl, (pw, ph), div, interp in ((buf[:ysz].reshape(CH, CW), (B.W, B.H), 1, cv2.INTER_CUBIC),
                                          (buf[ysz:ysz + csz].reshape(CH // 2, CW // 2), (B.W // 2, B.H // 2), 2,
                                           cv2.INTER_LINEAR),
                                          (buf[ysz + csz:].reshape(CH // 2, CW // 2), (B.W // 2, B.H // 2), 2,
                                           cv2.INTER_LINEAR)):
            cx, cy = u * CW / div, v * CH / div
            M = np.float32([[sx, 0, cx + (0.5 - pw / 2) * sx - 0.5], [0, sy, cy + (0.5 - ph / 2) * sy - 0.5]])
            p_ = cv2.warpAffine(pl, M, (pw, ph), flags=interp | cv2.WARP_INVERSE_MAP,
                                borderMode=cv2.BORDER_REPLICATE)
            if blur[i] > 0.3:                    # transição: desfoque no quadro inteiro (croma na metade)
                p_ = cv2.GaussianBlur(p_, (0, 0), blur[i] / div, borderType=cv2.BORDER_REPLICATE)
            planes.append(p_)
        enc.stdin.write(b"".join(p.tobytes() for p in planes))
    dec.stdout.close()
    enc.stdin.close()
    if dec.wait() != 0 or enc.wait() != 0:
        sys.exit("base: o ffmpeg falhou ao montar base.mkv")
    if missing:
        print(f"base: ATENÇÃO — faltaram {missing} quadros no corte (repeti o último)")
    os.remove(wav)


# pico de cada efeito em dB relativo ao RMS da fala. Padrão Cleide (04/11: "efeitos sonoros simples, nada
# exagerado"): poucos efeitos, suaves, ~8–14 dB abaixo da voz; só no que aparece na tela
SFX_DB = {"whoosh": 2, "air": -1, "pop": 4, "softpop": 1, "tap": 0, "chime": 0, "shimmer": 0, "click": 1,
          "pling": 1, "paper": -2}


def read_audio(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vn", "-f", "f32le", "-ac", "2",
                          "-ar", str(S.SR), "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def write_wav(path, x):
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ac", "2", "-ar", str(S.SR),
                          "-i", "-", "-c:a", "pcm_s24le", path], stdin=subprocess.PIPE)
    p.stdin.write(x.astype(np.float32).tobytes())
    p.stdin.close()
    p.wait()


def db(x):
    return 20 * np.log10(max(x, 1e-9))


def mix_audio(edl, d):
    voice = read_audio(os.path.join(d, "base.mkv"))
    if edl.get("mute_source"):
        voice[:] = 0
    n = int(round(B.total_duration(edl) * S.SR))
    voice = np.pad(voice, ((0, max(0, n - len(voice))), (0, 0)))[:n]
    blk = S.SR // 20
    rms = np.sqrt(np.mean(voice[: len(voice) // blk * blk].reshape(-1, blk, 2) ** 2, axis=(1, 2)))
    active = rms[rms > 10 ** (-45 / 20)]
    v_db = db(np.sqrt(np.mean(active ** 2))) if len(active) else -20.0
    out = voice.copy()
    events = []
    mcfg = edl.get("music", {"style": "calm", "db": -24})
    if mcfg:
        if mcfg.get("file"):
            # trilha enviada pela agência (padrão Cleide: calma e sofisticada, como a do 6A5B), estendida
            # até a duração do vídeo repetindo compassos e mantendo o final original (music_extend.py)
            import music_extend as MX
            src_m = os.path.normpath(os.path.join(d, mcfg["file"]))
            cache = os.path.join(d, "music_ext.wav")
            ck = json.dumps([src_m, os.path.getmtime(src_m), round(n / S.SR, 3)])
            if os.path.exists(cache) and os.path.exists(cache + ".key") and open(cache + ".key").read() == ck:
                m = read_audio(cache)
            else:
                m, rep = MX.extend(src_m, n / S.SR)
                write_wav(cache, m)
                open(cache + ".key", "w").write(ck)
                json.dump(rep, open(os.path.join(d, "music_ext.json"), "w"), ensure_ascii=False, indent=1)
                print(f"trilha: {os.path.basename(src_m)} {rep['music_s']}s → {rep.get('result_s', n / S.SR):.2f}s "
                      f"({rep['mode']})")
            m = np.pad(m, ((0, max(0, n - len(m))), (0, 0)))[:n]
            act = m[np.abs(m).max(1) > 10 ** (-40 / 20)]
            m_rms = np.sqrt(np.mean(act ** 2)) if len(act) else 1e-4
        else:
            m = S.music(n / S.SR, mcfg.get("style", "calm"))
            m = np.pad(m, ((0, max(0, n - len(m))), (0, 0)))[:n]
            m_rms = np.sqrt(np.mean(m ** 2))
        g = 10 ** ((v_db + mcfg.get("db", -24) - db(m_rms)) / 20)
        if edl.get("mute_source"):
            g = 10 ** ((-20 - db(m_rms)) / 20)
        env = np.full(n, g)
        last_word = B.body_duration(edl)
        words = B.load_words(edl)
        if words:
            last_word = words[-1]["end"]
        i0 = int(last_word * S.SR)
        ramp = int(0.4 * S.SR)
        boost = 10 ** (mcfg.get("end_boost_db", 10) / 20)
        if i0 < n and not edl.get("mute_source"):
            env[i0:i0 + ramp] *= np.linspace(1, boost, len(env[i0:i0 + ramp]))
            env[i0 + ramp:] *= boost
        out += m * env[:, None]
    # efeitos: eventos dos cards + trocas de enquadramento (≥ 4 s de distância)
    idx_p = os.path.join(d, "cards", "index.json")
    if os.path.exists(idx_p):
        for c in json.load(open(idx_p)):
            events += c.get("events", [])
    cap_sfx = os.path.join(d, "captions_sfx.json")
    if edl.get("captions", {}).get("style") and os.path.exists(cap_sfx):
        # impacto no gancho, pop na caixa, rabisco no círculo, dinheiro nos valores, clique no "clique"
        events += [dict(e, src="legenda") for e in json.load(open(cap_sfx))]
    events += edl.get("sfx_events", [])
    if edl.get("sfx", "auto") == "auto":
        # "air" (sopro suave, 0,5 s) com o pico no meio de cada transição de desfoque
        for t0, dur, peak in transitions(edl, with_sfx=True):
            events.append({"t": max(0.0, t0 - 0.25), "kind": "air", "auto": True})
    events.sort(key=lambda e: e["t"])
    # sem amontoar: som da legenda até 0,3 s antes ou 0,6 s depois de um som de card sai (fica o do card)
    card_t = [e["t"] for e in events if not e.get("auto") and e.get("src") != "legenda"]
    events = [e for e in events if e.get("src") != "legenda" or not any(-0.3 < e["t"] - x < 0.6 for x in card_t)]
    kept, last = [], -99
    opaque = B.opaque_windows(edl)
    manual = [e["t"] for e in events if not e.get("auto")]
    for e in events:
        # sopro automático da transição: no máx. 1 a cada 2,5 s e nunca colado (< 0,6 s) em outro efeito
        if e.get("auto") and (e["t"] - last < 2.5 or any(abs(e["t"] - m) < 0.6 for m in manual)):
            continue
        kept.append(e)
        last = e["t"]
    if edl.get("sfx", "auto"):
        for k, e in enumerate(kept):
            y = S.sfx(e["kind"], seed=k)
            g = 10 ** ((v_db + SFX_DB.get(e["kind"], -8)) / 20)   # pico relativo à voz (RMS da fala)
            i = int(e["t"] * S.SR)
            seg = y[: max(0, min(len(y), n - i))] * g
            out[i:i + len(seg)] += seg[:, None]
    raw = os.path.join(d, "mix_raw.wav")
    write_wav(raw, out)
    # loudnorm em duas passadas: −14 LUFS, pico ≤ −1,5 dBTP
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", raw, "-af",
                        "loudnorm=I=-14:TP=-2:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    js = json.loads(r[r.rindex("{"):r.rindex("}") + 1])
    af = (f"loudnorm=I=-14:TP=-2:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:"
          f"linear=true,aresample={S.SR}")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", af, "-c:a", "pcm_s24le",
         os.path.join(d, "mix.wav")])
    print(f"áudio: voz {v_db:.1f} dBFS, trilha {'arquivo ' if mcfg and mcfg.get('file') else ''}"
          f"{mcfg.get('db', -24) if mcfg else 'sem'} dB, "
          f"{len(kept)} efeitos")
    return kept


def stale(target, *deps):
    if not os.path.exists(target):
        return True
    t = os.path.getmtime(target)
    return any(os.path.exists(p) and os.path.getmtime(p) > t for p in deps)


def version_old(d, name, edl_path):
    p = os.path.join(d, name)
    if not os.path.exists(p):
        return
    base, ext = os.path.splitext(name)
    k = 1
    while os.path.exists(os.path.join(d, f"{base}_v{k}{ext}")):
        k += 1
    os.replace(p, os.path.join(d, f"{base}_v{k}{ext}"))
    if os.path.exists(edl_path):
        shutil.copy2(edl_path, os.path.join(d, f"edl_v{k}.json"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--edl", default="edl.json")
    ap.add_argument("--force", action="store_true", help="refaz base, cards e legendas")
    a = ap.parse_args()
    edl = B.load_edl(a.edl)
    d = edl["_dir"]
    src = os.path.normpath(os.path.join(d, edl["source"]))
    edl_path = os.path.abspath(a.edl)

    # 1) base (só refaz se cortes/fonte/hold/cor mudaram)
    key = hashlib.md5(json.dumps([edl["source"], edl["segments"], edl.get("hold"), edl.get("hdr"),
                                  "zoom-suave-2", edl.get("zoom_ease", ZOOM_EASE), edl.get("headroom"),
                                  edl.get("transitions", [])],
                                 sort_keys=True).encode()).hexdigest()
    kp = os.path.join(d, "base.key")
    if a.force or not os.path.exists(os.path.join(d, "base.mkv")) or \
            not os.path.exists(kp) or open(kp).read() != key:
        build_base(edl, src)
        open(kp, "w").write(key)
    else:
        print("base: sem mudanças nos cortes, reaproveitando base.mkv")

    # 1b) onde está a pessoa (rosto → legenda abaixo do pescoço; recorte → títulos atrás dela)
    py = sys.executable
    import person as PS
    pj = os.path.join(d, "person.json")
    try:
        old = json.load(open(pj))
        fresh = old.get("key") == open(kp).read() and \
            [list(w) for w in old.get("windows", [])] == [list(w) for w in PS.behind_windows(edl)]
    except Exception:
        fresh = False
    if a.force or not fresh:
        run([py, os.path.join(HERE, "person.py"), edl_path])
        # a legenda e os cards dependem da posição da pessoa
        for f in ("captions.mov", os.path.join("cards", "index.json")):
            if os.path.exists(os.path.join(d, f)):
                os.remove(os.path.join(d, f))
    B._person.clear()

    # 2) cards e legendas
    if edl.get("cards") and (a.force or stale(os.path.join(d, "cards", "index.json"), edl_path)):
        run([py, os.path.join(HERE, "animations", "cleide_cards.py"), edl_path])
    cap = edl.get("captions")
    cap_file = os.path.join(d, "captions.mov")
    if cap and cap.get("style") and os.path.exists(os.path.join(d, cap.get("words_file", "transcript.json"))):
        if a.force or stale(cap_file, edl_path, os.path.join(d, cap.get("words_file", "transcript.json"))):
            run([py, os.path.join(HERE, "animations", "captions_cleide.py"), edl_path])
    else:
        cap_file = None
        print("legendas: desligadas ou sem transcript.json")

    # 3) áudio
    mix_audio(edl, d)

    # 4) composição
    total = B.total_duration(edl)
    nfr = B.total_frames(edl)
    inputs = ["-i", os.path.join(d, "base.mkv")]
    fc, cur, k = ["[0:v]split=2[base0][base1]"], "[base0]", 1
    cards = json.load(open(os.path.join(d, "cards", "index.json"))) if edl.get("cards") and \
        os.path.exists(os.path.join(d, "cards", "index.json")) else []
    half = 0.5 / B.FPS

    def overlay(c, label):
        nonlocal cur, k
        inputs.extend(["-i", os.path.join(d, c["file"])])
        at, dur = c["at"], c["dur"]
        conv = RGBA_TO_YUV if c["alpha"] else "null"
        fc.append(f"[{k}:v]{conv},setpts=PTS-STARTPTS+{max(0, at - half):.6f}/TB[c{k}]")
        fc.append(f"{cur}[c{k}]overlay=eof_action=repeat:enable='between(t,{at - 1e-4:.6f},{at + dur - half:.6f})'"
                  f"[o{k}]")
        cur = f"[o{k}]"
        k += 1

    for c in cards:
        if not c["alpha"]:                       # telas opacas (fotos) por baixo de tudo
            overlay(c, "op")
    logo = os.path.join(B.ASSETS, B.LOGO_FILE)
    logo = logo if os.path.exists(logo) else None
    if edl.get("logo", False) and logo:          # padrão Cleide: sem logo fixo (nada no alto sem título)
        inputs.extend(["-loop", "1", "-framerate", str(B.FPS), "-t", f"{total + 1 / B.FPS:.6f}", "-i", logo])
        off = [(c["at"], c["at"] + c["dur"]) for c in cards if c.get("hide_logo")] + \
            [tuple(w) for w in edl.get("logo_hide", [])]          # EDL: trechos sem logo (ex.: close com a cabeça no alto)
        cond = "+".join(f"between(t,{x - 1e-4:.4f},{y:.4f})" for x, y in off) or "0"
        fc.append(f"[{k}:v]scale={B.LOGO_W}:-1,format=rgba,colorchannelmixer=aa={B.LOGO_OPACITY},{RGBA_TO_YUV}[lg]")
        pos = {"top-center": f"x=(W-w)/2:y={B.LOGO_Y}",
               "top-right": f"x={B.SAFE[2]}-w-10:y={B.LOGO_Y}",
               "bottom-center": f"x=(W-w)/2:y={B.SAFE[3]}-h-6"}[B.LOGO_POS]
        fc.append(f"{cur}[lg]overlay={pos}:enable='not({cond})'[o{k}]")
        cur = f"[o{k}]"
        k += 1
    elif edl.get("logo", False):
        print(f"logo: assets/{B.LOGO_FILE} não encontrado — vídeo sai sem logo")
    behind = [c for c in cards if c["alpha"] and c["type"] != "end" and c.get("behind")]
    front = [c for c in cards if c["alpha"] and c["type"] != "end" and not c.get("behind") and not c.get("top")]
    for c in behind:                         # capa, título, lista, tag: por baixo da pessoa
        overlay(c, "ov")
    mask = os.path.join(d, "person_mask.mkv")
    if behind and os.path.exists(mask):
        inputs.extend(["-i", mask])
        cond = "+".join(f"between(t,{c['at'] - 1e-4:.4f},{c['at'] + c['dur']:.4f})" for c in behind)
        # com b-roll / foto / antes-depois na tela a pessoa da base não aparece: nada de recolar ela por cima
        opaque = "+".join(f"between(t,{c['at'] - 1e-4:.4f},{c['at'] + c['dur']:.4f})" for c in cards if not c["alpha"])
        if opaque:
            cond = f"({cond})*not({opaque})"
        fc.append(f"[{k}:v]format=gray[pm]")
        fc.append(f"[base1]format=yuva420p[pb];[pb][pm]alphamerge[pp]")      # sem passar por RGB (cor igual)
        fc.append(f"{cur}[pp]overlay=enable='{cond}'[o{k}]")
        cur = f"[o{k}]"
        k += 1
    else:
        fc.append("[base1]nullsink")
    for c in front:                          # preço, serviço, etiqueta: na frente (abaixo do pescoço)
        overlay(c, "ov")
    if cap_file:
        inputs.extend(["-i", cap_file])
        fc.append(f"[{k}:v]{RGBA_TO_YUV}[cap]")
        fc.append(f"{cur}[cap]overlay=eof_action=pass[o{k}]")
        cur = f"[o{k}]"
        k += 1
    for c in cards:                          # brilho de luz: por cima da legenda também
        if c.get("top") and c["type"] != "end":
            overlay(c, "top")
    for c in cards:
        if c["type"] == "end":
            overlay(c, "end")
    fc.append(f"{cur}{TAG709},format=yuv420p[vout]")
    inputs.extend(["-i", os.path.join(d, "mix.wav")])
    aidx = k

    out_name = "preview.mp4" if a.preview else "final.mp4"
    version_old(d, out_name, edl_path)
    enc = ["-preset", "veryfast", "-crf", "21"] if a.preview else ["-preset", "slow", "-crf", "17"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats", *inputs, "-filter_complex", ";".join(fc),
           "-map", "[vout]", "-map", f"{aidx}:a", "-frames:v", str(nfr), "-r", str(B.FPS),
           "-c:v", "libx264", *enc, "-pix_fmt", "yuv420p", *BT709,
           "-c:a", "aac", "-b:a", "192k", "-ar", str(S.SR), "-af", f"atrim=duration={total:.6f}",
           "-movflags", "+faststart+write_colr", os.path.join(d, out_name)]
    run(cmd)
    print(f"→ {out_name}: {nfr} quadros ({total:.2f}s)")


if __name__ == "__main__":
    main()
