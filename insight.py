"""Insight da Convertfy enquanto a pessoa fala o número.

Identidade: a pílula com o degradê do símbolo (violeta #5B2BFF para azul #6FA0FF) nasce do C e abre revelando a
etiqueta; o número em Gilroy (a grotesca mais perto da logo) entra desfocado e conta até o valor no tempo em que é
dito; um traço em degradê corre por baixo; a frase entra palavra por palavra. Na tela o bloco aproxima devagar
(nunca fica parado) e sai subindo e desfocando. Sem véu nem caixa: a leitura vem da sombra macia do próprio texto.

Formatos (campo `modo`):
  numero  rotulo, g, p                      o número conta (de=valor inicial, conta_em=atraso)
  versus  rotulo, g, g2, n1, n2[, em2, p]   dois números lado a lado, com quem apostou embaixo
  antes   rotulo, a, g[, depois_em, p]      o antes pequeno e apagado, a seta se desenha, o depois conta
  frase   rotulo, linhas=[(texto, atraso, destaque)]   palavra por palavra, destaque no degradê
Lugar (`onde`): baixo (padrão), alto, esquerda, direita. Escolhido pelo plano de baixo: nunca no rosto.
"""
import os, re, json, hashlib
import fontes
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

VIOLETA, AZUL_CLARO = (91, 43, 255), (111, 160, 255)
LUGAR = {"baixo": (0.5, 0.70), "alto": (0.5, 0.27), "esquerda": (0.28, 0.66), "direita": (0.72, 0.66)}


def _f(nome, tam):
    return ImageFont.truetype(fontes.tipo(nome), max(int(round(tam)), 1))


def _sai(x):     # ease-out forte: começa rápido, assenta devagar
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 4


def _entra(x):
    x = min(max(x, 0.0), 1.0)
    return x * x


def _degrade(w, h):
    x = np.linspace(0, 1, max(w, 1))[None, :, None]
    c = np.array(VIOLETA)[None, None, :] * (1 - x) + np.array(AZUL_CLARO)[None, None, :] * x
    rgb = np.repeat(c, max(h, 1), 0)
    return Image.fromarray(np.dstack([rgb, np.full(rgb.shape[:2] + (1,), 255)]).astype(np.uint8), "RGBA")


def _forma(w, h, raio):
    m = Image.new("L", (max(w, 1), max(h, 1)), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, max(w, 1) - 1, max(h, 1) - 1], radius=raio, fill=255)
    return m


def _alfa(im, k):
    if k >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.split()[3].point(lambda v: int(v * k)))
    return im


def _larg(f, txt, tr):
    d = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    return sum(d.textlength(ch, font=f) + tr for ch in txt) - tr if txt else 0


class Pecas:
    def __init__(self, S, marca):
        self.S, self.marca, self._c = S, marca, {}

    def texto(self, txt, f, tr=0, cor=(255, 255, 255, 255), grad=False):
        """texto num PNG justo com folga pra desfoque; devolve (img, folga, largura, altura da letra maiúscula)"""
        k = (txt, f.path, f.size, tr, cor, grad)
        if k in self._c:
            return self._c[k]
        fol = int(26 * self.S)
        asc, desc = f.getmetrics()
        top = f.getbbox("H")[1]
        alt = asc - top
        w = int(_larg(f, txt, tr)) + 2
        im = Image.new("RGBA", (w + 2 * fol, alt + desc // 2 + 2 * fol), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        x = fol
        for ch in txt:
            d.text((x, fol - top), ch, font=f, fill=cor)
            x += d.textlength(ch, font=f) + tr
        if grad:
            g = _degrade(im.width, im.height)
            g.putalpha(im.split()[3])
            im = g
        self._c[k] = (im, fol, w, alt)
        return self._c[k]

    def icone(self, alt):
        im = Image.open(os.path.join(self.marca, "logo-convertfy-hd.png")).convert("RGBA").crop((0, 0, 290, 285))
        im = im.crop(im.getbbox())
        a = im.split()[3].resize((round(im.width * alt / im.height), alt), Image.LANCZOS)
        out = Image.new("RGBA", a.size, (255, 255, 255, 0))
        out.putalpha(a)
        return out


def gera(pasta, chave, ins, dur, W, H, S, fps, marca):
    """renderiza a sequência do insight e devolve (padrão dos PNGs, quadros, (x, y) na tela)"""
    n = int(round(dur * fps))
    sig = hashlib.md5(json.dumps([ins, dur, W, H, S, fps, os.path.getmtime(__file__)], sort_keys=True,
                                 default=str).encode()).hexdigest()[:12]
    dirq = os.path.join(pasta, f"{chave}_{sig}")
    padrao = os.path.join(dirq, "%04d.png")
    cw, ch = min(W, int(1560 * S)), int(640 * S)
    fx, fy = LUGAR[ins.get("onde", "baixo")]
    x0 = int(min(max(W * fx - cw / 2, 0), W - cw)) // 2 * 2
    y0 = int(min(max(H * fy - ch / 2, 0), H - ch)) // 2 * 2
    if os.path.exists(os.path.join(dirq, f"{n - 1:04d}.png")):
        return padrao, n, (x0, y0)
    os.makedirs(dirq, exist_ok=True)

    P = Pecas(S, marca)
    modo = ins.get("modo", "numero")
    big = ins.get("tam", 150 if modo != "frase" else 112)
    f_big = _f("Gilroy-ExtraBold.ttf", big * S); t_big = -big * 0.02 * S
    f_med = _f("Gilroy-ExtraBold.ttf", big * 0.5 * S)
    f_rot = _f("Gilroy-Bold.ttf", 26 * S); t_rot = 26 * 0.13 * S
    f_leg = _f("Gilroy-SemiBold.ttf", 42 * S)
    f_nome = _f("Gilroy-Bold.ttf", 28 * S); t_nome = 28 * 0.12 * S
    claro = (236, 239, 255, 255)
    cxb = cw / 2                                        # centro do bloco no quadro de desenho

    # ---------------------------------------------------------------- pílula (nasce do C e abre)
    rot = ins.get("rotulo", "").upper()
    ic = P.icone(int(32 * S))
    ph = int(60 * S)
    r_img, r_fol, r_w, r_alt = P.texto(rot, f_rot, t_rot)
    pw = int(22 * S + ic.width + 13 * S + r_w + 26 * S)
    pilula = _degrade(pw, ph)
    pilula.alpha_composite(ic, (int(22 * S), (ph - ic.height) // 2))
    pilula.alpha_composite(r_img, (int(22 * S + ic.width + 13 * S - r_fol), int((ph - r_alt) / 2 - r_fol)))

    def poe_pilula(cam, tt, y):
        a = _sai(tt / 0.3)
        if a <= 0:
            return
        abre = _sai((tt - 0.12) / 0.5)
        w = int(ph + (pw - ph) * abre)
        peca = pilula.crop((0, 0, w, ph))
        peca.putalpha(Image.fromarray(np.minimum(np.array(peca.split()[3]), np.array(_forma(w, ph, ph // 2)))))
        esc = 0.86 + 0.14 * a
        if esc < 0.999:
            peca = peca.resize((max(int(peca.width * esc), 1), max(int(ph * esc), 1)), Image.LANCZOS)
        # abre a partir do C: a ponta esquerda fica onde a pílula inteira vai começar
        cam.alpha_composite(_alfa(peca, a), (int(cxb - pw / 2), int(y + (ph - peca.height) / 2)))

    def poe(cam, img, x, y, tt, t0, d=0.45, dy=26, blur=9):
        a = _sai((tt - t0) / d)
        if a <= 0:
            return
        if blur and a < 0.98:
            img = img.filter(ImageFilter.GaussianBlur((1 - a) * blur * S))
        cam.alpha_composite(_alfa(img, a), (int(x), int(y + (1 - a) * dy * S)))

    def conta(g, tt, t0, de=0):
        m = re.match(r"^(.*?)(\d+)(.*)$", g)
        if not m or len(re.findall(r"\d+", g)) != 1:
            return g
        k = _sai((tt - t0) / 0.85)
        return f"{m.group(1)}{int(round(de + (int(m.group(2)) - de) * k))}{m.group(3)}"

    def traco(cam, x, y, w, tt, t0):
        a = _sai((tt - t0) / 0.6)
        if a <= 0:
            return
        b = _degrade(int(w), int(7 * S))
        b.putalpha(_forma(int(w), int(7 * S), int(3.5 * S)))
        cam.alpha_composite(b.crop((0, 0, max(int(w * a), 1), b.height)), (int(x), int(y)))

    def legenda(cam, txt, y, tt, t0):
        if not txt:
            return
        pals = txt.split()
        esp = ImageDraw.Draw(Image.new("RGBA", (4, 4))).textlength(" ", font=f_leg)
        larg = sum(P.texto(p_, f_leg, cor=claro)[2] for p_ in pals) + esp * (len(pals) - 1)
        x = cxb - larg / 2
        for i, p_ in enumerate(pals):
            img, fol, w, _ = P.texto(p_, f_leg, cor=claro)
            poe(cam, img, x - fol, y - fol, tt, t0 + i * 0.045, d=0.38, dy=12, blur=5)
            x += w + esp

    # ---------------------------------------------------------------- cada formato
    desloc = [0]

    def desenha(tt):
        y_pil = int(40 * S) + desloc[0]
        y_top = y_pil + (ph + int(28 * S) if rot else 0)
        cam = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        if rot:
            poe_pilula(cam, tt, y_pil)
        if modo == "numero":
            g = ins["g"]
            _, fol, w_fin, alt = P.texto(g, f_big, t_big)
            img, fol, w, alt = P.texto(conta(g, tt, ins.get("conta_em", 0.12), ins.get("de", 0)), f_big, t_big)
            x = cxb - w_fin / 2
            poe(cam, img, x - fol, y_top - fol, tt, 0.1)
            traco(cam, x, y_top + alt + 22 * S, w_fin, tt, 0.34)
            legenda(cam, ins.get("p", ""), y_top + alt + 50 * S, tt, 0.46)
        elif modo == "versus":
            em2 = ins.get("em2", 0.4)
            gap = 120 * S
            _, fo1, w1, alt = P.texto(ins["g"], f_big, t_big)
            _, fo2, w2, _ = P.texto(ins["g2"], f_big, t_big)
            larg = w1 + gap + w2
            x1, x2 = cxb - larg / 2, cxb - larg / 2 + w1 + gap
            i1 = P.texto(conta(ins["g"], tt, 0.12), f_big, t_big)[0]
            i2 = P.texto(conta(ins["g2"], tt, em2 + 0.02), f_big, t_big)[0]
            poe(cam, i1, x1 - fo1, y_top - fo1, tt, 0.1)
            poe(cam, i2, x2 - fo2, y_top - fo2, tt, em2)
            xs, xs_f, xs_w, xs_alt = P.texto("×", f_med, 0, grad=True)
            poe(cam, xs, x1 + w1 + gap / 2 - xs_w / 2 - xs_f, y_top + (alt - xs_alt) / 2 - xs_f, tt, em2 - 0.1)
            traco(cam, x1, y_top + alt + 22 * S, w1, tt, 0.34)
            traco(cam, x2, y_top + alt + 22 * S, w2, tt, em2 + 0.24)
            for nome, x, w, t0 in ((ins.get("n1", ""), x1, w1, 0.46), (ins.get("n2", ""), x2, w2, em2 + 0.36)):
                im, fo, wn, _ = P.texto(nome.upper(), f_nome, t_nome, cor=claro)
                poe(cam, im, x + w / 2 - wn / 2 - fo, y_top + alt + 50 * S - fo, tt, t0, d=0.38, dy=12, blur=5)
            legenda(cam, ins.get("p", ""), y_top + alt + 112 * S, tt, em2 + 0.5)
        elif modo == "antes":
            dep = ins.get("depois_em", 0.5)
            ia, foa, wa, alta = P.texto(ins["a"], f_med, -big * 0.01 * S, cor=(255, 255, 255, 150))
            _, fob, wb_fin, alt = P.texto(ins["g"], f_big, t_big)
            ib = P.texto(conta(ins["g"], tt, dep + 0.05, ins.get("de", 0)), f_big, t_big)[0]
            seta_w, gap = 92 * S, 36 * S
            larg = wa + gap + seta_w + gap + wb_fin
            xa = cxb - larg / 2
            ya = y_top + alt - alta                       # o antes senta na mesma linha de base
            poe(cam, ia, xa - foa, ya - foa, tt, 0.08)
            k = _sai((tt - dep) / 0.35)                   # risco no antes quando o depois chega
            if k > 0:
                ImageDraw.Draw(cam).rounded_rectangle([xa, ya + alta * 0.48, xa + wa * k, ya + alta * 0.48 + 5 * S],
                                                      radius=int(2.5 * S), fill=(255, 255, 255, 170))
            k = _sai((tt - dep + 0.1) / 0.4)              # a seta se desenha
            if k > 0:
                xs, ys = xa + wa + gap, y_top + alt * 0.55
                seta = Image.new("RGBA", (int(seta_w + 6 * S), int(40 * S)), (0, 0, 0, 0))
                ds = ImageDraw.Draw(seta)
                ds.rounded_rectangle([0, 17 * S, max(seta_w * k, 6 * S), 23 * S], radius=int(3 * S), fill=(255, 255, 255, 255))
                if k > 0.6:
                    ds.polygon([(seta_w * k - 22 * S, 5 * S), (seta_w * k + 2 * S, 20 * S), (seta_w * k - 22 * S, 35 * S)],
                               fill=(255, 255, 255, 255))
                g = _degrade(seta.width, seta.height); g.putalpha(seta.split()[3])
                cam.alpha_composite(g, (int(xs), int(ys - 20 * S)))
            xb = xa + wa + gap + seta_w + gap
            poe(cam, ib, xb - fob, y_top - fob, tt, dep)
            traco(cam, xb, y_top + alt + 22 * S, wb_fin, tt, dep + 0.24)
            legenda(cam, ins.get("p", ""), y_top + alt + 50 * S, tt, dep + 0.36)
        elif modo == "frase":
            y = y_top
            esp = ImageDraw.Draw(Image.new("RGBA", (4, 4))).textlength(" ", font=f_big)
            for texto, t0, dest in ins["linhas"]:
                pecas = [P.texto(p_, f_big, t_big, grad=dest) for p_ in texto.split()]
                larg = sum(pc[2] for pc in pecas) + esp * (len(pecas) - 1)
                x = cxb - larg / 2
                for i, (img, fol, w, alt) in enumerate(pecas):
                    poe(cam, img, x - fol, y - fol, tt, t0 + i * 0.09, d=0.42, dy=30, blur=10)
                    x += w + esp
                y += pecas[0][3] + 44 * S
            legenda(cam, ins.get("p", ""), y + 10 * S, tt, ins["linhas"][-1][1] + 0.3)
        return cam

    # o bloco inteiro centraliza na altura do quadro de desenho (cai onde `onde` manda)
    bb = desenha(max(dur - 0.4, 0)).getbbox()
    if bb:
        desloc[0] = int(ch / 2 - (bb[1] + bb[3]) / 2)
    for q in range(n):
        tt = q / fps
        cam = desenha(tt)
        # aproxima devagar enquanto fica na tela (nunca parado)
        esc = 1 + 0.035 * (tt / dur)
        bb = cam.getbbox()
        if bb:
            bloco = cam.crop(bb)
            bloco = bloco.resize((max(int(bloco.width * esc), 1), max(int(bloco.height * esc), 1)), Image.BILINEAR)
            cx_, cy_ = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
            cam = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            cam.alpha_composite(bloco, (int(cx_ - bloco.width / 2), int(cy_ - bloco.height / 2)))
        # sombra macia (leitura sem véu): uma larga e uma curta
        a = cam.split()[3]
        larga = np.array(a.filter(ImageFilter.GaussianBlur(20 * S))).astype(np.int32) * 165 // 255
        curta = np.array(a.filter(ImageFilter.GaussianBlur(4 * S))).astype(np.int32) * 90 // 255
        quadro = Image.new("RGBA", cam.size, (0, 0, 0, 0))
        quadro.putalpha(Image.fromarray(np.maximum(larga, curta).astype(np.uint8)))
        quadro.alpha_composite(cam)
        # saída: sobe, desfoca e some
        fora = _entra((tt - (dur - 0.34)) / 0.34)
        if fora > 0:
            quadro = _alfa(quadro.filter(ImageFilter.GaussianBlur(fora * 8 * S)), 1 - fora)
            q2 = Image.new("RGBA", quadro.size, (0, 0, 0, 0))
            q2.paste(quadro, (0, -int(fora * 16 * S)))
            quadro = q2
        quadro.save(os.path.join(dirq, f"{q:04d}.png"), compress_level=1)
    return padrao, n, (x0, y0)
