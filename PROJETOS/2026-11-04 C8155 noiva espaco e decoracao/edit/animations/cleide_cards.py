"""Grafismos Cleide Dias → cards/*.mov + cards/index.json

Tipos (EDL "cards"; "at"/"dur" no tempo do vídeo FINAL):
  pills   lista em pílulas cinza translúcidas, uma embaixo da outra, cada uma entra quando é falada
          ("cansada" / "irritada" e "mais leveza" / "mais clareza" da referência). Na frente da
          pessoa, do meio do pescoço para baixo (esconde a legenda no trecho).
          {"type": "pills", "at": 7.8, "dur": 3.3, "items": [["A entrada", 0.0], ["A cerimônia", 1.0]]}
          (o 2º número é o atraso em s a partir de "at"; "sync": true acha o tempo no transcript)
  screen  tela clara (off-white com sombras de folhagem) com a frase em texto escuro, palavra a
          palavra no tempo da fala, uma palavra em cursiva e o círculo tracejado dourado em volta
          dela (as telas brancas da referência). Entra e sai desfocando.
          {"type": "screen", "at": 13.7, "dur": 3.6, "lines": ["para criar", "um projeto que",
           "*valoriza*", "cada espaço."], "circle": "valoriza"}
          *palavra* = cursiva · **palavra** = negrito.
  leak    brilho de luz quente (rosé + dourado) atravessando a tela, para transição. 1–2 por vídeo.
          {"type": "leak", "at": 3.0, "dur": 0.6}
  end     card final: tela clara, "Cleide Dias" em cursiva se escrevendo, filete dourado,
          "DECORAÇÃO DE EVENTOS" e o botão. {"type": "end", "lead": -0.2}
          (lead negativo = começa um pouco antes do fim da fala, por cima do congelado)

Uso:  python animations/cleide_cards.py [edl.json]
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

import brand as B  # noqa: E402
from frames import FrameWriter  # noqa: E402

EDL = None


def nframes(dur):
    return int(round(dur * B.FPS))


def norm(w):
    return re.sub(r"[^\wáàâãéêíóôõúüç]", "", w.lower())


def edge_fade(t, dur, a=0.2, b=0.2):
    """Entrada/saída (0→1→0) com ease."""
    return min(B.ease_out_cubic(t / a) if a else 1.0, B.ease_in_out((dur - t) / b) if b else 1.0)


def text_img(text, fnt, color, halo=False):
    """Texto na cor dada; (imagem, ox, oy) com (ox, oy) = origem da linha de base."""
    s = fnt.size
    pad = int(s * 0.5)
    bb = fnt.getbbox(text, anchor="ls")
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    ox, oy = pad - bb[0], pad - bb[1]
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).text((ox, oy), text, font=fnt, fill=255, anchor="ls")
    out = Image.new("RGBA", (w, h), B.INK + (0,))
    if halo:
        a = np.maximum(np.asarray(m.filter(ImageFilter.GaussianBlur(s * 0.07)), np.float32) * 0.55,
                       np.asarray(m.filter(ImageFilter.GaussianBlur(s * 0.28)), np.float32) * 0.42)
        out.putalpha(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)))
    fill = Image.new("RGBA", (w, h), tuple(color[:3]) + (0,))
    fill.putalpha(m)
    out.alpha_composite(fill)
    return out, ox, oy


def words_in(t0, t1):
    """Palavras do transcript (tempo final) entre t0 e t1."""
    return [w for w in B.load_words(EDL) if t0 - 0.15 <= w["start"] < t1]


# ------------------------------------------------------------------ pills
def render_pills(c, path):
    s = c.get("size", B.CAPTION_SIZE)
    fnt = B.font(B.PILL_FONT, s)
    cap = -fnt.getbbox("H", anchor="ls")[1]
    ph = cap * 2.15
    gap = c.get("gap", s * 0.55)
    items = []
    ws = words_in(c["at"], c["at"] + c["dur"]) if c.get("sync") else []
    for it in c["items"]:
        txt, dt = (it, None) if isinstance(it, str) else (it[0], it[1])
        if dt is None and ws:                                   # tempo da 1ª palavra do item no transcript
            first = norm(txt.split()[0])
            hit = next((w for w in ws if norm(w["word"]) == first and w["start"] >= c["at"] - 0.15
                        and all(w["start"] > x[1] + c["at"] for x in items)), None)
            dt = (hit["start"] - c["at"]) if hit else (len(items) * 0.8)
        items.append((txt, max(0.0, dt or 0.0)))
    imgs = [text_img(t, fnt, B.WHITE, halo=True) for t, _ in items]
    widths = [fnt.getlength(t) + s * 0.95 for t, _ in items]
    total_h = len(items) * ph + (len(items) - 1) * gap
    neck = B.neck_line(EDL, c["at"], c["at"] + c["dur"])
    top = c.get("y") or ((neck + B.NECK_GAP) if neck is not None else B.CAPTION_CY - total_h / 2)
    top = min(top, B.SAFE[3] - 8 - total_h)
    cx = c.get("x", B.W / 2)
    fw = FrameWriter(path, alpha=True)
    n = nframes(c["dur"])
    boxes = []
    for f in range(n):
        t = f / B.FPS
        im = Image.new("RGBA", (B.W, B.H), (0, 0, 0, 0))
        out = B.clamp01((t - (c["dur"] - 0.17)) / 0.17)          # todas somem juntas, desfocando
        for i, ((txt, dt), (ti, ox, oy), pw) in enumerate(zip(items, imgs, widths)):
            k = (t - dt) * B.FPS / 6
            if k < 0:
                continue
            e = B.ease_out_cubic(k)
            y = top + i * (ph + gap)
            pill = B.rounded((int(pw), int(ph)), int(ph / 2), B.PILL + (B.PILL_ALPHA,))
            layer = Image.new("RGBA", (int(pw) + 2 * int(s), int(ph) + 2 * int(s)), (0, 0, 0, 0))
            layer.alpha_composite(pill, (int(s), int(s)))
            layer.alpha_composite(ti, (int(s + pw / 2 - fnt.getlength(txt) / 2 - ox),
                                       int(s + ph / 2 + cap / 2 - oy)))
            layer = B.premul_blur(layer, 7 * (1 - e) + 8 * out)
            layer = B.scale_rgba(layer, 0.88 + 0.12 * e)
            B.paste_center(im, layer, cx, y + ph / 2 + 8 * (1 - e), alpha=min(1.0, 0.15 + e) * (1 - out),
                           boxes=boxes if f == n - 8 else None, tag=txt)
        fw.write(im)
    fw.close()
    ev = [{"t": dt, "kind": "tap"} for _, dt in items]
    return boxes, ev, True


# ------------------------------------------------------------------ screen
def parse_line(line):
    """'que *valoriza* **cada**' → [(palavra, estilo)]"""
    out = []
    for tok in re.findall(r"\*\*[^*]+\*\*|\*[^*]+\*|\S+", line):
        if tok.startswith("**"):
            out += [(w, "bold") for w in tok[2:-2].split()]
        elif tok.startswith("*"):
            out.append((tok[1:-1], "script"))
        else:
            out.append((tok, "text"))
    return out


def render_screen(c, path):
    dur = c["dur"]
    s = c.get("size", 84)
    f_t, f_b = B.font("Sans Bold", s), B.font("Sans Bold", s)        # tela clara: texto em negrito (referência)
    f_s = B.font(B.SCRIPT_FONT, s * 2.1)
    lines = [parse_line(ln) for ln in c["lines"]]
    # tempos: cada palavra entra quando é falada (transcript); sem casar, entra escalonada
    ws = words_in(c["at"], c["at"] + dur)
    wi, timed = 0, []
    for ln in lines:
        row = []
        for word, st in ln:
            k = wi
            while k < len(ws) and norm(ws[k]["word"]) != norm(word):
                k += 1
            if k < len(ws):
                tt, wi = ws[k]["start"] - c["at"], k + 1
            else:
                tt = (timed[-1][-1][2] + 0.18) if timed and timed[-1] else (row[-1][2] + 0.18 if row else 0.15)
            row.append((word, st, max(0.12, tt)))
        timed.append(row)
    # layout centrado; cursiva encosta nas linhas vizinhas
    cap = -f_t.getbbox("H", anchor="ls")[1]
    rows, y = [], 0.0
    for i, row in enumerate(timed):
        pieces, x = [], 0.0
        for word, st, tt in row:
            fnt = f_s if st == "script" else f_b if st == "bold" else f_t
            col = B.CHARCOAL
            img = text_img(word, fnt, col)
            pieces.append({"img": img, "x": x, "w": fnt.getlength(word), "t": tt, "st": st, "word": word})
            x += fnt.getlength(word) + f_t.getlength(" ")
        w = x - f_t.getlength(" ")
        script = any(p["st"] == "script" for p in pieces)
        asc = max((-f_s.getbbox(p["word"], anchor="ls")[1] if p["st"] == "script" else cap) for p in pieces)
        desc = max((f_s.getbbox(p["word"], anchor="ls")[3] if p["st"] == "script" else s * 0.2) for p in pieces)
        if i:
            y += s * 0.16 + (s * 0.30 if script or rows[-1]["script"] else 0) - (asc * 0.10 if script else 0)
        rows.append({"pieces": pieces, "w": w, "base": y + asc, "script": script})
        y += asc + desc
    block_h = y
    top = c.get("cy", 900) - block_h / 2
    circle_word = norm(c.get("circle", ""))
    target = None
    for r in rows:
        for p in r["pieces"]:
            if circle_word and norm(p["word"]) == circle_word:
                target = (r, p)
    fw = FrameWriter(path, alpha=True)
    n = nframes(dur)
    boxes = []
    ent, ext = c.get("in", 0.25), c.get("out", 0.25)
    for f in range(n):
        t = f / B.FPS
        bg = B.paper_background(t, seed=c.get("seed", 3))
        im = bg.copy()
        for r in rows:
            lx = B.W / 2 - r["w"] / 2
            for p in r["pieces"]:
                k = (t - p["t"]) * B.FPS / (7 if p["st"] == "script" else 5)
                if k < 0:
                    continue
                e = B.ease_out_cubic(k)
                ti, ox, oy = p["img"]
                px, py = lx + p["x"] - ox, top + r["base"] - oy
                layer = B.premul_blur(ti, (9 if p["st"] == "script" else 6) * (1 - e))
                if p["st"] == "script":
                    layer = B.scale_rgba(layer, 1.12 - 0.12 * e)
                B.paste_center(im, layer, px + ti.width / 2, py + ti.height / 2 + 5 * (1 - e),
                               alpha=min(1.0, 0.15 + 1.1 * k), boxes=boxes if f == n - 12 else None, tag=p["word"])
        if target:
            r, p = target
            k = (t - p["t"] - 0.25) / 0.7
            if k > 0:
                bb = f_s.getbbox(p["word"], anchor="ls")
                rx, ry = p["w"] / 2 + s * 0.80, (bb[3] - bb[1]) / 2 + s * 0.12
                el = B.dashed_ellipse(rx, ry, B.ease_in_out(k), color=B.GOLD, thick=6)
                ccx = B.W / 2 - r["w"] / 2 + p["x"] + p["w"] / 2
                ccy = top + r["base"] + (bb[1] + bb[3]) / 2
                B.paste_center(im, el, ccx, ccy)
        # entrada e saída: a tela inteira desfoca e some (por baixo, a base também desfoca: "transitions")
        a_in = B.ease_out_cubic(t / ent) if ent else 1.0
        a_out = B.ease_in_out((dur - t - 1 / B.FPS) / ext) if ext else 1.0
        k = min(a_in, a_out)
        if k < 0.999:
            im = B.with_alpha(B.premul_blur(im, 14 * (1 - k)), k)
        fw.write(im)
    fw.close()
    return boxes, [{"t": 0.0, "kind": "air"}], True


# ------------------------------------------------------------------ leak
def render_leak(c, path):
    """Brilho de luz quente: duas manchas (rosé e dourado) atravessam a tela da esquerda para a direita,
    com pico de intensidade no meio do card."""
    dur = c["dur"]
    n = nframes(dur)
    sw, sh = B.W // 4, B.H // 4
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    rose = np.array(c.get("color1", B.ROSE), np.float32)
    gold = np.array(c.get("color2", (255, 196, 128)), np.float32)
    peak = c.get("strength", 0.42)                  # sutil: o rosto continua visível no pico
    fw = FrameWriter(path, alpha=True)
    for f in range(n):
        u = f / max(1, n - 1)
        inten = math.sin(math.pi * u) ** 1.4 * peak
        cx1, cy1 = (-0.3 + 1.2 * u) * sw, 0.25 * sh
        cx2, cy2 = (1.1 - 0.9 * u) * sw, 0.85 * sh
        g1 = np.exp(-(((xx - cx1) / (0.55 * sw)) ** 2 + ((yy - cy1) / (0.45 * sh)) ** 2))
        g2 = np.exp(-(((xx - cx2) / (0.6 * sw)) ** 2 + ((yy - cy2) / (0.4 * sh)) ** 2))
        a = np.clip((g1 * 0.95 + g2 * 0.8) * inten + 0.05 * inten, 0, 1)
        col = (rose[None, None] * g1[..., None] + gold[None, None] * g2[..., None]) / (g1 + g2 + 1e-4)[..., None]
        col = col * 0.75 + 255 * 0.25                       # puxa para o claro (luz)
        rgba = np.dstack([np.clip(col, 0, 255), a * 255]).astype(np.uint8)
        im = Image.fromarray(rgba, "RGBA").resize((B.W, B.H), Image.BICUBIC)
        fw.write(im)
    fw.close()
    return [], [], True


# ------------------------------------------------------------------ end
def render_end(c, path, dur):
    name = c.get("name", B.BRAND)
    tagline = c.get("tagline", B.TAGLINE).upper()
    cta = c.get("cta", B.CTA)
    handle = c.get("handle", B.HANDLE)
    f_name = B.font(B.SCRIPT_FONT, c.get("name_size", 200))
    while f_name.getlength(name) > B.SAFE[2] - B.SAFE[0] - 60:
        f_name = B.font(B.SCRIPT_FONT, f_name.size - 6)
    f_tag = B.font("Sans Medium", 38)
    f_btn = B.font("Sans Medium", 44)
    f_h = B.font("Sans Medium", 36)
    name_img = text_img(name, f_name, B.CHARCOAL)
    # caixa-alta espaçada
    track = 9
    tag_w = sum(f_tag.getlength(ch) for ch in tagline) + track * (len(tagline) - 1)
    tag_im = Image.new("RGBA", (int(tag_w) + 20, 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(tag_im)
    x = 10
    for ch in tagline:
        d.text((x, 52), ch, font=f_tag, fill=B.GOLD + (255,), anchor="ls")
        x += f_tag.getlength(ch) + track
    btn_tw = f_btn.getlength(cta)
    bw, bh = int(btn_tw + 110), 104
    btn = B.rounded((bw, bh), bh // 2, B.CHARCOAL + (255,))
    ImageDraw.Draw(btn).text((bw / 2, bh / 2 + 16), cta, font=f_btn, fill=B.WHITE + (255,), anchor="ms")
    cy = c.get("cy", 860)
    T = {"name": 0.25, "line": 0.95, "tag": 1.15, "btn": 1.45, "handle": 1.7}
    fw = FrameWriter(path, alpha=True)
    n = nframes(dur)
    boxes = []
    for f in range(n):
        t = f / B.FPS
        im = B.paper_background(t, seed=c.get("seed", 5))
        # nome em cursiva: revela da esquerda para a direita (como se escrevesse), desfoque saindo
        ni, ox, oy = name_img
        k = B.clamp01((t - T["name"]) / 0.75)
        if k > 0:
            e = B.ease_in_out(k)
            m = Image.new("L", ni.size, 0)
            ImageDraw.Draw(m).rectangle((0, 0, int(ni.width * e) + 40, ni.height), fill=255)
            m = m.filter(ImageFilter.GaussianBlur(28))
            lay = ni.copy()
            lay.putalpha(Image.fromarray((np.asarray(ni.getchannel("A"), np.float32) *
                                          np.asarray(m, np.float32) / 255).astype(np.uint8)))
            B.paste_center(im, B.premul_blur(lay, 3 * (1 - e)), B.W / 2, cy, boxes=boxes if f == n - 5 else None,
                           tag="nome")
        # filete dourado abrindo do centro
        k = B.ease_out_cubic((t - T["line"]) / 0.45)
        if k > 0:
            L = int(300 * k)
            ImageDraw.Draw(im).line((B.W / 2 - L / 2, cy + 150, B.W / 2 + L / 2, cy + 150), fill=B.GOLD + (255,), width=3)
        k = B.ease_out_cubic((t - T["tag"]) / 0.4)
        if k > 0:
            B.paste_center(im, B.premul_blur(tag_im, 5 * (1 - k)), B.W / 2, cy + 215 + 10 * (1 - k), alpha=k,
                           boxes=boxes if f == n - 5 else None, tag="tagline")
        k = (t - T["btn"]) / 0.35
        if k > 0:
            e = B.ease_out_back(k, 1.3)
            B.paste_center(im, B.scale_rgba(btn, 0.85 + 0.15 * e), B.W / 2, cy + 370, alpha=min(1.0, k * 1.5),
                           boxes=boxes if f == n - 5 else None, tag="botão")
        if handle:
            k = B.ease_out_cubic((t - T["handle"]) / 0.4)
            if k > 0:
                hi, hox, hoy = text_img(handle, f_h, B.CHARCOAL)
                B.paste_center(im, hi, B.W / 2, cy + 480, alpha=k, boxes=boxes if f == n - 5 else None, tag="@")
        a = B.ease_out_cubic(t / 0.3)
        if a < 0.999:
            im = B.with_alpha(B.premul_blur(im, 14 * (1 - a)), a)
        fw.write(im)
    fw.close()
    ev = [{"t": 0.0, "kind": "air"}, {"t": T["name"] + 0.1, "kind": "chime"}, {"t": T["btn"], "kind": "softpop"}]
    return boxes, ev, True


def main():
    global EDL
    edl_path = sys.argv[1] if len(sys.argv) > 1 else "edl.json"
    EDL = B.load_edl(edl_path)
    outdir = os.path.join(EDL["_dir"], "cards")
    os.makedirs(outdir, exist_ok=True)
    for old in os.listdir(outdir):
        os.remove(os.path.join(outdir, old))
    index, allboxes = [], []
    renderers = {"pills": render_pills, "screen": render_screen, "leak": render_leak}
    for k, (a, b, c) in enumerate(B.card_windows(EDL)):
        typ = c["type"]
        c = dict(c, at=a, dur=b - a)
        path = os.path.join(outdir, f"{k:02d}_{typ}.mov")
        if typ in renderers:
            boxes, ev, alpha = renderers[typ](c, path)
        elif typ == "end":
            boxes, ev, alpha = render_end(c, path, b - a)
        else:
            print(f"tipo de card desconhecido: {typ}")
            continue
        if c.get("sfx") is False:                    # EDL: "sfx": false = card mudo
            ev = []
        elif isinstance(c.get("sfx"), str) and ev:   # EDL: "sfx": "pling" troca o som principal do card
            ev = [dict(ev[0], kind=c["sfx"])] + ev[1:]
        for bx in boxes:
            bx["t"] = round(a, 2)
            bx["t_end"] = round(b, 2)
            bx["tag"] = f"{typ}: {bx['tag']}"
        if typ in ("screen", "end"):                 # tela cheia: a margem vale para o texto, não para o fundo
            pass
        allboxes += boxes
        index.append({"file": os.path.relpath(path, EDL["_dir"]), "type": typ, "at": a, "dur": b - a,
                      "alpha": alpha, "hide_logo": typ in B.HIDE_LOGO_TYPES, "behind": False,
                      "top": typ == "leak",
                      "events": [{"t": a + e["t"], "kind": e["kind"]} for e in ev]})
        print(f"card {k}: {typ} {a:.2f}–{b:.2f}s → {os.path.basename(path)}")
    with open(os.path.join(outdir, "index.json"), "w") as f:
        json.dump(index, f, indent=1)
    B.write_bboxes("cards", EDL, allboxes)


if __name__ == "__main__":
    main()
