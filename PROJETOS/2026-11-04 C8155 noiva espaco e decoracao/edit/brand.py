"""Marca, medidas e utilitários compartilhados: Cleide Dias (decoração de eventos).

Tudo o que é "regra do cliente" (cores, margem, fontes, tamanhos aprovados)
fica aqui, para os outros scripts só importarem.
"""
import json
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")

# ---------- formato ----------
W, H, FPS = 1080, 1920, 30
SAFE = (91, 100, 988, 1681)          # x0, y0, x1, y1 (inclusive): nada sai daqui (assets/margem_seguranca.jpeg)

# ---------- cores (padrão montado em 04/11/2026; ainda sem manual de marca) ----------
WHITE = (255, 255, 255)              # legenda (como na referência)
INK = (28, 20, 16)                   # sombra da legenda: marrom quase preto (lê na camisa clara)
PILL = (84, 76, 70)                  # pílula translúcida da legenda/lista (cinza quente, ~70 % de opacidade)
PILL_ALPHA = 178
PAPER = (247, 243, 237)              # fundo das telas brancas (off-white quente)
SHADOW = (120, 108, 96)              # sombras de folhagem nas telas brancas
CHARCOAL = (46, 42, 40)              # texto nas telas brancas
GOLD = (190, 154, 98)                # champanhe/dourado: círculo tracejado, detalhes do card final
GOLD_LIGHT = (226, 200, 150)
ROSE = (226, 150, 150)               # rosé (das flores do quadro): só no brilho de luz (leak)

# ---------- textos fixos (CONFIRMAR com a cliente: nome, @, frase do botão) ----------
BRAND = "Cleide Dias"
TAGLINE = "Decoração de eventos"
CTA = "Fale no WhatsApp"
HANDLE = ""                          # @ do Instagram: ainda não informado (o card final sai sem)

# ---------- legenda (estilo de REFERENCIAS/referencia_legenda.mp4) ----------
# Palavras entram uma a uma, desfocadas → nítidas, em blocos curtos (1–2 linhas) na altura do peito.
# Destaques: cursiva grande (Brush Script), negrito na linha, pílula translúcida, sublinhado à mão.
CAPTION_FONT = "Sans Medium"         # Helvetica Neue Medium branca
CAPTION_SIZE = 58
HOOK_K = 1.08                        # gancho (até "hook_end"): tudo 8 % maior
BOLD_FONT = "Sans Bold"              # palavra em negrito na mesma linha ("hoje", "falta" da referência)
SCRIPT_FONT = "Script"               # cursiva grande na linha de baixo ("pequena", "se sente")
SCRIPT_K = 2.45
PILL_FONT = "Sans Medium"            # pílula translúcida ("cansada", "mais leveza")
PILL_K = 1.0
LINE_W = 640                         # largura máxima de uma linha de palavras normais
LINE_WORDS = 4
LEADING = 0.16                       # espaço entre linhas (× tamanho da palavra normal)
SCRIPT_OVERLAP = 0.22                # a cursiva sobe e encosta na linha de cima (× tamanho dela)
CAPTION_MAX_LINES = 2
CAPTION_MAX_WORDS = 5
NECK_GAP = 110                       # 1ª linha começa abaixo do meio do pescoço (person.json), na altura do peito
CAPTION_CY = 1040                    # centro do bloco quando não há rosto
CAPTION_MIN_TOP = 760                # selfeval: sem rosto detectado, nenhuma legenda começa acima disso

# ---------- logo ----------
# Ainda não há logo. Pedido de 04/11: NADA fixo no alto do vídeo ("teto") se não houver título.
LOGO_FILE = "logo.png"
LOGO_W = 220
LOGO_OPACITY = 1.0
LOGO_POS = "bottom-center"
LOGO_Y = SAFE[1] + 20

# tipos de card que escondem a legenda / o logo
HIDE_CAPTION_TYPES = {"screen", "pills", "end", "photo"}
HIDE_LOGO_TYPES = {"screen", "end", "photo"}


# =====================================================================
# Fontes: Helvetica Neue (texto) e Brush Script (cursiva), as duas do macOS.
# Fora do Mac cai na Prompt (assets/fonts, licença OFL).
# =====================================================================
_SYS = "/System/Library/Fonts"
FONTS = {
    "Sans Light": (f"{_SYS}/HelveticaNeue.ttc", 7, "Prompt-Regular.ttf"),
    "Sans": (f"{_SYS}/HelveticaNeue.ttc", 0, "Prompt-Regular.ttf"),
    "Sans Medium": (f"{_SYS}/HelveticaNeue.ttc", 10, "Prompt-Medium.ttf"),
    "Sans Bold": (f"{_SYS}/HelveticaNeue.ttc", 1, "Prompt-Bold.ttf"),
    "Sans Medium Italic": (f"{_SYS}/HelveticaNeue.ttc", 11, "Prompt-SemiBoldItalic.ttf"),
    "Script": (f"{_SYS}/Supplemental/Brush Script.ttf", 0, "Prompt-ExtraBoldItalic.ttf"),
}
_cache = {}


def font(style, size):
    key = (style, int(size))
    if key not in _cache:
        path, idx, fallback = FONTS[style]
        try:
            _cache[key] = ImageFont.truetype(path, int(size), index=idx)
        except OSError:
            _cache[key] = ImageFont.truetype(os.path.join(ASSETS, "fonts", fallback), int(size))
    return _cache[key]


# =====================================================================
# Desenho
# =====================================================================
def text_size(text, fnt):
    b = fnt.getbbox(text)
    return b[2] - b[0], b[3] - b[1]


def text_mask(text, fnt, pad=0):
    """Máscara 'L' justa do texto, com origem (offset) do bbox."""
    b = fnt.getbbox(text)
    w, h = b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad
    m = Image.new("L", (max(1, w), max(1, h)), 0)
    ImageDraw.Draw(m).text((pad - b[0], pad - b[1]), text, font=fnt, fill=255)
    return m


def rounded(size, radius, fill):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=fill)
    return im


def scale_rgba(im, s):
    if abs(s - 1) < 1e-3:
        return im
    w, h = max(1, int(im.width * s)), max(1, int(im.height * s))
    return im.resize((w, h), Image.LANCZOS)


def premul_blur(im, r):
    if r < 0.4:
        return im
    return im.convert("RGBa").filter(ImageFilter.GaussianBlur(r)).convert("RGBA")


def with_alpha(im, k):
    if k >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * max(0.0, k))))
    return im


def paste_center(canvas, im, cx, cy, alpha=1.0, boxes=None, tag=None):
    if alpha <= 0.001 or im.width < 1:
        return
    im = with_alpha(im, alpha)
    x, y = int(round(cx - im.width / 2)), int(round(cy - im.height / 2))
    _safe_composite(canvas, im, x, y)
    if boxes is not None:
        bb = im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
        if bb:
            boxes.append({"tag": tag, "box": [x + bb[0], y + bb[1], x + bb[2] - 1, y + bb[3] - 1]})


def _safe_composite(canvas, im, x, y):
    # paste SEM máscara copia o RGBA como está; com máscara (paste(im, pos, im)) a transparência
    # saía multiplicada por ela mesma e brilho/sombras semitransparentes quase sumiam
    if 0 <= x and 0 <= y and x + im.width <= canvas.width and y + im.height <= canvas.height:
        canvas.alpha_composite(im, (x, y))
        return
    tmp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    tmp.paste(im, (x, y))
    canvas.alpha_composite(tmp)


def load_logo(kind="white"):
    p = os.path.join(ASSETS, f"logo_{kind}.png")
    return Image.open(p).convert("RGBA") if os.path.exists(p) else None


def soft_text(text, fnt, color=WHITE, shadow=0.55, shadow_r=0.10, wide=0.30, wide_k=0.45):
    """Texto com sombra escura dupla: uma justa (contorno suave) e uma larga (halo). Na camisa clara
    da Cleide o branco some sem o halo; com ele, lê sem parecer contorno."""
    s = fnt.size
    pad = int(s * 0.55)
    m = text_mask(text, fnt, pad)
    import numpy as np
    a = np.asarray(m.filter(ImageFilter.GaussianBlur(s * shadow_r)), np.float32) * shadow
    if wide:
        a = np.maximum(a, np.asarray(m.filter(ImageFilter.GaussianBlur(s * wide)), np.float32) * wide_k)
    out = Image.new("RGBA", m.size, INK + (0,))
    out.putalpha(Image.fromarray(np.clip(a, 0, 255).astype("uint8")))
    fill = Image.new("RGBA", m.size, tuple(color[:3]) + (0,))
    fill.putalpha(m)
    out.alpha_composite(fill)
    return out, pad


def dashed_ellipse(rx, ry, progress=1.0, color=GOLD, thick=5, dash=26, gap=16, rot=-8, start=-110):
    """Elipse tracejada que se desenha (o círculo da tela branca da referência)."""
    pad = thick * 2 + 4
    im = Image.new("RGBA", (int(2 * rx + 2 * pad), int(2 * ry + 2 * pad)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = im.width / 2, im.height / 2
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    n = 360
    pts = []
    for i in range(n + 1):
        a = math.radians(start) + 2 * math.pi * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + x * cr - y * sr, cy + x * sr + y * cr))
    seg = [0.0]
    for i in range(1, len(pts)):
        seg.append(seg[-1] + math.dist(pts[i - 1], pts[i]))
    total = seg[-1] * clamp01(progress)
    run = []
    for i, p in enumerate(pts):
        if seg[i] > total:
            break
        on = (seg[i] % (dash + gap)) < dash
        if on:
            run.append(p)
        elif run:
            if len(run) > 1:
                d.line(run, fill=color + (255,), width=thick, joint="curve")
            run = []
    if len(run) > 1:
        d.line(run, fill=color + (255,), width=thick, joint="curve")
    return im


# =====================================================================
# Telas claras: off-white com sombras suaves de folhagem (como as telas brancas da referência)
# =====================================================================
_leaf_cache = {}


def leaf_shadows(seed=3):
    """Camada de sombras de folhas (borradas), maior que a tela, para deslizar devagar."""
    if seed in _leaf_cache:
        return _leaf_cache[seed]
    import random
    rnd = random.Random(seed)
    big = (W + 300, H + 300)
    m = Image.new("L", big, 0)
    d = ImageDraw.Draw(m)
    # ramos saindo dos cantos de cima e de baixo, com folhas ovais
    for corner in ((0, 0), (big[0], 0), (big[0], big[1]), (0, int(big[1] * 0.75))):
        for _ in range(3):
            ang = math.atan2(big[1] / 2 - corner[1], big[0] / 2 - corner[0]) + rnd.uniform(-0.6, 0.6)
            L = rnd.uniform(500, 900)
            for k in range(9):
                t = (k + 1) / 9
                px = corner[0] + math.cos(ang) * L * t
                py = corner[1] + math.sin(ang) * L * t
                side = 1 if k % 2 else -1
                la = ang + side * rnd.uniform(0.6, 1.1)
                lw, lh = rnd.uniform(110, 190) * (1.1 - t * 0.5), rnd.uniform(40, 70) * (1.1 - t * 0.5)
                leaf = Image.new("L", (int(lw * 2.2), int(lw * 2.2)), 0)
                ImageDraw.Draw(leaf).ellipse((leaf.width / 2 - lw, leaf.height / 2 - lh,
                                              leaf.width / 2 + lw, leaf.height / 2 + lh), fill=255)
                leaf = leaf.rotate(-math.degrees(la), resample=Image.BICUBIC)
                ox = int(px + math.cos(la) * lw * 0.8 - leaf.width / 2)
                oy = int(py + math.sin(la) * lw * 0.8 - leaf.height / 2)
                m.paste(255, (ox, oy), leaf)
            d.line((corner, (corner[0] + math.cos(ang) * L, corner[1] + math.sin(ang) * L)), fill=255, width=14)
    m = m.filter(ImageFilter.GaussianBlur(38))
    _leaf_cache[seed] = m
    return m


def paper_background(t, seed=3, strength=0.20):
    """Tela off-white com as sombras de folhagem balançando devagar."""
    bg = Image.new("RGBA", (W, H), PAPER + (255,))
    m = leaf_shadows(seed)
    ox = int(150 + 40 * math.sin(t * 0.7 + seed))
    oy = int(150 + 30 * math.cos(t * 0.5 + seed))
    crop = m.crop((ox, oy, ox + W, oy + H)).point(lambda v: int(v * strength))
    sh = Image.new("RGBA", (W, H), SHADOW + (0,))
    sh.putalpha(crop)
    bg.alpha_composite(sh)
    return bg


# =====================================================================
# Easing
# =====================================================================
def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ease_out_cubic(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp01(x)
    return 3 * x * x - 2 * x * x * x


def ease_sine(x):
    x = clamp01(x)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def ease_out_back(x, s=1.70158):
    x = clamp01(x)
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


# =====================================================================
# EDL e mapeamento de tempo
# =====================================================================
def load_edl(path="edl.json"):
    with open(path, encoding="utf-8") as f:
        edl = json.load(f)
    edl["_dir"] = os.path.dirname(os.path.abspath(path))
    return edl


def snap(t):
    return round(t * FPS) / FPS


def segments_out(edl):
    """Lista de (src_start, src_end, out_start, out_end) no grid de quadros."""
    res, o = [], 0.0
    for s in edl["segments"]:
        a, b = snap(s["start"]), snap(s["end"])
        if b <= a:
            continue
        res.append((a, b, o, o + (b - a)))
        o += b - a
    return res


def body_duration(edl):
    seg = segments_out(edl)
    return seg[-1][3] if seg else 0.0


def total_duration(edl):
    return body_duration(edl) + snap(edl.get("hold", 0.0))


def total_frames(edl):
    return int(round(total_duration(edl) * FPS))


def src_to_out(t, segs):
    for a, b, oa, ob in segs:
        if a - 1e-6 <= t <= b + 1e-6:
            return oa + (t - a)
    return None


def card_windows(edl, types=None):
    """Janelas (início, fim) dos cards no tempo de saída."""
    wins = []
    body = body_duration(edl)
    for c in edl.get("cards", []):
        if types and c["type"] not in types:
            continue
        if c["type"] == "end":
            wins.append((snap(body + c.get("lead", 0.0)) if c.get("lead") else body, total_duration(edl), c))
        else:
            wins.append((snap(c["at"]), snap(c["at"]) + snap(c["dur"]), c))
    return wins


def opaque_windows(edl):
    """Janelas em que a legenda some."""
    return [(a, b) for a, b, c in card_windows(edl) if c["type"] in HIDE_CAPTION_TYPES]


def load_words(edl):
    """Palavras do transcript mapeadas para o tempo de saída (cortes removidos)."""
    p = os.path.join(edl["_dir"], edl.get("captions", {}).get("words_file", "transcript.json"))
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        tr = json.load(f)
    segs = segments_out(edl)
    shift = edl.get("captions", {}).get("shift", [])     # [[src_t0, src_t1, Δs]]: acerta tempos do transcript
    out = []
    for w in tr["words"]:
        d = next((float(dt) for a, b, dt in shift if a <= w["start"] < b), 0.0)
        ws, we = w["start"] + d, w["end"] + d
        mid = (ws + we) / 2
        if src_to_out(mid, segs) is None:
            continue
        s = src_to_out(max(ws, 0), segs)
        e = src_to_out(we, segs)
        if s is None:
            s = src_to_out(mid, segs)
        if e is None:
            e = src_to_out(mid, segs) + 0.05
        out.append({"word": w["word"].strip(), "start": s, "end": max(e, s + 0.05), "src": ws})
    return [w for w in out if w["word"]]


def write_bboxes(name, edl, boxes):
    p = os.path.join(edl["_dir"], "bboxes.json")
    data = {}
    if os.path.exists(p):
        with open(p) as f:
            data = json.load(f)
    data[name] = boxes
    with open(p, "w") as f:
        json.dump(data, f)


# =====================================================================
# Onde está a pessoa (person.json, gerado pelo person.py a partir do base.mkv)
# =====================================================================
NECK_K = 0.40            # meio do pescoço ≈ fim do rosto detectado + 0,40 × altura do rosto
HAIR_K = 0.55            # topo da cabeça ≈ início do rosto − 0,55 × altura (cabelo)
_person = {}


def load_person(edl):
    p = os.path.join(edl["_dir"], "person.json")
    if p not in _person:
        _person[p] = json.load(open(p)) if os.path.exists(p) else None
    return _person[p]


def _faces(edl, t0, t1):
    pj = load_person(edl)
    if not pj:
        return []
    fs = pj["faces"]
    a, b = max(0, int(t0 * FPS)), min(len(fs), int(math.ceil(t1 * FPS)) + 1)
    return [f for f in fs[a:b] if f]


def neck_line(edl, t0, t1):
    """y do meio do pescoço (o mais baixo no intervalo). Legenda e lista começam daqui para baixo."""
    fs = _faces(edl, t0, t1)
    return max(f[1] + f[3] * (1 + NECK_K) for f in fs) if fs else None


def head_top(edl, t0, t1):
    """y do topo da cabeça (o mais alto no intervalo)."""
    fs = _faces(edl, t0, t1)
    return min(f[1] - f[3] * HAIR_K for f in fs) if fs else None
