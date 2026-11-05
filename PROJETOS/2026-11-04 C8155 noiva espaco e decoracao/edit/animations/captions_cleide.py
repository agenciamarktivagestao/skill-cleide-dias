"""Legenda Cleide Dias → captions.mov (transparente)

Estilo de REFERENCIAS/referencia_legenda.mp4:
  • Blocos CURTOS (1–2 linhas, até 5 palavras) na altura do peito, centralizados.
  • Cada palavra entra no tempo da fala, desfocada e transparente → nítida (5 quadros), e a linha
    desliza para o centro quando ganha uma palavra.
  • Letra: Helvetica Neue Medium branca, com halo escuro suave (lê na camisa clara).
  • Destaques (no EDL, use pouco: 1 por frase no máximo):
      script     CURSIVA: Brush Script grande, na linha de baixo, encostando na de cima
                 ("pequena", "se sente" da referência). Entra desfocada e um pouco maior.
      bold       NEGRITO: Helvetica Neue Bold na mesma linha ("hoje", "falta").
      pills      PÍLULA: palavra numa pílula cinza translúcida ("cansada", "mais leveza").
      underline  SUBLINHADO: traço branco desenhado à mão embaixo da expressão ("uma coisa").
  • Troca de bloco: o anterior some desfocando (4 quadros), 2 quadros antes do novo entrar.
  • Posição: a 1ª linha começa abaixo do meio do pescoço (rosto do person.json) + NECK_GAP;
    sem rosto, o bloco fica centrado em "cy". Na mesma tomada a altura não pula.

Uso:  python animations/captions_cleide.py [edl.json]
EDL:  "captions": {"style": "CLD", "hook_end": 0.8,
                   "script": ["Noiva!", "decoração"], "bold": ["diretamente"],
                   "pills": ["WhatsApp"], "underline": ["seu casamento"],
                   "fix": {"cli": "Clique"}, "breaks": [9.52], "keep_case": ["WhatsApp"],
                   "punct": false, "lower": false, "skip": [[t0, t1]], "cy": 1040}
  script/pills/underline  palavra ou expressão (vira uma linha só, com o destaque).
  bold       palavras em negrito na própria linha.
  fix        correções; com espaço na chave, junta as palavras ("cleide dias" → "Cleide Dias").
  breaks     tempos do vídeo ORIGINAL (início da palavra) onde começa um bloco novo.
  punct      true mantém vírgula e ponto (padrão: só ? e !, como na referência).
  skip       janelas do vídeo FINAL sem legenda.
  shift      [[src_t0, src_t1, Δs]] acerta o tempo das palavras de um trecho do transcript.
  joins      tempos do ORIGINAL (início da palavra) que continuam o bloco anterior (o transcript pôs
             ponto onde a frase continua, ex.: "conheça. As lindas" → "conheça as lindas").
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

WORD_IN = 5              # quadros: palavra entra desfocada → nítida
SCRIPT_IN = 7            # quadros: cursiva entra desfocada e 12 % maior → no lugar
PILL_IN = 6              # quadros: pílula abre (escala + desfoque)
UNDER_DELAY, UNDER_IN = 3, 9     # sublinhado desenhado da esquerda para a direita
RECENTER = 4             # quadros: linha desliza para o centro quando ganha palavra
BLOCK_OUT = 4            # quadros: bloco some desfocando
GAP_BREAK = 0.40         # pausa que fecha o bloco
MAX_DUR = 2.6            # bloco longo demais quebra (blocos curtos, como na referência)
TAIL = 0.35              # s que a última palavra fica na tela depois de falada (se houver pausa)
MARGIN = 80              # folga do bloco para halo e escala
SIDE = 24                # folga lateral dentro da margem de segurança
MIN_SCALE = 0.78
CLICK_WORDS = {"clique", "clica", "clicar", "clicando"}
SPECIAL = ("script", "pill", "under")


def norm(w):
    return re.sub(r"[^\w$áàâãéêíóôõúüç-]", "", w.lower())


KEEP_CASE = set()
OPTS = {"punct": False, "lower": False}


def clean(w):
    w = re.sub(r'^["“”\']+|["“”\']+$', "", w.strip())
    if not OPTS["punct"]:
        w = re.sub(r"[.,;:…]+$", "", w)
    if OPTS["lower"] and norm(w) not in KEEP_CASE:
        w = w.lower()
    return w


# ---------------------------------------------------------------- destaques e blocos
def special_flags(words, special):
    """Para cada palavra: (id da expressão, tipo, é a última da expressão) ou None."""
    toks = [norm(w["word"]) for w in words]
    flags = [None] * len(words)
    sid = 0
    for ph, kind in sorted(special, key=lambda p: -len(p[0])):
        n = len(ph)
        for i in range(len(toks) - n + 1):
            if toks[i:i + n] == ph and not any(flags[i:i + n]):
                for j in range(i, i + n):
                    flags[j] = (sid, kind, j == i + n - 1)
                sid += 1
    return flags


def group(words, flags, hidden, hook_end, breaks=(), breaths=(), joins=()):
    """Blocos curtos: fecham em pausa, pontuação, respiro cortado, depois de um destaque,
    em CAPTION_MAX_WORDS palavras ou MAX_DUR s. Expressão de destaque nunca é partida."""
    caps, cur, curf = [], [], []

    def flush():
        nonlocal cur, curf
        if cur:
            caps.append((cur, curf))
        cur, curf = [], []

    for wi, w in enumerate(words):
        f = flags[wi]
        cont = bool(f and cur and curf[-1] and curf[-1][0] == f[0])     # meio de uma expressão
        if any(a - 0.05 <= w["start"] < b for a, b in hidden):
            flush()
            continue
        joined = any(abs(w.get("src", -9) - j) < 0.06 for j in joins)
        if cur and joined and len(cur) < B.CAPTION_MAX_WORDS:
            pass
        elif cur and not cont:
            was_hook, is_hook = cur[0]["start"] < hook_end, w["start"] < hook_end
            if (was_hook != is_hook
                    or any(abs(w.get("src", -9) - b) < 0.06 for b in breaks)
                    or any(cur[-1]["start"] < b <= w["start"] + 0.03 for b in breaths)
                    or w["start"] - cur[-1]["end"] > GAP_BREAK
                    or len(cur) >= B.CAPTION_MAX_WORDS
                    or w["end"] - cur[0]["start"] > MAX_DUR
                    or re.search(r"[.?!…]$", cur[-1]["word"])
                    or (re.search(r",$", cur[-1]["word"]) and len(cur) >= 2)
                    or (curf[-1] and curf[-1][2])):                 # destaque fecha o bloco
                flush()
            elif f and not cont and len(cur) >= 4:                  # destaque novo com bloco já cheio
                flush()
        cur.append(w)
        curf.append(f)
    flush()
    return caps


def layout_lines(ws, fs, bold, mult):
    """Linhas: destaques numa linha só; o resto até LINE_W px / LINE_WORDS palavras."""
    f_s = B.font(B.CAPTION_FONT, B.CAPTION_SIZE * mult)
    f_b = B.font(B.BOLD_FONT, B.CAPTION_SIZE * mult)
    space = f_s.getlength(" ")
    lines, cur = [], []

    def width(words):
        return sum((f_b if norm(w["word"]) in bold else f_s).getlength(clean(w["word"])) for w in words) + \
            space * (len(words) - 1)

    def flush():
        nonlocal cur
        if cur:
            lines.append(("text", cur))
        cur = []

    i = 0
    while i < len(ws):
        f = fs[i]
        if f:
            flush()
            j = i
            while j < len(ws) and fs[j] and fs[j][0] == f[0]:
                j += 1
            lines.append((f[1], ws[i:j]))
            i = j
            continue
        w = ws[i]
        if cur and (len(cur) >= B.LINE_WORDS or width(cur + [w]) > B.LINE_W * mult):
            flush()
        cur.append(w)
        i += 1
    flush()
    # 2 linhas de texto com a de baixo bem curta → equilibra
    if len(lines) == 2 and lines[0][0] == lines[1][0] == "text" and len(lines[1][1]) == 1 and len(lines[0][1]) >= 3:
        lines = [("text", lines[0][1][:-1]), ("text", lines[0][1][-1:] + lines[1][1])]
    return lines


# ---------------------------------------------------------------- desenho
def word_image(text, fnt, color=B.WHITE, halo=True):
    """Palavra com halo; devolve (imagem, ox, oy) — (ox, oy) = origem da linha de base na imagem."""
    s = fnt.size
    pad = int(s * 0.6)
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


def swoosh_points(x0, x1, y, size, n=60):
    """Traço de caneta embaixo do texto: leve curva, sobe um pouco no fim."""
    pts = []
    for i in range(n + 1):
        u = i / n
        x = x0 + (x1 - x0) * u
        yy = y + size * 0.10 * math.sin(math.pi * u) * 0.6 - size * 0.16 * u ** 3
        pts.append((x, yy))
    return pts


class Piece:
    """Uma palavra (ou a expressão de destaque inteira) já desenhada; x = início do texto na linha."""

    def __init__(self, kind, text, fnt, start):
        self.kind, self.text, self.font, self.start = kind, text, fnt, B.snap(start)
        self.img, self.ox, self.oy = word_image(text, fnt)
        self.w = fnt.getlength(text)
        bb = fnt.getbbox(text, anchor="ls")
        self.asc, self.desc = -bb[1], bb[3]
        self.x = 0.0


class Block:
    """Até CAPTION_MAX_LINES linhas. Coordenadas: x relativo ao centro, y ao topo do bloco."""

    def __init__(self, lines, hook, scale, bold, max_w):
        mult = (B.HOOK_K if hook else 1.0) * scale
        s = B.CAPTION_SIZE * mult
        f_cap = B.font(B.CAPTION_FONT, s)
        cap_h = -f_cap.getbbox("H", anchor="ls")[1]
        desc_h = f_cap.getbbox("g", anchor="ls")[3]
        self.lines = []
        for kind, words in lines:
            if kind == "text":
                ps = [Piece("bold" if norm(w["word"]) in bold else "small", clean(w["word"]),
                            B.font(B.BOLD_FONT if norm(w["word"]) in bold else B.CAPTION_FONT, s), w["start"])
                      for w in words]
            elif kind == "script":
                txt = " ".join(clean(w["word"]) for w in words)
                size = s * B.SCRIPT_K
                while B.font(B.SCRIPT_FONT, size).getlength(txt) > max_w and size > 40:
                    size -= 3
                ps = [Piece("script", txt, B.font(B.SCRIPT_FONT, size), words[0]["start"])]
            elif kind == "pill":
                txt = " ".join(clean(w["word"]) for w in words)
                ps = [Piece("pill", txt, B.font(B.PILL_FONT, s * B.PILL_K), words[0]["start"])]
            else:                                               # under: palavras normais + traço
                ps = [Piece("small", clean(w["word"]), f_cap, w["start"]) for w in words]
            space = f_cap.getlength(" ")
            x, cum, starts = 0.0, [], []
            for p in ps:
                p.x = x
                x += p.w + space
                cum.append(x - space)
                starts.append(p.start)
            ln = {"kind": kind, "pieces": ps, "cum": cum, "starts": starts, "w": cum[-1],
                  "end": max(w["end"] for w in words)}
            if kind == "script":
                ln["asc"] = max(p.asc for p in ps)
                ln["desc"] = max(p.desc for p in ps)
            elif kind == "pill":
                ph = cap_h * 2.15
                ln["pill"] = (ln["w"] + s * 0.95, ph)
                ln["asc"] = ph / 2 + cap_h / 2
                ln["desc"] = ph / 2 - cap_h / 2
            else:
                ln["asc"], ln["desc"] = cap_h, desc_h
                if kind == "under":
                    ln["desc"] = desc_h + s * 0.25
            self.lines.append(ln)
        y = 0.0
        for i, ln in enumerate(self.lines):
            if i:
                y += B.LEADING * s
                if ln["kind"] == "script":                       # cursiva encosta na linha de cima
                    y -= B.SCRIPT_OVERLAP * ln["asc"]
                elif ln["kind"] == "pill" or self.lines[i - 1]["kind"] == "pill":
                    y += s * 0.18
            ln["top"] = y
            ln["base"] = y + ln["asc"]
            y = ln["base"] + ln["desc"]
        self.height = y
        allp = [p for ln in self.lines for p in ln["pieces"]]
        self.t_in = min(p.start for p in allp)
        self.last = max(p.start for p in allp)
        self.end_words = max(ln["end"] for ln in self.lines)
        self.kinds = [p.kind for p in allp] + [ln["kind"] for ln in self.lines if ln["kind"] == "under"]
        self.size_s = s
        maxw = max((ln["pill"][0] if "pill" in ln else ln["w"]) for ln in self.lines)
        self.ox = int(-maxw / 2 - MARGIN)
        self.oy = int(-MARGIN)
        self.size = (int(maxw + 2 * MARGIN), int(self.height + 2 * MARGIN))
        bb = self.draw(self.last + 5).getchannel("A").point(lambda v: 255 if v > 60 else 0).getbbox()
        self.vis = (bb[0] + self.ox, bb[1] + self.oy, bb[2] + self.ox, bb[3] + self.oy)

    @staticmethod
    def stepped(points, t, frames):
        prev, val, t_k = None, None, 0
        for tk, v in points:
            if t + 1e-6 < tk:
                break
            prev, val, t_k = val, v, tk
        if val is None:
            return points[0][1]
        if prev is None:
            return val
        return prev + (val - prev) * B.ease_out_cubic((t - t_k) * B.FPS / frames)

    def line_x(self, ln, t):
        return self.stepped([(st, -c / 2) for st, c in zip(ln["starts"], ln["cum"])], t, RECENTER)

    def draw(self, t):
        c = Image.new("RGBA", self.size, (0, 0, 0, 0))
        for ln in self.lines:
            lx = self.line_x(ln, t) - self.ox
            base = ln["base"] - self.oy
            if "pill" in ln:
                p = ln["pieces"][0]
                dt = (t - p.start) * B.FPS
                if dt < 0:
                    continue
                e = B.ease_out_cubic(dt / PILL_IN)
                pw, ph = ln["pill"]
                pill = B.rounded((int(pw), int(ph)), int(ph / 2), B.PILL + (B.PILL_ALPHA,))
                pill = B.scale_rgba(B.premul_blur(pill, 6 * (1 - e)), 0.86 + 0.14 * e)
                B.paste_center(c, pill, -self.ox, ln["top"] - self.oy + ph / 2, alpha=min(1.0, 0.15 + e))
                im = B.premul_blur(p.img, 6 * (1 - e))
                B._safe_composite(c, B.with_alpha(im, min(1.0, 0.2 + e)),
                                  int(round(-self.ox - p.w / 2 - p.ox)), int(round(base - p.oy)))
                continue
            for p in ln["pieces"]:
                dt = (t - p.start) * B.FPS
                if dt < 0:
                    continue
                px, py = lx + p.x - p.ox, base - p.oy
                n_in = SCRIPT_IN if p.kind == "script" else WORD_IN
                k = dt / n_in
                if k >= 1:
                    B._safe_composite(c, p.img, int(round(px)), int(round(py)))
                    continue
                e = B.ease_out_cubic(k)
                cx, cy = px + p.img.width / 2, py + p.img.height / 2
                if p.kind == "script":
                    im = B.scale_rgba(B.premul_blur(p.img, 10 * (1 - e)), 1.12 - 0.12 * e)
                    B.paste_center(c, im, cx, cy, alpha=min(1.0, 0.15 + 1.2 * k))
                else:
                    im = B.premul_blur(p.img, 7 * (1 - e))
                    B.paste_center(c, im, cx, cy + 6 * (1 - e), alpha=min(1.0, 0.2 + 1.1 * k))
            if ln["kind"] == "under":
                p_last = ln["pieces"][-1]
                dt = (t - p_last.start) * B.FPS - UNDER_DELAY
                if dt > 0:
                    k = B.ease_in_out(dt / UNDER_IN)
                    x0 = -self.ox - ln["w"] / 2 - self.size_s * 0.12
                    x1 = -self.ox + ln["w"] / 2 + self.size_s * 0.18
                    pts = swoosh_points(x0, x1, base + self.size_s * 0.30, self.size_s)
                    pts = pts[:max(2, int(len(pts) * k))]
                    wd = max(4, int(self.size_s * 0.075))
                    sh = Image.new("L", self.size, 0)
                    ImageDraw.Draw(sh).line([(x, y + 2) for x, y in pts], fill=140, width=wd + 6, joint="curve")
                    layer = Image.new("RGBA", self.size, B.INK + (0,))
                    layer.putalpha(sh.filter(ImageFilter.GaussianBlur(5)))
                    c.alpha_composite(layer)
                    d = ImageDraw.Draw(c)
                    d.line(pts, fill=B.WHITE + (255,), width=wd, joint="curve")
                    r = wd / 2
                    for x, y in (pts[0], pts[-1]):
                        d.ellipse((x - r, y - r, x + r, y + r), fill=B.WHITE + (255,))
        return c

    def frame(self, t):
        if t < self.t_in - 1e-6 or t >= self.t_gone - 1e-6:
            return None
        c = self.draw(t)
        if t < self.t_out:
            return c
        e = B.clamp01(((t - self.t_out) * B.FPS + 1) / (BLOCK_OUT + 1))
        return B.with_alpha(B.premul_blur(c, 8 * e), 1 - e)


def merge_fixes(words, fixes):
    """Correções com mais de uma palavra ("cleide dias" → "Cleide Dias") juntam as palavras numa só."""
    multi = sorted([(k.split(), v) for k, v in fixes.items() if len(k.split()) > 1], key=lambda x: -len(x[0]))
    out, i = [], 0
    while i < len(words):
        for toks, v in multi:
            n = len(toks)
            if [norm(w["word"]) for w in words[i:i + n]] == [norm(t) for t in toks]:
                tail = re.sub(r"^.*?([.,;:?!]*)$", r"\1", words[i + n - 1]["word"])
                out.append(dict(words[i], word=v + tail, end=words[i + n - 1]["end"]))
                i += n
                break
        else:
            w = words[i]
            n = norm(w["word"])
            if n in fixes:
                w = dict(w, word=fixes[n] + re.sub(r"^.*?([.,;:?!]*)$", r"\1", w["word"]))
            out.append(w)
            i += 1
    return out


def main():
    edl_path = sys.argv[1] if len(sys.argv) > 1 else "edl.json"
    edl = B.load_edl(edl_path)
    cfg = edl.get("captions", {})
    cy_default = cfg.get("cy", B.CAPTION_CY)
    hook_end = float(cfg.get("hook_end", 0))
    OPTS["punct"] = bool(cfg.get("punct", False))
    OPTS["lower"] = bool(cfg.get("lower", False))
    KEEP_CASE.update(norm(k) for k in cfg.get("keep_case", []))
    special = []
    for key, kind in (("script", "script"), ("pills", "pill"), ("underline", "under")):
        special += [([norm(x) for x in k.split()], kind) for k in cfg.get(key, [])]
    bold = {norm(t) for a in cfg.get("bold", []) for t in a.split()}
    fixes = {" ".join(norm(t) for t in k.split()): v for k, v in cfg.get("fix", {}).items()}
    words = B.load_words(edl)
    if not words:
        sys.exit("Sem transcript.json — rode transcribe.py antes (ou desligue as legendas no EDL).")
    words = merge_fixes(words, fixes)
    max_w = B.SAFE[2] - B.SAFE[0] - 2 * SIDE
    hidden = B.opaque_windows(edl) + [tuple(x) for x in cfg.get("skip", [])]
    segs = B.segments_out(edl)
    breaths = [segs[i][2] for i in range(1, len(segs)) if segs[i][0] - segs[i - 1][1] > 0.05]
    flags = special_flags(words, special)
    caps = group(words, flags, hidden, hook_end, cfg.get("breaks", []), breaths, cfg.get("joins", []))

    plans = []
    for ws, fs in caps:
        hook = ws[0]["start"] < hook_end
        lines = layout_lines(ws, fs, bold, B.HOOK_K if hook else 1.0)
        for i in range(0, len(lines), B.CAPTION_MAX_LINES):
            plans.append((lines[i:i + B.CAPTION_MAX_LINES], hook))
    blocks = [Block(ln, hook, 1.0, bold, max_w) for ln, hook in plans]
    order = sorted(range(len(blocks)), key=lambda i: blocks[i].t_in)
    blocks = [blocks[i] for i in order]
    plans = [plans[i] for i in order]

    def seg_of(t):
        return next((i for i, s in enumerate(segs) if s[2] - 1e-6 <= t < s[3]), -1)

    total = B.total_duration(edl)
    prev = None
    for i in range(len(blocks)):
        u = blocks[i]
        t_out = B.snap(max(u.last + 3 / B.FPS, u.end_words + TAIL))
        if i + 1 < len(blocks):                     # começa a sumir 2 quadros antes do próximo entrar
            t_out = min(t_out, max(B.snap(u.last + 3 / B.FPS), blocks[i + 1].t_in - 2 / B.FPS))
        for a, b in hidden:                         # sai inteiro antes da tela / lista / card final
            if u.t_in < a < t_out + BLOCK_OUT / B.FPS:
                t_out = max(u.t_in + 2 / B.FPS, B.snap(a - BLOCK_OUT / B.FPS))
        t_out = min(t_out, B.snap(total - BLOCK_OUT / B.FPS))
        t_gone = t_out + BLOCK_OUT / B.FPS
        neck = B.neck_line(edl, u.t_in, t_gone)

        def place(b):
            return neck + B.NECK_GAP - b.vis[1] if neck is not None else cy_default - (b.vis[1] + b.vis[3]) / 2

        top = place(u)
        sg = seg_of(u.t_in)
        if prev and prev[0] == sg and abs(prev[1] - top) < 50 and (neck is None or prev[1] >= top - 6):
            top = prev[1]                           # mesma tomada: a legenda não fica pulando
        bottom_lim = B.SAFE[3] - 6
        if top + u.vis[3] > bottom_lim:
            s = max(MIN_SCALE, (bottom_lim - top) / max(1, u.vis[3]))
            u = blocks[i] = Block(plans[i][0], plans[i][1], s, bold, max_w)
            top = min(place(u), bottom_lim - u.vis[3])
        top = max(top, B.SAFE[1] + 6 - u.vis[1])
        u.t_out, u.t_gone = t_out, t_gone
        u.top = int(round(top))
        u.cx = B.W // 2
        prev = (sg, u.top)

    nfr = B.total_frames(edl)
    fw = FrameWriter(os.path.join(edl["_dir"], "captions.mov"), alpha=True)
    blank = Image.new("RGBA", (B.W, B.H), (0, 0, 0, 0))
    j0 = 0
    for f in range(nfr):
        t = f / B.FPS
        while j0 < len(blocks) and blocks[j0].t_gone <= t:
            j0 += 1
        live = []
        for u in blocks[j0:]:
            if u.t_in > t + 1e-6:
                break
            r = u.frame(t)
            if r is not None:
                live.append((u, r))
        if not live:
            fw.write(blank)
            continue
        im = blank.copy()
        for u, c in live:
            B._safe_composite(im, c, u.cx + u.ox, u.top + u.oy)
        fw.write(im)
    fw.close()

    boxes = []
    for i, u in enumerate(blocks):
        txt = " / ".join(" ".join(p.text for p in ln["pieces"]) for ln in u.lines)
        kinds = sorted({k for k in u.kinds if k not in ("small",)})
        boxes.append({"tag": f"legenda {i + 1}{' (gancho)' if u.t_in < hook_end else ''}"
                             f"{' [' + ', '.join(kinds) + ']' if kinds else ''}: {txt}",
                      "t": round(u.t_in, 2), "t_end": round(u.t_gone, 2),
                      "box": [u.cx + u.vis[0], u.top + u.vis[1], u.cx + u.vis[2] - 1, u.top + u.vis[3] - 1]})
    B.write_bboxes("captions", edl, boxes)

    # efeitos (o build.py mixa): brilho na cursiva do gancho e clique no "clique" (a pílula fica muda).
    # As outras cursivas ficam sem som (pedido de 04/11: efeitos simples, nada exagerado).
    sfx = []
    for u in blocks:
        for ln in u.lines:
            for p in ln["pieces"]:
                if p.kind == "script" and u.t_in < hook_end:
                    sfx.append({"t": round(p.start, 3), "kind": "shimmer", "why": p.text})
    for w in words:
        if norm(w["word"]) in CLICK_WORDS and not any(a - 0.05 <= w["start"] < b for a, b in hidden):
            sfx.append({"t": round(B.snap(w["start"]) + 0.05, 3), "kind": "click", "why": w["word"]})
    with open(os.path.join(edl["_dir"], "captions_sfx.json"), "w") as f:
        json.dump(sorted(sfx, key=lambda e: e["t"]), f, ensure_ascii=False, indent=1)
    nk = sum(1 for u in blocks for k in u.kinds if k in SPECIAL)
    print(f"{len(blocks)} blocos de legenda ({nk} destaques; gancho até {hook_end:.1f}s) → captions.mov")


if __name__ == "__main__":
    main()
