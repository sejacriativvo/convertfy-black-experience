"""cards.py: os elementos de tela do vídeo (pedido de 15/11, com referência do G4 Valley e do Primo Rico), na cara da Convertfy.

  glossario(termo, texto)   janelinha branca com a barra de cima no degradê da marca e os três pontos, sombra deslocada
                            em violeta; o termo em negrito e a explicação entram palavra por palavra. Embaixo, no meio.
  nome(nome, papel, lado)   quem fala: o nome grande e o que a pessoa faz embaixo, sem caixa, no lado oposto ao rosto.
                            As letras sobem uma a uma; o papel entra depois. O papel é só o que é dito no vídeo.
  qr(...)                   o "L" do QR code: o vídeo encolhe pro canto de cima (yt.compoe), entra a coluna com o QR da
                            campanha (convertfy.me, utm 11-11) e o Bruno recortado, e a faixa de baixo com a logo e a chamada.

Cada função desenha a sequência de PNGs (cache por assinatura) e devolve (padrão, quadros, (x, y)), como insight.gera.
Tudo animado com ease-out forte na entrada e ease-in curto na saída; nada para de repente.
"""
import os, json, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from insight import _f, _sai, _entra, _degrade, _forma, _alfa

AQUI = os.path.dirname(os.path.abspath(__file__))
INK = (16, 18, 28)
BRANCO = (250, 250, 252)
VIOLETA, AZUL_CLARO, AZUL_NOITE, FUNDO = (91, 43, 255), (111, 160, 255), (6, 20, 107), (7, 8, 11)
QR_SC = 0.81            # tamanho do vídeo dentro do L (o resto é a coluna e a faixa)
# o degradê dos cartões de QR da própria Convertfy (azul claro à esquerda, azul-noite à direita) e o lilás do itálico
AZ1, AZ2, AZ3 = (74, 95, 217), (32, 48, 170), (11, 18, 80)
LILAS = (200, 207, 255)


def _grad(w, h):
    """degradê horizontal da marca, medido na arte de QR do time da Convertfy (15/11): azul vivo à esquerda,
    azul-noite à direita, sem variação na vertical"""
    pts = [(0.0, (77, 97, 215)), (0.208, (59, 80, 201)), (0.417, (40, 62, 187)), (0.573, (28, 49, 170)),
           (0.729, (19, 38, 145)), (0.807, (15, 32, 132)), (1.0, (4, 19, 103))]
    x = np.linspace(0, 1, max(w, 1))
    c = np.stack([np.interp(x, [p_[0] for p_ in pts], [p_[1][k] for p_ in pts]) for k in range(3)], 1)
    rgb = np.repeat(c[None, :, :], max(h, 1), 0)
    return Image.fromarray(np.dstack([rgb, np.full(rgb.shape[:2] + (1,), 255)]).astype(np.uint8), "RGBA")


def _pasta(base, chave, dados):
    sig = hashlib.md5(json.dumps([dados, os.path.getmtime(__file__)], sort_keys=True, default=str).encode()).hexdigest()[:12]
    d = os.path.join(base, f"{chave}_{sig}")
    return d, os.path.join(d, "%04d.png")


def _sombra(im, raio, alfa, S):
    a = im.split()[3].filter(ImageFilter.GaussianBlur(raio * S))
    s = Image.new("RGBA", im.size, (0, 0, 0, 0))
    s.putalpha(a.point(lambda v: v * alfa // 255))
    return Image.alpha_composite(s, im)


def _saida(tt, dur, d=0.34):
    """0 na entrada e no meio, sobe até 1 nos últimos d segundos"""
    return _entra((tt - (dur - d)) / d)


# ======================================================================= glossário

def glossario(base, chave, termo, texto, dur, W, H, S, fps):
    n = int(round(dur * fps))
    dirq, padrao = _pasta(base, chave, [termo, texto, dur, W, H, S, fps])
    larg = int(880 * S); pad = int(28 * S); barra = int(30 * S); off = int(10 * S)
    f_t, f_d = _f("Inter-Bold.otf", 29 * S), _f("Inter-Medium.otf", 29 * S)
    dd = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    esp = dd.textlength(" ", font=f_d)
    # quebra em linhas: o termo (com dois-pontos) é a primeira "palavra", em negrito
    pals = [(termo + ":", f_t)] + [(p, f_d) for p in texto.split()]
    linhas, atual, w_at = [], [], 0
    for p, f in pals:
        wp = dd.textlength(p, font=f)
        if atual and w_at + esp + wp > larg - 2 * pad:
            linhas.append(atual); atual, w_at = [], 0
        atual.append((p, f, wp)); w_at += (esp if w_at else 0) + wp
    linhas.append(atual)
    lh = int(41 * S)
    alt = barra + pad + len(linhas) * lh + pad - int(6 * S)
    cw, ch = larg + off + int(40 * S), alt + off + int(60 * S)
    x0 = (W - cw) // 2 // 2 * 2
    y0 = int(H - 96 * S - ch) // 2 * 2
    if os.path.exists(os.path.join(dirq, f"{n - 1:04d}.png")):
        return padrao, n, (x0, y0)
    os.makedirs(dirq, exist_ok=True)

    # o cartão parado (sem o texto), desenhado uma vez
    cx, cy = int(20 * S), int(30 * S)
    cartao = Image.new("RGBA", (larg, alt), (0, 0, 0, 0))
    m = _forma(larg, alt, int(12 * S))
    corpo = Image.new("RGBA", (larg, alt), BRANCO + (255,)); corpo.putalpha(m)
    cartao.alpha_composite(corpo)
    ImageDraw.Draw(cartao).rounded_rectangle([0, 0, larg - 1, alt - 1], radius=int(12 * S), outline=INK + (255,),
                                             width=max(int(2 * S), 1))
    placa = _grad(larg, alt); placa.putalpha(m)
    # posições de cada palavra
    pos = []
    y = barra + pad - int(4 * S)
    for ln in linhas:
        x = pad
        for p, f, wp in ln:
            pos.append((p, f, x, y)); x += wp + esp
        y += lh

    def palavra(p, f):
        im = Image.new("RGBA", (int(dd.textlength(p, font=f) + 8 * S), int(50 * S)), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 0), p, font=f, fill=INK + (255,))
        return im
    pal_img = [palavra(p, f) for p, f, _, _ in pos]

    for i in range(n):
        tt = i / fps
        cam = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        a = _sai(tt / 0.42); e = _saida(tt, dur)
        k = a * (1 - e)
        if k > 0.002:
            dy = (1 - a) * 28 * S + e * 22 * S
            esc = 0.965 + 0.035 * a
            # sombra deslocada em degradê, chegando um pouco depois
            o = _sai((tt - 0.08) / 0.45) * off
            cam.alpha_composite(_alfa(placa, k), (cx + int(o), cy + int(o + dy)))
            c = cartao.copy()
            dc = ImageDraw.Draw(c)
            # a barra de cima corre da esquerda pra direita
            wb = int(larg * _sai((tt - 0.10) / 0.45))
            if wb > 2:
                b = _grad(larg, barra).crop((0, 0, wb, barra))
                mb = _forma(larg, alt, int(12 * S)).crop((0, 0, wb, barra))
                b.putalpha(mb)
                c.alpha_composite(b, (0, 0))
                dc.line([0, barra, larg, barra], fill=INK + (255,), width=max(int(2 * S), 1))
            for j in range(3):                 # os três pontos acendem um depois do outro
                aj = _sai((tt - 0.28 - 0.06 * j) / 0.2)
                if aj > 0:
                    r = 4.5 * S * (0.6 + 0.4 * aj)
                    px, py = 20 * S + j * 17 * S, barra / 2
                    dc.ellipse([px - r, py - r, px + r, py + r], fill=(255, 255, 255, int(255 * aj)))
            for j, ((p, f, x, y), im) in enumerate(zip(pos, pal_img)):
                aw = _sai((tt - 0.32 - 0.042 * j) / 0.3)
                if aw > 0:
                    c.alpha_composite(_alfa(im, aw), (int(x), int(y + (1 - aw) * 9 * S)))
            if esc < 0.999:
                c = c.resize((int(larg * esc), int(alt * esc)), Image.LANCZOS)
            cam.alpha_composite(_alfa(c, k), (cx + (larg - c.width) // 2, cy + int(dy) + (alt - c.height) // 2))
        cam.save(os.path.join(dirq, f"{i:04d}.png"), compress_level=1)
    return padrao, n, (x0, y0)


# ======================================================================= nome

def nome(base, chave, nome_, papel, lado, dur, W, H, S, fps):
    n = int(round(dur * fps))
    dirq, padrao = _pasta(base, chave, [nome_, papel, lado, dur, W, H, S, fps, "traço do nome inteiro"])
    f_n, f_p = _f("Inter-ExtraBold.otf", 66 * S), _f("Inter-Medium.otf", 26 * S)
    tn, tp = -66 * 0.025 * S, 26 * 0.05 * S
    dd = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    letras = [(c, dd.textlength(c, font=f_n)) for c in nome_.upper()]
    wn = sum(w for _, w in letras) + tn * (len(letras) - 1)
    pal = papel.upper().split()
    esp = dd.textlength(" ", font=f_p) + tp
    wps = [sum(dd.textlength(c, font=f_p) + tp for c in p) - tp for p in pal]
    wp = sum(wps) + esp * (len(pal) - 1)
    cw, ch = int(max(wn, wp) + 80 * S), int(150 * S)
    margem = int(110 * S)
    x0 = (W - margem - cw + int(40 * S)) if lado == "dir" else margem - int(40 * S)
    x0 = x0 // 2 * 2
    y0 = int(H - 118 * S - ch) // 2 * 2
    if os.path.exists(os.path.join(dirq, f"{n - 1:04d}.png")):
        return padrao, n, (x0, y0)
    os.makedirs(dirq, exist_ok=True)
    pad = int(40 * S)
    xn = (cw - pad - wn) if lado == "dir" else pad
    xp = (cw - pad - wp) if lado == "dir" else pad
    yn, yp = int(10 * S), int(96 * S)

    def glifo(c, f, cor):
        im = Image.new("RGBA", (int(dd.textlength(c, font=f) + 12 * S), int(f.size * 1.4)), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 0), c, font=f, fill=cor)
        return im
    g_n = [glifo(c, f_n, (255, 255, 255, 255)) for c, _ in letras]
    g_p = [glifo(p, f_p, (226, 230, 245, 255)) for p in pal]

    for i in range(n):
        tt = i / fps
        cam = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        e = _saida(tt, dur, 0.32)
        x = xn
        for j, ((c, w), im) in enumerate(zip(letras, g_n)):
            a = _sai((tt - 0.022 * j) / 0.42) * (1 - e)
            if a > 0.002:
                cam.alpha_composite(_alfa(im, a), (int(x), int(yn + (1 - a) * 30 * S + e * 10 * S)))
            x += w + tn
        # o traço da marca corre por baixo do nome inteiro (15/11: "a linha azul não tem o tamanho do nome")
        at = _sai((tt - 0.18) / 0.5) * (1 - e)
        if at > 0.01:
            wt = int(wn * at)
            b = _grad(int(wn) + 1, int(5 * S)).crop((0, 0, max(wt, 1), int(5 * S)))
            b.putalpha(_forma(max(wt, 1), int(5 * S), int(2.5 * S)))
            xt = (xn + wn - wt) if lado == "dir" else xn
            cam.alpha_composite(_alfa(b, at), (int(xt), int(yp - 14 * S)))
        x = xp
        for j, (im, w) in enumerate(zip(g_p, wps)):
            a = _sai((tt - 0.30 - 0.05 * j) / 0.4) * (1 - e)
            if a > 0.002:
                cam.alpha_composite(_alfa(im, a), (int(x), int(yp + (1 - a) * 10 * S + e * 8 * S)))
            x += w + esp
        cam = _sombra(cam, 9, 170, S)
        cam.save(os.path.join(dirq, f"{i:04d}.png"), compress_level=1)
    return padrao, n, (x0, y0)


# ======================================================================= quem é, com seta

def _curva(p0, p1, dobra):
    """arco de p0 a p1 (bézier quadrática), curvado pra direita de quem vai de p0 a p1"""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    c = ((x0 + x1) / 2 - dy * dobra, (y0 + y1) / 2 + dx * dobra)
    t = np.linspace(0, 1, 90)[:, None]
    return (1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(c) + t ** 2 * np.array(p1)


def seta(base, chave, nome_, papel, texto, alvos, dur, W, H, S, fps):
    """quem é a pessoa apontada (16/11, o designer: "coloca o nome dele puxando uma setinha" e o contexto "num textinho,
    numa barrinha"). O nome e o papel no desenho do cartão de nome, embaixo à esquerda; embaixo deles a barra no degradê
    da marca com o contexto; e uma seta que se desenha do nome até a pessoa e segue ela no quadro (câmera na mão).
    alvos = [(x, y, h)] em pixels, um por quadro: o centro do rosto e a altura dele. Folha do tamanho da tela."""
    n = len(alvos)
    dirq, padrao = _pasta(base, chave, [nome_, papel, texto, [[round(v, 1) for v in a] for a in alvos], dur, W, H, S, fps])
    if os.path.exists(os.path.join(dirq, f"{n - 1:04d}.png")):
        return padrao, n, (0, 0)
    os.makedirs(dirq, exist_ok=True)
    f_n, f_p, f_b = _f("Inter-ExtraBold.otf", 66 * S), _f("Inter-Medium.otf", 26 * S), _f("Inter-SemiBold.otf", 31 * S)
    tn, tp = -66 * 0.025 * S, 26 * 0.05 * S
    dd = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    letras = [(c, dd.textlength(c, font=f_n)) for c in nome_.upper()]
    wn = sum(w for _, w in letras) + tn * (len(letras) - 1)
    pal = papel.upper().split()
    esp_p = dd.textlength(" ", font=f_p) + tp
    wps = [sum(dd.textlength(c, font=f_p) + tp for c in p) - tp for p in pal]

    # a barra: o contexto quebrado em linhas de até 660 px, letra de 31 (lida no celular)
    pad_x, pad_y, lh = int(26 * S), int(19 * S), int(42 * S)
    esp_b = dd.textlength(" ", font=f_b)
    linhas, atual, w_at = [], [], 0
    for p in texto.split():
        wp = dd.textlength(p, font=f_b)
        if atual and w_at + esp_b + wp > 660 * S:
            linhas.append(atual); atual, w_at = [], 0
        atual.append((p, wp)); w_at += (esp_b if w_at else 0) + wp
    linhas.append(atual)
    larg_b = int(max(sum(w for _, w in ln) + esp_b * (len(ln) - 1) for ln in linhas) + 2 * pad_x)
    alt_b = 2 * pad_y + len(linhas) * lh - int(6 * S)
    x_t = int(110 * S)
    yb = int(H - 96 * S - alt_b)                 # topo da barra
    yp = yb - int(48 * S)                         # o papel
    yn = yp - int(86 * S)                         # o nome
    barra = _grad(larg_b, alt_b); barra.putalpha(_forma(larg_b, alt_b, int(12 * S)))
    pal_b = []
    y = yb + pad_y - int(3 * S)
    for ln in linhas:
        x = x_t + pad_x
        for p, wp in ln:
            pal_b.append((p, x, y)); x += wp + esp_b
        y += lh

    def glifo(c, f, cor):
        im = Image.new("RGBA", (int(dd.textlength(c, font=f) + 12 * S), int(f.size * 1.4)), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 0), c, font=f, fill=cor)
        return im
    g_n = [glifo(c, f_n, (255, 255, 255, 255)) for c, _ in letras]
    g_p = [glifo(p, f_p, (226, 230, 245, 255)) for p in pal]
    g_b = [glifo(p, f_b, (255, 255, 255, 255)) for p, _, _ in pal_b]

    # a seta sai da ponta do nome e para no pescoço da pessoa (nunca em cima do rosto); a posição anda suave
    ini = (x_t + wn + 30 * S, yn + 30 * S)
    sup = 3                                        # desenho em 3x e reduzido: traço liso
    for i in range(n):
        tt = i / fps
        cam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        e = _saida(tt, dur, 0.32)
        x = x_t
        for j, ((c, w), im) in enumerate(zip(letras, g_n)):
            a = _sai((tt - 0.022 * j) / 0.42) * (1 - e)
            if a > 0.002:
                cam.alpha_composite(_alfa(im, a), (int(x), int(yn + (1 - a) * 30 * S + e * 10 * S)))
            x += w + tn
        at = _sai((tt - 0.18) / 0.5) * (1 - e)
        if at > 0.01:
            wt = int(wn * at)
            b = _grad(int(wn) + 1, int(5 * S)).crop((0, 0, max(wt, 1), int(5 * S)))
            b.putalpha(_forma(max(wt, 1), int(5 * S), int(2.5 * S)))
            cam.alpha_composite(_alfa(b, at), (x_t, int(yp - 14 * S)))
        x = x_t
        for j, (im, w) in enumerate(zip(g_p, wps)):
            a = _sai((tt - 0.30 - 0.05 * j) / 0.4) * (1 - e)
            if a > 0.002:
                cam.alpha_composite(_alfa(im, a), (int(x), int(yp + (1 - a) * 10 * S + e * 8 * S)))
            x += w + esp_p
        # a barra abre da esquerda pra direita e o contexto entra palavra por palavra
        ab = _sai((tt - 0.50) / 0.5) * (1 - e)
        if ab > 0.01:
            wb = max(int(larg_b * _sai((tt - 0.50) / 0.5)), 2)
            cam.alpha_composite(_alfa(barra.crop((0, 0, wb, alt_b)), ab), (x_t, yb + int(e * 10 * S)))
            for j, ((p, px, py), im) in enumerate(zip(pal_b, g_b)):
                a = _sai((tt - 0.72 - 0.035 * j) / 0.35) * (1 - e)
                if a > 0.002 and px < x_t + wb:
                    cam.alpha_composite(_alfa(im, a), (int(px), int(py + (1 - a) * 8 * S + e * 10 * S)))
        # a seta: se desenha do nome até a pessoa e acompanha ela
        ds = _sai((tt - 0.40) / 0.55) * (1 - e)
        if ds > 0.01:
            fx, fy, fh = alvos[i]
            fim = (fx, fy + 1.05 * fh)
            pts = _curva(ini, fim, 0.22)
            k = max(int(len(pts) * _sai((tt - 0.40) / 0.55)), 2)
            pts = pts[:k]
            x0b, y0b = pts.min(0) - 40 * S
            x1b, y1b = pts.max(0) + 40 * S
            bw, bh = int(x1b - x0b), int(y1b - y0b)
            sub = Image.new("RGBA", (bw * sup, bh * sup), (0, 0, 0, 0))
            ds_ = ImageDraw.Draw(sub)
            q = [((px - x0b) * sup, (py - y0b) * sup) for px, py in pts]
            larg_s = int(5 * S * sup)
            ds_.line(q, fill=(255, 255, 255, 255), width=larg_s, joint="curve")
            for px, py in (q[0], q[-1]):
                r = larg_s / 2
                ds_.ellipse([px - r, py - r, px + r, py + r], fill=(255, 255, 255, 255))
            if k >= len(_curva(ini, fim, 0.22)) - 1:   # a ponta só aparece quando o traço chega
                (ax, ay), (bx, by) = q[-1], q[-6]
                ang = np.arctan2(ay - by, ax - bx)
                for d in (2.55, -2.55):
                    hx, hy = ax + 24 * S * sup * np.cos(ang + d), ay + 24 * S * sup * np.sin(ang + d)
                    ds_.line([(ax, ay), (hx, hy)], fill=(255, 255, 255, 255), width=larg_s)
                    ds_.ellipse([hx - larg_s / 2, hy - larg_s / 2, hx + larg_s / 2, hy + larg_s / 2], fill=(255, 255, 255, 255))
            sub = sub.resize((bw, bh), Image.LANCZOS)
            cam.alpha_composite(_alfa(sub, ds), (int(x0b), int(y0b)))
        cam = _sombra(cam, 9, 170, S)
        cam.save(os.path.join(dirq, f"{i:04d}.png"), compress_level=1)
    return padrao, n, (0, 0)


# ======================================================================= o L do QR code

def qr_painel(base, W, H, S, marca):
    """o fundo do L, inteiro (fica por baixo do vídeo encolhido): o degradê da marca e o C gigante a 9%"""
    p = os.path.join(base, f"qr_fundo2_{W}.png")
    if os.path.exists(p):
        return p
    os.makedirs(base, exist_ok=True)
    out = _grad(W, H)
    ic = Image.open(os.path.join(marca, "logo-convertfy-hd.png")).convert("RGBA")
    c = ic.crop((0, 0, int(ic.height * 1.08), ic.height))      # o símbolo fica no começo da logo
    c = c.crop(c.getbbox())
    lado = int(760 * S)
    c = c.resize((int(c.width * lado / c.height), lado), Image.LANCZOS)
    branco = Image.new("RGBA", c.size, (255, 255, 255, 0))
    branco.putalpha(c.split()[3].point(lambda v: v * 23 // 255))
    out.alpha_composite(branco, (int(330 * S), int(730 * S)))
    out.convert("RGB").save(p)
    return p


def _rico(linhas, tam, S, cor_b=(255, 255, 255, 255), cor_i=LILAS + (255,)):
    """chamada como nos cartões da Convertfy: grotesca em negrito e o pedaço em destaque em itálico com serifa lilás.
    linhas = [[(texto, "b" | "i"), ...], ...]; devolve uma imagem por linha"""
    f_b, f_i = _f("Inter-ExtraBold.otf", tam * S), _f("InstrumentSerif-Italic.ttf", tam * 1.18 * S)
    dd = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    out = []
    for ln in linhas:
        pecas = []
        for txt, est in ln:
            f = f_b if est == "b" else f_i
            tr = -tam * 0.03 * S if est == "b" else 0
            pecas.append((txt, f, tr, cor_b if est == "b" else cor_i))
        w = sum(sum(dd.textlength(c, font=f) + tr for c in t) for t, f, tr, _ in pecas)
        im = Image.new("RGBA", (int(w + 12 * S), int(tam * 1.55 * S)), (0, 0, 0, 0))
        d, x = ImageDraw.Draw(im), 0
        for t, f, tr, cor in pecas:
            dy = 0 if f is f_b else -int(tam * 0.12 * S)
            for c in t:
                d.text((x, dy + int(tam * 0.08 * S)), c, font=f, fill=cor); x += d.textlength(c, font=f) + tr
        out.append(im)
    return out


def qr(base, chave, dur, W, H, S, fps, marca, chamada, cta, sub=None, foto="bruno-autoridade.png"):
    """as peças do L por cima do fundo. Coluna: o QR num cartão branco e o texto em três linhas (a primeira em
    negrito). Faixa: a logo com "O time que vai cuidar do e-mail da sua loja" à esquerda, a chamada ao lado.
    Quem aparece: o Bruno recortado na coluna (foto=bruno-autoridade.png) ou a equipe no canto (foto=equipe-recorte.png).
    chamada = linhas ricas (ver _rico); cta = linhas do texto da coluna."""
    n = int(round(dur * fps))
    if not os.path.exists(os.path.join(marca, foto)):
        foto = "bruno-recorte.png"
    dirq, padrao = _pasta(base, chave, [dur, W, H, S, fps, chamada, cta, sub, foto, os.path.getmtime(os.path.join(marca, foto))])
    if os.path.exists(os.path.join(dirq, f"{n - 1:04d}.png")):
        return padrao, n, (0, 0)
    os.makedirs(dirq, exist_ok=True)
    vw, vh = int(W * QR_SC), int(H * QR_SC)
    col_cx = (vw + W) / 2
    dd = ImageDraw.Draw(Image.new("RGBA", (4, 4)))

    def linha(txt, f, cor=(255, 255, 255, 255), track=0.0):
        w = sum(dd.textlength(c, font=f) + track for c in txt) - track
        im = Image.new("RGBA", (int(w + 6 * S), int(f.size * 1.4)), (0, 0, 0, 0))
        d, x = ImageDraw.Draw(im), 0
        for c in txt:
            d.text((x, 0), c, font=f, fill=cor); x += d.textlength(c, font=f) + track
        return im
    # o QR num cartão branco de canto bem redondo
    qrimg = Image.open(os.path.join(marca, "qrcode-youtube-11-11.png")).convert("RGBA")
    lq = int(282 * S); padq = int(17 * S)
    cartao = Image.new("RGBA", (lq, lq), (0, 0, 0, 0))
    branco = Image.new("RGBA", (lq, lq), (255, 255, 255, 255)); branco.putalpha(_forma(lq, lq, int(24 * S)))
    cartao.alpha_composite(branco)
    cartao.alpha_composite(qrimg.resize((lq - 2 * padq, lq - 2 * padq), Image.NEAREST), (padq, padq))
    yq = int(42 * S)
    # o texto da coluna: três linhas, a primeira em negrito
    tam = 17
    l_cta = [linha(t, _f("Inter-Bold.otf" if j == 0 else "Inter-Medium.otf", tam * S),
                   (255, 255, 255, 255) if j == 0 else (228, 232, 255, 255), tam * 0.07 * S) for j, t in enumerate(cta)]
    yt = yq + lq + int(22 * S)
    # a faixa: logo e a frase do time empilhadas à esquerda
    logo = Image.open(os.path.join(marca, "logo-convertfy-hd.png")).convert("RGBA")
    lw = int(196 * S); logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    tag = linha("O time que vai cuidar do e-mail da sua loja", _f("Cabin-Medium-TTF.ttf", 19 * S), (205, 212, 255, 255), 0.2 * S)
    faixa_cy = (vh + H) / 2
    bloco_logo = logo.height + int(16 * S) + tag.height
    y_logo = faixa_cy - bloco_logo / 2
    xc = int(70 * S + max(lw, tag.width) + 80 * S)
    # quem aparece
    pessoa = Image.open(os.path.join(marca, foto)).convert("RGBA")
    if foto.startswith("equipe"):
        hp = int(205 * S)
        pessoa = pessoa.resize((int(pessoa.width * hp / pessoa.height), hp), Image.LANCZOS)
        xp = W - pessoa.width - int(14 * S)
        limite = xp - int(30 * S)
    else:
        hp = int(H - (yt + len(l_cta) * 24 * S + 40 * S))
        pessoa = pessoa.resize((int(pessoa.width * hp / pessoa.height), hp), Image.LANCZOS)
        if pessoa.width > (W - vw) * 1.25:
            cut = (pessoa.width - int((W - vw) * 1.25)) // 2
            pessoa = pessoa.crop((cut, 0, pessoa.width - cut, hp))
        xp = col_cx - pessoa.width / 2 + 8 * S
        limite = vw - int(30 * S)
    # a chamada encolhe até caber entre a logo e quem aparece
    for t_c in (52, 48, 44, 40, 36):
        linhas_c = _rico(chamada, t_c, S)
        if max(im.width for im in linhas_c) <= limite - xc:
            break
    lh_c = t_c * 1.2 * S
    l_sub = linha(sub, _f("Cabin-SemiBold-TTF.ttf", 22 * S), LILAS + (255,), 22 * 0.02 * S) if sub else None

    for i in range(n):
        tt = i / fps
        cam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        e = _entra((tt - (dur - 0.95)) / 0.35)          # as peças saem antes do vídeo voltar ao tamanho

        def poe(im, x, y, t0, dy=24, dx=0, d=0.5):
            a = _sai((tt - t0) / d) * (1 - e)
            if a > 0.002:
                cam.alpha_composite(_alfa(im, a), (int(x + (1 - a) * dx * S), int(y + (1 - a) * dy * S + e * 12 * S)))
        a_q = _sai((tt - 0.55) / 0.55) * (1 - e)
        if a_q > 0.002:
            esc = 0.88 + 0.12 * a_q
            c = cartao.resize((int(lq * esc), int(lq * esc)), Image.LANCZOS)
            cam.alpha_composite(_alfa(_sombra(c, 16, 90, S), a_q), (int(col_cx - c.width / 2), int(yq + (lq - c.height) / 2)))
        for j, im in enumerate(l_cta):
            poe(im, col_cx - im.width / 2, yt + j * 24 * S, 0.80 + 0.06 * j, dy=12)
        poe(pessoa, xp, H - pessoa.height, 0.62, dy=60, d=0.7)
        poe(logo, 70 * S, y_logo, 0.58, dy=0, dx=-40)
        poe(tag, 70 * S, y_logo + logo.height + 16 * S, 0.70, dy=10)
        alt_c = len(linhas_c) * lh_c + (38 * S if l_sub else 0)
        y0c = faixa_cy - alt_c / 2 - 6 * S
        for j, im in enumerate(linhas_c):
            poe(im, xc, y0c + j * lh_c, 0.72 + 0.09 * j, dy=18)
        if l_sub:
            poe(l_sub, xc + 2 * S, y0c + len(linhas_c) * lh_c + 6 * S, 0.95, dy=10)
        cam.save(os.path.join(dirq, f"{i:04d}.png"), compress_level=1)
    return padrao, n, (0, 0)
