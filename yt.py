"""yt.py: o vídeo do YouTube do Black Experience (16:9), montado a partir do ROTEIRO de linha_yt.py.

    ESC=1 caffeinate -i .venv/bin/python yt.py   -> render/black-experience-1080p.mp4  (validação)
    ESC=2 caffeinate -i .venv/bin/python yt.py   -> render/black-experience-4k.mp4     (entrega)

Imagem: FX30 em 4K 59,94p S-Log3. Cada pedaço vira um arquivo no cache (recorte, LUT, acabamento): ProRes no 1080p,
HEVC 10 bits no 4K (ProRes 4K de 10 min não cabe no disco). B-roll em câmera lenta 50% (60p tocado a 30).
Fala em tempo real, sem respiração, com o zoom alternando a cada emenda (esconde o corte). Quem fala fica no centro.

Corte J e L (o "efeito" que o Matheus pediu): no J a voz do bloco seguinte entra antes da imagem dele (o plano anterior
continua por `j` segundos); no L a imagem do bloco entra antes e a fala do bloco anterior termina por cima (`l` segundos).
O som nunca sai de sincronia: o que se estica é sempre a imagem do próprio clipe, no tempo certo dele.

Letreiros em PNG (PIL), na escala da saída, animados no overlay: entram com ease-out forte e saem mais rápido pelo mesmo
caminho. Som: voz limpa, trilha 13 dB abaixo da fala com ducking, efeitos no quadro da animação, -14 LUFS.
"""
import os, sys, json, hashlib, subprocess
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import enquadra, respiros, insight, fontes, som_cinema, cards

ESC = int(os.environ.get("ESC", "1"))
W, H = 1920 * ESC, 1080 * ESC
S = ESC                                   # escala dos letreiros (desenhados em 1080 e multiplicados)
FPS_S, FPS, SR = "30000/1001", 30000 / 1001, 48000
CACHE = os.path.join(AQUI, "cache")
TRECHOS = os.path.join(CACHE, f"trechos{H}")
GRAF = os.path.join(CACHE, f"graf{H}")
MARCA = os.path.join(AQUI, "marca")
SFX = os.path.join(AQUI, "sfx")
SAIDA = os.path.join(AQUI, "render", "black-experience-4k.mp4" if ESC == 2 else "black-experience-1080p.mp4")
ZMAX = 1.5                                # 4K de saída: acima disso o recorte já amolece

# Padrão de enquadramento (pedido de 15/11: "ancorar certo e enquadrar certo, tratar as cenas de maneira igualitária").
# Toda fala tem o rosto do mesmo tamanho na tela e no mesmo lugar, venha de que câmera vier:
ROSTO_AB, ROSTO_FE = 0.17, 0.215         # altura do rosto no plano aberto e no fechado (fração da altura da tela)
OLHOS = 0.36                              # olhos a 36% da altura, rosto no centro na horizontal
ANCORA = 0.05                             # o centro de cada pedaço só sai da âncora do bloco se a pessoa andou mais que isso

# tokens da marca (tela ao vivo bf.convertfy.me)
BG, AZUL, AZUL_HI, AZUL_NOITE = (7, 8, 11), (76, 97, 215), (142, 158, 255), (6, 20, 107)
INK, INK2 = (242, 243, 247), (169, 174, 192)


def clip(n):
    return fontes.caminho(n)


def nq(t):
    return int(round(t * FPS))


def sh(cmd):
    subprocess.run(cmd, check=True)


# ======================================================================= imagem

def recorte(z, cx, cy, fw=3840, fh=2160):
    if z <= 1.001:
        return ""
    cw, ch = int(round(fw / z / 2)) * 2, int(round(fh / z / 2)) * 2
    x = int(min(max(cx * fw - cw / 2, 0), fw - cw)) // 2 * 2
    y = int(min(max(cy * fh - ch / 2, 0), fh - ch)) // 2 * 2
    return f"crop={cw}:{ch}:{x}:{y},"


def filtro(p):
    """o filtro de imagem de um pedaço (o sync.py usa o mesmo pra achar o pedaço no cache). Imagem de apoio gravada a
    24 ou 25 quadros ganha quadro intermediário pelo movimento em vez de quadro repetido: repetir um quadro a cada
    quatro some na fala, mas no kart e no carro vira engasgo ("pegou uns takes travados no kart").
    Sem estabilizador: o deshake girava e pulava o quadro inteiro quando gente andava na frente, e a logo parada por
    cima denunciava (16/11: "o take da Black Experience 11/11 tá travando, tremendo, não travava antes")"""
    tempo = "setpts=2*(PTS-STARTPTS)," if p["lento"] else ""
    rec = f"{recorte(p['z'], p['cx'], p['cy'], *fontes.dims(p['src']))}scale={W}:{H}:flags=lanczos,"
    if p.get("interp"):
        # o fps no fim amarra os quadros na grade: perto do fim do clipe o minterpolate fica sem quadro à frente e
        # deixava um buraco de 3 quadros nos tempos; o pedaço do 1408 (1,5 s de arquivo) empurrou o resto do kart 2 quadros
        return (f"{tempo}{rec}minterpolate=fps={FPS_S}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
                f"{fontes.cor(p['src'])},tpad=stop_mode=clone:stop_duration=3,fps={FPS_S}")
    return f"{tempo}fps={FPS_S},{rec}{fontes.cor(p['src'])},tpad=stop_mode=clone:stop_duration=3"


def decodifica(src):
    """decodificador do Mac só pra HEVC e drone: no H.264 da Sony (4:2:2 de 10 bits e alguns 8 bits) ele falha em
    quadros soltos e o ffmpeg repete o anterior; daí vinham os 0,4 s parados no começo dos planos e o trecho da Bosch"""
    hevc = fontes._probe(src)["codec"] == "hevc"
    return ["-hwaccel", "videotoolbox"] if hevc or (isinstance(src, str) and src.startswith("d")) else []


def chave_peca(p, n, vf, dec):
    """o nome do pedaço no cache (o sync.py acha o pedaço por ela); sem a pasta do repositório, vale em qualquer máquina"""
    return hashlib.md5(json.dumps([p["src"], round(p["ss"], 4), n, fontes.relativo(vf)] + ([] if dec else ["sw"])).encode()).hexdigest()[:14]


def render(p, n):
    """um pedaço de imagem no cache: p = dict(src, ss, lento, z, cx, cy[, interp])"""
    vf = filtro(p)
    if ESC == 2:
        vf += ",format=p010le"
        enc = ["-c:v", "hevc_videotoolbox", "-b:v", "110M", "-tag:v", "hvc1"]
    else:
        vf += ",format=yuv422p10le"
        enc = ["-c:v", "prores_ks", "-profile:v", "2"]
    dec = decodifica(p["src"])
    chave = chave_peca(p, n, vf, dec)
    # o pedaço começa no tempo 0: depois do salto, o primeiro quadro de algumas câmeras cai em 0,03 a 0,3 s e esse
    # deslocamento, somado no concat, fazia os tempos voltarem e o ffmpeg descartar quadros (a imagem descolava do som)
    vf_cmd = vf if p["lento"] else "setpts=PTS-STARTPTS," + vf
    out = os.path.join(TRECHOS, chave + ".mov")
    if os.path.exists(out):
        return out
    os.makedirs(TRECHOS, exist_ok=True)
    fonte_dur = dur(clip(p["src"]))
    precisa = p["ss"] + n / FPS * (0.5 if p["lento"] else 1)
    if precisa > fonte_dur + 0.02:
        print(f"  AVISO: {p['src']} acaba em {fonte_dur:.2f}s e o pedaço pede até {precisa:.2f}s (último quadro congela)")
    sh(["ffmpeg", "-v", "error", "-y", *dec, *fontes.flags(p["src"]), "-ss", f"{p['ss']:.4f}", "-i", clip(p["src"]),
        "-vf", vf_cmd, "-frames:v", str(n), "-an", "-dn", "-map_metadata", "-1", "-write_tmcd", "0", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", *enc,
        out + ".tmp.mov"])
    os.replace(out + ".tmp.mov", out)
    return out


_DUR = {}


def dur(f):
    if f not in _DUR:
        _DUR[f] = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                       capture_output=True, text=True).stdout)
    return _DUR[f]


def pode_lento(src):
    """câmera lenta só no que foi gravado a 60p: 24p a 50% vira 12 quadros por segundo e trava"""
    return fontes.fps(src) > 50


def zooms_fala(g):
    """(z aberto, z fechado) que dão ao rosto ROSTO_AB e ROSTO_FE da altura da tela. A razão entre os dois é sempre a
    mesma (o pulo de plano na emenda tem o mesmo tamanho no vídeo todo); se o teto de 1,5 não deixa chegar, o par desce
    junto. Grupo largo (duas pessoas lado a lado) limita o zoom pra ninguém sair do quadro."""
    x0, x1, _, w, h = g
    razao = ROSTO_FE / ROSTO_AB
    z_fe = min(ROSTO_FE / h, ZMAX, 0.92 / ((x1 - x0) + 3 * w) * razao)
    z_ab = z_fe / razao
    if z_ab < 1.0:
        z_ab, z_fe = 1.0, razao
    return z_ab, z_fe


def quadro_apoio(src, ss, n, lento):
    """enquadramento do B-roll pelos rostos (gente no centro; sem gente fica como está). Drone vai inteiro."""
    if isinstance(src, str) and src.startswith("d"):
        return 1.0, 0.5, 0.5
    z, cx, cy = enquadra.apoio(clip(src), ss, max(n / FPS * (0.5 if lento else 1), 0.4), 1.0)
    # câmera na mão: zoom digital multiplica o tremor (15/11, as mesas a 1,40 "dando zoom, tá péssimo")
    return min(z, 1.10 if isinstance(src, int) else ZMAX), cx, cy


def pinta(V, t0, n, p):
    """põe o pedaço p em [t0, t0+n) por cima do que houver, cortando os vizinhos no tempo certo deles"""
    out = []
    for a, m, q in V:
        b = a + m
        if b <= t0 or a >= t0 + n:
            out.append([a, m, q]); continue
        if a < t0:
            out.append([a, t0 - a, q])
        if b > t0 + n:
            corte = t0 + n - a
            q2 = dict(q, ss=q["ss"] + corte / FPS * (0.5 if q["lento"] else 1))
            out.append([t0 + n, b - (t0 + n), q2])
    out.append([t0, n, p])
    return sorted(out, key=lambda x: x[0])


def em(V, t):
    """pedaço que cobre o quadro t: (início, n, p)"""
    for a, m, q in V:
        if a <= t < a + m:
            return a, m, q
    raise SystemExit(f"buraco na imagem no quadro {t}")


# ======================================================================= letreiros

def fonte(peso, tam):
    return ImageFont.truetype(fontes.tipo(f"Inter-{peso}.otf"), int(round(tam * S)))


def tela():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def texto_track(d, xy, txt, f, track, fill):
    x, y = xy
    for ch in txt:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + track
    return x


def larg_track(d, txt, f, track):
    return sum(d.textlength(ch, font=f) + track for ch in txt) - track


def sombra(camada, raio=10, alfa=150):
    a = camada.split()[3].filter(ImageFilter.GaussianBlur(raio * S))
    s = Image.new("RGBA", camada.size, (0, 0, 0, 0))
    s.putalpha(a.point(lambda v: v * alfa // 255))
    return Image.alpha_composite(s, camada)


def salva(im, nome, folga=0):
    """PNG justo + posição: o overlay só mexe no pedaço"""
    os.makedirs(GRAF, exist_ok=True)
    bb = im.getbbox()
    x0, y0 = max(bb[0] - folga * S, 0), max(bb[1] - folga * S, 0)
    p = os.path.join(GRAF, nome + ".png")
    im.crop((x0, y0, min(bb[2] + folga * S, W), min(bb[3] + folga * S, H))).save(p)
    return p, (x0, y0)


def logo(nome, larg):
    im = Image.open(os.path.join(MARCA, nome)).convert("RGBA")
    larg = int(larg * S)
    return im.resize((larg, round(im.height * larg / im.width)), Image.LANCZOS)


def veu(nome, forma):
    """véu escuro macio onde o texto senta (nunca caixa dura)"""
    x = np.arange(W)[None, :] / W
    y = np.arange(H)[:, None] / H
    if forma == "centro":
        a = np.clip(1 - np.sqrt(((x - 0.5) / 0.55) ** 2 + ((y - 0.5) / 0.45) ** 2), 0, 1) ** 1.2 * 175
    elif forma == "esquerda":
        a = np.clip(1 - x / 0.72, 0, 1) ** 1.5 * 200 + 0 * y
    else:  # canto de baixo à esquerda
        a = np.clip(1 - np.sqrt((x / 0.55) ** 2 + ((1 - y) / 0.37) ** 2), 0, 1) ** 1.2 * 195
    im = np.zeros((H, W, 4), np.uint8)
    im[..., :3] = BG
    im[..., 3] = np.clip(a, 0, 255).astype(np.uint8)
    p = os.path.join(GRAF, f"veu_{forma}.png")
    os.makedirs(GRAF, exist_ok=True)
    if not os.path.exists(p):
        Image.fromarray(im, "RGBA").save(p)
    return p, (0, 0)


def g_titulo(chave, kicker):
    """a virada do gancho: logo Black Experience grande no centro e o kicker embaixo"""
    im = tela()
    lg = logo("logo-black-experience-hd.png", 980)
    y = H // 2 - lg.height // 2 - 34 * S
    im.alpha_composite(lg, ((W - lg.width) // 2, y))
    a = salva(sombra(im, 18, 140), f"{chave}_logo", 30)
    im = tela(); d = ImageDraw.Draw(im)
    f = fonte("SemiBold", 30); tk = 30 * 0.22 * S
    lw = larg_track(d, kicker, f, tk)
    texto_track(d, ((W - lw) / 2, y + lg.height + 44 * S), kicker, f, tk, (205, 212, 255, 255))
    b = salva(sombra(im, 8, 170), f"{chave}_kicker", 16)
    return a, b


def g_nome(chave, nome, papel):
    im = tela(); d = ImageDraw.Draw(im)
    fn, fp = fonte("Bold", 58), fonte("Medium", 31)
    m = 96 * S
    x, y = m + 30 * S, H - m - 118 * S
    texto_track(d, (x, y), nome, fn, -1.4 * S, INK + (255,))
    d.text((x, y + 76 * S), papel, font=fp, fill=(220, 223, 233, 255))
    d.rounded_rectangle([m, y + 10 * S, m + 7 * S, y + 114 * S], radius=3 * S, fill=AZUL + (255,))
    return salva(sombra(im, 14, 210), f"{chave}_nome", 30)


def quebra(d, texto, f, larg, track=0):
    linhas, atual = [], ""
    for p in texto.split():
        teste = (atual + " " + p).strip()
        if larg_track(d, teste, f, track) <= larg or not atual:
            atual = teste
        else:
            linhas.append(atual); atual = p
    return linhas + [atual]


def g_card(chave, numero, rotulo):
    """número dito em tela: material escuro translúcido, filete claro no topo, embaixo à direita (longe dos rostos)"""
    d0 = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tam = 92
    while True:
        fn = fonte("Black", tam)
        if larg_track(d0, numero, fn, -tam * 0.03 * S) <= 560 * S or tam <= 56:
            break
        tam -= 4
    fr = fonte("Medium", 27)
    linhas = quebra(d0, rotulo, fr, 500 * S)
    pad = 38 * S
    larg = int(max(larg_track(d0, numero, fn, -tam * 0.03 * S), max(d0.textlength(l, font=fr) for l in linhas), 300 * S)) + 2 * pad
    alt = int(pad + 30 * S + tam * S + 16 * S + len(linhas) * 37 * S + pad - 6 * S)
    x0, y0 = W - 96 * S - larg, H - 96 * S - alt
    im = tela()
    som = tela()
    ImageDraw.Draw(som).rounded_rectangle([x0, y0 + 14 * S, x0 + larg, y0 + alt + 14 * S], radius=28 * S, fill=(0, 0, 0, 120))
    im = Image.alpha_composite(im, som.filter(ImageFilter.GaussianBlur(24 * S)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([x0, y0, x0 + larg, y0 + alt], radius=28 * S, fill=(13, 15, 21, 216), outline=(255, 255, 255, 30), width=2 * S)
    d.line([x0 + 30 * S, y0 + S, x0 + larg - 30 * S, y0 + S], fill=(255, 255, 255, 64), width=2 * S)
    y = y0 + pad + 4 * S
    d.rounded_rectangle([x0 + pad, y, x0 + pad + 40 * S, y + 5 * S], radius=2 * S, fill=AZUL_HI + (255,))
    y += 26 * S
    texto_track(d, (x0 + pad - 3 * S, y - int(tam * 0.12 * S)), numero, fn, -tam * 0.03 * S, INK + (255,))
    y += int(tam * S) + 16 * S
    for ln in linhas:
        d.text((x0 + pad, y), ln, font=fr, fill=INK2 + (255,)); y += 37 * S
    return salva(im, f"{chave}_card", 40)


def g_hora(chave, hora, legenda):
    """marca de tempo no canto de cima à esquerda: a história anda no relógio do dia"""
    d0 = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    fh, fl = fonte("SemiBold", 28), fonte("SemiBold", 21)
    tl = 21 * 0.14 * S
    lh = larg_track(d0, hora, fh, 1.0 * S)
    ll = larg_track(d0, legenda.upper(), fl, tl) if legenda else 0
    x, y, ph = 96 * S, 80 * S, 58 * S
    larg = int(22 * S + 12 * S + 14 * S + lh + (22 * S + ll if legenda else 0) + 24 * S)
    im = tela()
    som = tela()
    ImageDraw.Draw(som).rounded_rectangle([x, y + 8 * S, x + larg, y + ph + 8 * S], radius=ph // 2, fill=(0, 0, 0, 110))
    im = Image.alpha_composite(im, som.filter(ImageFilter.GaussianBlur(16 * S)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([x, y, x + larg, y + ph], radius=ph // 2, fill=(13, 15, 21, 205), outline=(255, 255, 255, 34), width=2 * S)
    cx = x + 22 * S
    d.ellipse([cx, y + ph // 2 - 6 * S, cx + 12 * S, y + ph // 2 + 6 * S], fill=AZUL_HI + (255,))
    fim = texto_track(d, (cx + 26 * S, y + 13 * S), hora, fh, 1.0 * S, INK + (255,))
    if legenda:
        texto_track(d, (fim + 20 * S, y + 19 * S), legenda.upper(), fl, tl, INK2 + (255,))
    return salva(im, f"{chave}_hora", 30)


def g_capitulo(chave, kicker, titulo):
    """abertura de parte: kicker azul e título grande à esquerda, cada um num PNG (entram escalonados)"""
    d0 = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    fk, ft = fonte("SemiBold", 25), fonte("Bold", 80)
    tt = -80 * 0.025 * S
    linhas = quebra(d0, titulo, ft, 1040 * S, tt)
    lh = int(80 * 1.06 * S)
    alt = 25 * S + 30 * S + len(linhas) * lh
    y, x = (H - alt) // 2 - 10 * S, 128 * S
    im = tela(); d = ImageDraw.Draw(im)
    texto_track(d, (x + 52 * S, y), kicker, fk, 25 * 0.16 * S, AZUL_HI + (255,))
    d.rectangle([x, y + 13 * S, x + 36 * S, y + 16 * S], fill=AZUL_HI + (255,))
    a = salva(sombra(im, 8, 150), f"{chave}_kick", 20)
    im = tela(); d = ImageDraw.Draw(im)
    for k, ln in enumerate(linhas):
        texto_track(d, (x - 4 * S, y + 55 * S + k * lh), ln, ft, tt, INK + (255,))
    b = salva(sombra(im, 14, 160), f"{chave}_tit", 30)
    return a, b


def g_cartela(chave, esq, meio, dir_):
    """a virada de dia, no desenho da referência (G4 Valley): uma linha só no meio da tela, data à esquerda,
    o dia em destaque na cor da marca no centro, o evento à direita. Sem caixa, só sombra."""
    im = tela(); d = ImageDraw.Draw(im)
    fs, fm = fonte("SemiBold", 22), fonte("Bold", 46)
    ts, tm = 22 * 0.24 * S, 46 * 0.06 * S
    y = H // 2 - 23 * S
    lm = larg_track(d, meio, fm, tm)
    texto_track(d, ((W - lm) / 2, y), meio, fm, tm, AZUL_HI + (255,))
    ys = y + 15 * S
    texto_track(d, (W * 0.16, ys), esq, fs, ts, INK + (235,))
    ld = larg_track(d, dir_, fs, ts)
    texto_track(d, (W * 0.84 - ld, ys), dir_, fs, ts, INK + (235,))
    return salva(sombra(im, 10, 170), f"{chave}_cartela", 20)


def g_fim():
    """cartão final: preto da marca, brilho azul-noite atrás da logo Convertfy"""
    x = (np.arange(W)[None, :] - W / 2) / (900 * S)
    y = (np.arange(H)[:, None] - H * 0.47) / (520 * S)
    g = np.clip(1 - np.sqrt(x ** 2 + y ** 2), 0, 1) ** 2
    im = np.zeros((H, W, 3), np.float32)
    for c in range(3):
        im[..., c] = BG[c] + (AZUL_NOITE[c] * 1.35 - BG[c]) * g * 0.9
    ruido = np.random.default_rng(7).normal(0, 1.2, (H, W, 1))
    os.makedirs(GRAF, exist_ok=True)
    fundo = os.path.join(GRAF, "fim_fundo.png")
    Image.fromarray(np.clip(im + ruido, 0, 255).astype(np.uint8), "RGB").save(fundo)
    im = tela()
    lg = logo("logo-convertfy-hd.png", 600)
    im.alpha_composite(lg, ((W - lg.width) // 2, H // 2 - lg.height // 2 - 40 * S))
    a = salva(im, "fim_logo", 10)
    im = tela(); d = ImageDraw.Draw(im)
    f = fonte("SemiBold", 24)
    txt = "BLACK EXPERIENCE  ·  11.11.2026"
    lw = larg_track(d, txt, f, 24 * 0.18 * S)
    texto_track(d, ((W - lw) / 2, H // 2 + 86 * S), txt, f, 24 * 0.18 * S, INK2 + (255,))
    b = salva(im, "fim_sub", 10)
    return fundo, a, b


def render_fundo(png, n):
    chave = hashlib.md5(json.dumps([fontes.relativo(png), n, os.path.getmtime(png), ESC]).encode()).hexdigest()[:14]
    out = os.path.join(TRECHOS, chave + ".mov")
    if not os.path.exists(out):
        os.makedirs(TRECHOS, exist_ok=True)
        if ESC == 2:
            enc = ["-vf", "format=p010le", "-c:v", "hevc_videotoolbox", "-b:v", "40M", "-tag:v", "hvc1"]
        else:
            enc = ["-vf", "format=yuv422p10le", "-c:v", "prores_ks", "-profile:v", "2"]
        sh(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", FPS_S, "-i", png, "-frames:v", str(n), "-dn", "-write_tmcd", "0",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", *enc, out + ".tmp.mov"])
        os.replace(out + ".tmp.mov", out)
    return out


def camada(png_pos, a, b, mov="fade", dist=36, din=0.5, dout=0.25):
    return dict(png=png_pos[0], pos=png_pos[1], a=a, b=b, mov=mov, dist=dist * S, din=din, dout=dout)


# ======================================================================= linha do tempo

class Linha:
    def __init__(self):
        self.V, self.A, self.AMB, self.G, self.FX = [], [], [], [], []
        self.marcas, self.jl, self.t = {}, [], 0
        self.fala_t = []          # (t0, t1) em segundos com voz, pro ducking
        self.fundo = []           # pedaços de cor sólida (cartão final): (t0, n, arquivo)
        self.QR = []              # o L do QR code: dict(a, b, fundo, seq)

    def segundo(self):
        return self.t / FPS


def encaixa(src, x, lado):
    """a ponta escrita no roteiro vai pra borda da palavra do Whisper antes de procurar o silêncio (pedido de 15/11:
    "sem cortar finais e começos de palavras"). Ponta no meio de uma palavra: o fim vai pro fim dela, o começo pro
    começo dela. Ponta colada no começo de uma palavra (até 0,06 s depois) conta como antes dela: o fim vai pro fim da
    palavra anterior. Sem isso, um fim escrito no começo de "faturamento" achava o silêncio do "t" e cortava a palavra."""
    ws = respiros._palavras(src)
    for i, (w0, w1) in enumerate(ws):
        if w0 - 0.04 <= x < w1:
            if x <= w0 + 0.06:
                return (ws[i - 1][1] if i and lado == "fim" else w0) if lado == "fim" else w0
            return w1 if lado == "fim" else w0
    return x


def fim_do_plano(L, t):
    """segundo em que a imagem que está na tela no instante t troca de clipe (troca de zoom no mesmo clipe não conta).
    Letreiro de fala termina aqui: o R$ 25 MIL ficava em cima da entrevista seguinte (15/11, "textos travados")"""
    vs = sorted(L.V, key=lambda v: v[0])
    n = int(round(t * FPS))
    i = next((j for j, v in enumerate(vs) if v[0] <= n < v[0] + v[1]), None)
    if i is None:
        return None
    src, fim = vs[i][2]["src"], vs[i][0] + vs[i][1]
    for v in vs[i + 1:]:
        if v[0] > fim + 1 or v[2]["src"] != src:
            break
        fim = v[0] + v[1]
    return fim / FPS


def bloco_fala(L, b, k):
    src = b["fonte"]
    pontas = [b["ini"]] + [x for a, c in b.get("tira", []) for x in (a, c)] + [b["fim"]]
    # par = começo de trecho que fica, ímpar = fim: cada um procura o silêncio do lado certo da palavra
    fixos = b.get("fixos", [])        # emenda escolhida no ouvido: não procura vão
    pontas = [x if x in fixos else respiros.vale(src, encaixa(src, x, "ini" if i % 2 == 0 else "fim"),
                                                  "ini" if i % 2 == 0 else "fim") for i, x in enumerate(pontas)]
    trechos = list(zip(pontas[0::2], pontas[1::2]))
    partes = []
    for a, c in trechos:
        partes += respiros.pedacos_vad(src, a, c) if b.get("respira", True) else [(a, c)]
    dets = enquadra.detecta(clip(src), b["ini"], b["fim"] - b["ini"], amostra=2)
    g = enquadra.grupo(dets)
    z_ab, z_fe = zooms_fala(g) if g else (1.0, ROSTO_FE / ROSTO_AB)
    if "z" in b:
        z_ab, z_fe = b["z"], min(b["z"] * ROSTO_FE / ROSTO_AB, ZMAX)
    ancora = {z: enquadra.centro(g, z, OLHOS) for z in (z_ab, z_fe)} if g else {}
    t_ini = L.t
    mapa = []
    for i, (s0, s1) in enumerate(partes):
        n = nq(s1 - s0)
        z = z_fe if i % 2 else z_ab
        gi = enquadra.grupo(dets, s0, s1) or g
        cx, cy = enquadra.centro(gi, z, OLHOS) if gi else (0.5, 0.5)
        if ancora and abs(cx - ancora[z][0]) < ANCORA and abs(cy - ancora[z][1]) < ANCORA:
            cx, cy = ancora[z]            # parado no lugar: fica na âncora do bloco, sem sambar de pedaço em pedaço
        if "quadro" in b:
            z, cx, cy = b["quadro"][i % 2] if isinstance(b["quadro"], list) else b["quadro"]
        L.V.append([L.t, n, dict(src=src, ss=s0, lento=False, z=z, cx=cx, cy=cy)])
        L.A.append((src, s0, n / FPS, L.t / FPS, b.get("ganho", 0)))
        L.fala_t.append((L.t / FPS, (L.t + n) / FPS))
        mapa.append((s0, s1, L.t))
        L.t += n

    def no_video(ts):
        for s0, s1, t0 in mapa:
            if ts < s1:
                return t0 + nq(max(ts - s0, 0))
        s0, s1, t0 = mapa[-1]
        return t0 + nq(s1 - s0)

    coberturas = []
    for cob in b.get("cobertura", []):
        if isinstance(cob[2], list):     # (a, b, [(clipe, ss), ...]): vários planos curtos dividindo o trecho
            a, c, planos = cob[:3]
            passo = (c - a) / len(planos)
            coberturas += [(a + i * passo, a + (i + 1) * passo) + tuple(pl) for i, pl in enumerate(planos)]
        else:
            coberturas.append(cob)
    for cob in coberturas:
        a, c, csrc, css = cob[:4]
        a, c = respiros.vale(src, a, r=0.25), respiros.vale(src, c, r=0.25)   # a imagem troca no respiro da fala
        lento = (cob[4] if len(cob) > 4 else True) and pode_lento(csrc)
        t0, t1 = no_video(a), no_video(c)
        z, cx, cy = quadro_apoio(csrc, css, t1 - t0, lento)
        L.V = pinta(L.V, t0, t1 - t0, dict(src=csrc, ss=css, lento=lento, z=z, cx=cx, cy=cy))
    if b.get("nome"):
        nm, papel = b["nome"]
        # com J a cara só aparece depois do plano de antes: o nome entra com ela
        tn = t_ini / FPS + max(b.get("nome_em", 0.4), b.get("j", 0) + 0.3)
        # tempo de leitura (16/11: "o nome do Bruno mostra muito rápido, não dá pra ler"): 2,2 s mais 0,3 s por palavra,
        # de 4 a 6 s. O nome é de quem está na tela: sai antes da primeira imagem de apoio
        leitura = min(max(2.2 + 0.3 * len(f"{nm} {papel}".split()), 4.0), 6.0)
        cobs = [no_video(c[0]) / FPS for c in coberturas]
        tf = min([tn + leitura] + [c - 0.05 for c in cobs if c > tn + 2.2] + [(fim_do_plano(L, tn) or tn + 9) - 0.05])
        if tf - tn < 3.5:
            print(f"  AVISO: o nome {nm} fica só {tf - tn:.1f}s na tela (apoio ou corte logo depois)")
        seq, nq_, pos = cards.nome(os.path.join(GRAF, "nomes"), f"n{k}", nm, papel, b.get("nome_lado", "dir"),
                                   round(tf - tn, 2), W, H, S, FPS)
        L.G.append(dict(seq=seq, png=seq, pos=pos, a=tn, b=tn + nq_ / FPS, mov="fixo", dist=0, din=0, dout=0))
    if b.get("destaque"):
        põe_destaque(L, b, k, src, t_ini)
    for i, (tg, termo, texto) in enumerate(b.get("glossario", [])):
        t0 = no_video(tg) / FPS
        # tempo de leitura (15/11: "você tira muito rápido, não dá pra ler"): 2 s pra achar o cartão e 0,3 s por
        # palavra, de 5 a 9 s. O glossário é uma janela à parte e pode passar do corte de cena; a leitura vem antes
        dur_g = round(min(max(2.0 + 0.30 * len((termo + " " + texto).split()), 5.0), 9.0), 2)
        seq, nq_, pos = cards.glossario(os.path.join(GRAF, "glossario"), f"g{k}_{i}", termo, texto, dur_g, W, H, S, FPS)
        L.G.append(dict(seq=seq, png=seq, pos=pos, a=t0, b=t0 + nq_ / FPS, mov="fixo", dist=0, din=0, dout=0))
        L.FX.append((t0 + 0.05, "pop-2.mp3", -24))
    if b.get("qr"):
        q = b["qr"]
        põe_qr(L, no_video(q["em"]) / FPS, q)
    for i, ins in enumerate(b.get("insights", [])):
        # insight no meio da tela: entra um pouco antes da palavra, o número conta até o valor quando ela é dita
        t0 = no_video(ins["t"]) / FPS - 0.15
        fp = fim_do_plano(L, t0 + 0.15)
        dur = round(max(min(ins.get("dur", 2.8), (fp or t0 + 9) - t0 - 0.05), 2.0), 2)
        padrao, nq_, pos = insight.gera(os.path.join(GRAF, "insights"), f"i{k}_{i}", ins, dur, W, H, S, FPS, MARCA)
        L.G.append(dict(seq=padrao, png=padrao, pos=pos, a=t0, b=t0 + nq_ / FPS, mov="fixo", dist=0, din=0, dout=0))
    for i, (a, c, num, rot) in enumerate(b.get("cards", [])):
        ta, tc = no_video(a) / FPS, no_video(c) / FPS
        L.G.append(camada(g_card(f"c{k}_{i}", num, rot), ta, tc, "dir", dist=44))
        L.FX.append((ta, "pop-1.mp3", -17))
    return t_ini


def põe_destaque(L, b, k, src, t_ini):
    """o nome de quem está sendo falado, com a seta até ele (cards.seta). A pessoa é seguida pelo rosto: achado na fonte
    a 10 por segundo, levado pro recorte de cada pedaço, escolhido pelo mais perto da posição anterior (começa no
    "alvo" do roteiro, em fração da tela) e suavizado em 0,4 s"""
    d_ = b["destaque"]
    t0 = t_ini / FPS + d_.get("em", 0.3)
    n = min(nq(d_["dur"]), L.t - nq(t0) - 2)      # a seta só vale no enquadramento deste bloco
    fw, fh = fontes.dims(src)
    pecas = [v for v in L.V if v[0] >= t_ini and v[2].get("src") == src]
    amostras = []
    for ts, rostos, _ in enquadra.detecta(clip(src), b["ini"], b["fim"] - b["ini"], amostra=10):
        for a, m, q in pecas:
            if q["ss"] <= ts < q["ss"] + m / FPS:
                z = q["z"]
                if z > 1.001:
                    cw, ch = int(round(fw / z / 2)) * 2, int(round(fh / z / 2)) * 2
                    x = int(min(max(q["cx"] * fw - cw / 2, 0), fw - cw)) // 2 * 2
                    y = int(min(max(q["cy"] * fh - ch / 2, 0), fh - ch)) // 2 * 2
                else:
                    cw, ch, x, y = fw, fh, 0, 0
                tv = (a + (ts - q["ss"]) * FPS) / FPS
                amostras.append((tv, [((r[0] * fw - x) / cw, (r[1] * fh - y) / ch, r[3] * fh / ch) for r in rostos
                                      if r[3] >= 0.04]))
                break
    amostras.sort()
    ax, ay = d_["alvo"]
    trilha = []
    for tv, rs in amostras:
        if rs:
            r = min(rs, key=lambda r: (r[0] - ax) ** 2 + (r[1] - ay) ** 2)
            if (r[0] - ax) ** 2 + (r[1] - ay) ** 2 < 0.22 ** 2:
                ax, ay = r[0], r[1]
                trilha.append((tv, r[0], r[1], r[2]))
    if len(trilha) < 3:
        raise SystemExit(f"destaque {d_['nome']}: rosto não encontrado perto de {d_['alvo']}")
    tr = np.array(trilha)
    ts_q = t0 + np.arange(n) / FPS
    jan = max(int(0.4 * FPS), 1)
    suave = lambda v: np.convolve(np.pad(v, jan // 2, mode="edge"), np.ones(jan) / jan, mode="valid")[:n]
    xs, ys, hs = (suave(np.interp(ts_q, tr[:, 0], tr[:, c])) for c in (1, 2, 3))
    alvos = [(float(x_ * W), float(y_ * H), float(h_ * H)) for x_, y_, h_ in zip(xs, ys, hs)]
    seq, nq_, pos = cards.seta(os.path.join(GRAF, "destaque"), f"d{k}", d_["nome"], d_["papel"], d_["texto"], alvos,
                               round(n / FPS, 2), W, H, S, FPS)
    L.G.append(dict(seq=seq, png=seq, pos=pos, a=t0, b=t0 + nq_ / FPS, mov="fixo", dist=0, din=0, dout=0))
    L.FX.append((t0 + 0.42, "swish-2.mp3", -24))


def põe_qr(L, a, q):
    """o L do QR vira um pedaço próprio na composição (render_qr); aqui fica a janela e o som da entrada"""
    L.QR.append(dict(a=a, b=a + q.get("dur", 9.0), q=q))
    L.FX.append((a, "whoosh-2.mp3", -22))


def bloco_broll(L, b, k):
    t_ini = L.t
    cum = 0.0
    bat = 60 / b["bpm"] if "bpm" in b else None
    for tom in b["tomadas"]:
        src, ss, d = tom[:3]
        op = tom[3] if len(tom) > 3 else {}
        lento = op.get("lento", b.get("lento", True)) and pode_lento(src)
        if bat:
            n = nq((cum + d) * bat) - nq(cum * bat)
        else:
            n = nq(cum + d) - nq(cum)
        cum += d
        interp = not lento and fontes.fps(src) < 29
        # o take não passa do fim do arquivo: o que falta virava o último quadro repetido (16/11, o 1408 e o 1410 do
        # kart com 3 quadros parados no fim). O minterpolate ainda precisa de uns quadros à frente
        sobra = fontes._probe(src)["dur"] - (0.15 if interp else 0.05)
        if ss + n / FPS * (0.5 if lento else 1) > sobra:
            ss = max(sobra - n / FPS * (0.5 if lento else 1), 0.0)
        if "quadro" in op:
            z, cx, cy = op["quadro"]
        else:
            z, cx, cy = quadro_apoio(src, ss, n, lento)
        L.V.append([L.t, n, dict(src=src, ss=ss, lento=lento, z=z, cx=cx, cy=cy, interp=interp)])
        if not lento and op.get("som") is not None:
            L.AMB.append((src, ss, n / FPS, L.t / FPS, op["som"]))
        L.t += n
    for src, a, c, desloc in b.get("vo", []):
        t0 = t_ini / FPS + desloc
        L.A.append((src, a, c - a, t0, 0))
        L.fala_t.append((t0, t0 + c - a))
    if b.get("qr"):
        põe_qr(L, t_ini / FPS + b["qr"].get("em", 0.0), b["qr"])
    return t_ini


def monta_linha(ROTEIRO):
    L = Linha()
    for k, b in enumerate(ROTEIRO):
        if b.get("marca"):
            L.marcas[b["marca"]] = L.segundo()
        if b["tipo"] == "fala":
            t0 = bloco_fala(L, b, k)
        elif b["tipo"] == "broll":
            t0 = bloco_broll(L, b, k)
        elif b["tipo"] == "fim":
            t0 = L.t
            n = nq(b["dur"])
            fundo, la, lb = g_fim()
            L.fundo.append((L.t, n, fundo))
            ts = L.t / FPS
            L.G.append(camada(la, ts + 0.15, ts + b["dur"], "sobe", dist=24, din=0.7, dout=0.01))
            L.G.append(camada(lb, ts + 0.25, ts + b["dur"], "sobe", dist=18, din=0.7, dout=0.01))
            L.t += n
            L.marcas["fim"] = L.segundo()
            continue
        ts = t0 / FPS
        if b.get("titulo"):
            a_, c_ = ts + b["titulo"].get("em", 0.0), ts + b["titulo"].get("em", 0.0) + b["titulo"]["dur"]
            la, lb = g_titulo(f"t{k}", b["titulo"]["kicker"])
            L.G.append(camada(veu("centro", "centro"), a_, c_, din=0.4, dout=0.35))
            L.G.append(camada(la, a_ + 0.05, c_, "sobe", dist=28, din=0.8, dout=0.3))
            L.G.append(camada(lb, a_ + 0.15, c_, "sobe", dist=18, din=0.8, dout=0.3))
        if b.get("cartela"):
            c_ = b["cartela"]
            a_, z_ = ts + c_.get("em", 0.4), ts + c_.get("em", 0.4) + c_.get("dur", 3.4)
            L.G.append(camada(veu("centro", "centro"), a_ - 0.1, z_ + 0.1, din=0.5, dout=0.5))
            L.G.append(camada(g_cartela(f"ct{k}", *c_["texto"]), a_, z_, "fade", din=0.6, dout=0.5))
            L.FX.append((a_, "tique-1.mp3", -26))
        if b.get("capitulo"):
            kick, tit, d = b["capitulo"]
            la, lb = g_capitulo(f"cap{k}", kick, tit)
            L.G.append(camada(veu("esquerda", "esquerda"), ts, ts + d, din=0.4, dout=0.3))
            L.G.append(camada(la, ts + 0.1, ts + d, "esq", dist=30, din=0.6))
            L.G.append(camada(lb, ts + 0.18, ts + d, "esq", dist=40, din=0.6))
            L.FX.append((ts + 0.05, "whoosh-1.mp3", -20))
        if b.get("hora"):
            h, leg = b["hora"]
            L.G.append(camada(g_hora(f"h{k}", h, leg), ts + 0.3, ts + 4.0, "esq", dist=20))
            L.FX.append((ts + 0.3, "tique-1.mp3", -24))
        for fx in b.get("fx", []):
            L.FX.append((ts + fx[0], fx[1], fx[2]))
        if b.get("j"):
            L.jl.append(("j", t0, nq(b["j"])))
        if b.get("l"):
            L.jl.append(("l", t0, nq(b["l"])))
    # J e L por último, por cima de tudo (inclusive do B-roll de cobertura)
    for tipo, T, n in L.jl:
        if tipo == "j":       # o plano de antes continua por cima do começo da fala nova (a voz chega antes da cara)
            a, m, q = em(L.V, T - 1)
            q2 = dict(q, ss=q["ss"] + (T - a) / FPS * (0.5 if q["lento"] else 1))
            if "src" in q2 and q2["ss"] + n / FPS * (0.5 if q2["lento"] else 1) > fontes._probe(q2["src"])["dur"] - 0.15:
                raise SystemExit(f"J no quadro {T}: o clipe {q2['src']} acaba antes de {n / FPS:.2f}s a mais (congelaria)")
            L.V = pinta(L.V, T, n, q2)
        else:                 # a imagem nova chega antes, com a fala de antes terminando por cima
            a, m, q = em(L.V, T)
            q2 = dict(q, ss=q["ss"] - (n + T - a) / FPS * (0.5 if q["lento"] else 1))
            if q2["ss"] < 0:
                raise SystemExit(f"L no quadro {T}: o clipe {q['src']} não tem {n / FPS:.2f}s antes")
            L.V = pinta(L.V, T - n, n, q2)
    for t0, n, png in L.fundo:
        L.V = pinta(L.V, t0, n, dict(fundo=png))
    # o L do QR começa e termina na borda de um pedaço (vira um pedaço só na composição); o whoosh vai junto
    for qr_ in L.QR:
        na, nb = nq(qr_["a"]), nq(qr_["b"])
        i0 = min(range(len(L.V)), key=lambda i: abs(L.V[i][0] - na))
        s0 = L.V[i0][0]
        alvo = s0 + nb - na
        # a primeira ponta que dá o tempo pedido (QR com menos de 9 s não dá tempo de escanear); só cai na mais perto
        # se a primeira passar 4 s do pedido
        cabe = [i for i in range(i0, len(L.V)) if L.V[i][0] + L.V[i][1] >= alvo - int(0.4 * FPS)]
        i1 = cabe[0] if cabe and L.V[cabe[0]][0] + L.V[cabe[0]][1] - alvo <= 4 * FPS else \
            min(range(i0, len(L.V)), key=lambda i: abs(L.V[i][0] + L.V[i][1] - alvo))
        a_ant = qr_["a"]
        qr_["a"], qr_["b"] = s0 / FPS, (L.V[i1][0] + L.V[i1][1]) / FPS
        L.FX = [(qr_["a"], f, d) if f == "whoosh-2.mp3" and abs(t - a_ant) < 1e-6 else (t, f, d) for t, f, d in L.FX]
    return L


# ======================================================================= som

def le_audio(f, ini, d):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(ini, 0):.4f}", "-i", f, "-t", f"{d:.4f}", "-map", "0:a:0",
                          "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
    n = int(round(d * SR))
    if ini < 0:
        a = np.vstack([np.zeros((int(round(-ini * SR)), 2), np.float32), a])
    return a[:n] if len(a) >= n else np.vstack([a, np.zeros((n - len(a), 2), np.float32)])


def filtra(a, filtro):
    p = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", filtro,
                        "-f", "f32le", "-"], input=a.astype(np.float32).tobytes(), capture_output=True, check=True)
    b = np.frombuffer(p.stdout, np.float32).reshape(-1, 2).copy()
    return b[:len(a)] if len(b) >= len(a) else np.vstack([b, np.zeros((len(a) - len(b), 2), np.float32)])


def db(x):
    return 20 * np.log10(max(x, 1e-9))


VOZ = ("pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,"   # os dois canais são o mesmo microfone
       "highpass=f=80,afftdn=nf=-40,acompressor=threshold=-32dB:ratio=3:attack=4:release=70")


def cama_cinema(c, d, de, T):
    """a intro de cinema (skill trilha-cinematografica): drone no tom desde o começo, golpe tonal nas falas fortes,
    a voz do cantor com reverb de sala nos últimos segundos, dois risers com pico exato no drop. Tudo corta seco no drop.
    c = dict(drone=[notas], golpes=[(t, nota)], voz=(arq, a, b), drop=marca)"""
    n = int(d * SR)
    x = np.zeros((n, 2))
    dr = som_cinema.drone(c["drone"], d, abre=c.get("abre", 4.0))
    drop = int((T(c["drop"]) - de) * SR)
    voz_ini = None
    if c.get("voz"):
        arq, a, b = c["voz"]
        voz_ini = drop - int(0.25 * SR) - int((b - a) * SR)
        env = np.ones(n)                    # o drone abaixa 7 dB enquanto o cantor canta (a voz é a prioridade)
        r = int(0.6 * SR)
        if voz_ini > r:
            env[voz_ini - r:voz_ini] = np.linspace(1, 0.45, r); env[voz_ini:] = 0.45
        dr = dr * env
    x += som_cinema.st(dr) * 0.30
    for t, nota in c.get("golpes", []):
        g = som_cinema.reverb(som_cinema.golpe(nota, 2.4), 0.35) * 0.55
        i = int((T(t) - de) * SR)
        if 0 <= i < n:
            x[i:i + len(g)] += g[: n - i]
    if c.get("voz"):
        v = sf.read(arq, always_2d=True)[0]
        sr_v = sf.info(arq).samplerate
        v = v[int(a * sr_v):int(b * sr_v)]
        if sr_v != SR:
            from scipy.signal import resample_poly
            v = resample_poly(v, SR, sr_v, axis=0)
        v = som_cinema.reverb(v.mean(1), mix=0.407)
        v *= 0.9 / (np.abs(v).max() or 1)
        i = drop - int(0.25 * SR) - len(v)
        if i >= 0:
            x[i:i + len(v)] += v[: n - i]
    for dur_r, g_r in ((5.1, 0.11), (3.7, 0.09)):     # risers bem abaixo da voz: só sobem no último segundo
        r = som_cinema.riser(dur_r) * g_r
        i = drop - len(r)
        if i >= 0:
            x[i:drop] += som_cinema.st(r / (np.abs(r).max() or 1) * g_r)
    # 15/11: "na hora que aparece o Black Experience a música entra normal e a transição não ficou legal". O cinema
    # não some no drop: o eco da voz e o drone seguem e apagam em ~2,5 s por baixo da batida, e um golpe na tônica
    # marca a logo (o grave de impacto é o gen:boom do bloco do drop)
    if drop < n:
        x[drop:] *= (np.exp(-np.arange(n - drop) / (0.9 * SR)) * 0.8)[:, None]
        g = som_cinema.reverb(som_cinema.golpe(c.get("impacto", c["drone"][0]), 3.0), 0.35) * 0.7
        x[drop:drop + len(g)] += g[: n - drop]
    return x.astype(np.float32)


_GERADO = os.path.join(CACHE, "sfx_gerado")


def gerado(nome):
    """efeito sintetizado em som_cinema, salvo uma vez: gen:whoosh, gen:boom, gen:riser-2.6"""
    os.makedirs(_GERADO, exist_ok=True)
    p = os.path.join(_GERADO, nome[4:] + ".wav")
    if not os.path.exists(p):
        tipo, *arg = nome[4:].split("-")
        if tipo == "whoosh":
            x = som_cinema.whoosh(0.5)
        elif tipo == "boom":
            x = som_cinema.st(som_cinema.sub_boom(1.6) * 0.9 + som_cinema.hp(som_cinema.ruido_rosa(int(1.6 * SR)), 2000)
                              * som_cinema.env_exp(int(1.6 * SR), 0.05) * 0.2)
        elif tipo == "riser":
            x = som_cinema.st(som_cinema.riser(float(arg[0]) if arg else 2.6))
        else:
            raise SystemExit(f"efeito gerado desconhecido: {nome}")
        sf.write(p, (x / (np.abs(x).max() or 1) * 0.9).astype(np.float32), SR)
    return p


def nivel_fala(x, src):
    """volume da fala do clipe: média de potência dos quadros de fala (Silero), sem os 30% mais baixos"""
    m = respiros.fala_vad(src)
    q = int(respiros.VAD_FR * SR)
    k = min(len(m), len(x) // q)
    e = (x[:k * q, 0].reshape(k, q) ** 2).mean(1)[m[:k]]
    if len(e) < 10:
        return db(np.sqrt((x[:, 0] ** 2).mean()))
    e = e[e >= np.percentile(e, 30)]
    return db(np.sqrt(e.mean()))


def monta_som(L, total, TRILHAS):
    n = int(round(total * SR))
    voz = np.zeros((n, 2), np.float32)
    mask = np.zeros(n, bool)
    cache_clip, nivel_clip = {}, {}
    for src, ini, d, t0, ganho in L.A:
        if src not in cache_clip:   # filtra o clipe inteiro uma vez (o afftdn precisa de contexto)
            bruto = le_audio(clip(src), 0, dur(clip(src)))
            # grito estourado (o Osmo no Mini Cooper satura 1% das amostras): reconstrói o pico antes de tudo
            cache_clip[src] = filtra(bruto, ("adeclip," if np.mean(np.abs(bruto) > 0.98) > 0.0005 else "") + VOZ)
            nivel_clip[src] = nivel_fala(cache_clip[src], src)
    # toda fala no mesmo volume, como o enquadramento. Medido por TRECHO de ~8 s da mesma fala (15/11: "os áudios
    # ficaram ruins"): no mesmo clipe a pessoa chega perto e se afasta do microfone, e o nível do clipe inteiro não vê
    # isso. Trecho vizinho da mesma fala muda no máximo 3 dB, pra emenda de respiração não pular de volume.
    def energias(src, ini, d):
        x = cache_clip[src][int(round(ini * SR)):int(round((ini + d) * SR)), 0]
        m = respiros.fala_vad(src)[int(ini / respiros.VAD_FR):int((ini + d) / respiros.VAD_FR)]
        q = int(respiros.VAD_FR * SR)
        k = min(len(m), len(x) // q)
        return (x[:k * q].reshape(k, q) ** 2).mean(1)[m[:k]] if k else np.array([])
    ordem = sorted(range(len(L.A)), key=lambda i: L.A[i][3])
    janelas, atual, fim_ant, src_ant = [], [], -9, None
    for i in ordem:
        src, ini, d, t0, _ = L.A[i]
        if atual and (src != src_ant or t0 - fim_ant > 0.4 or sum(L.A[j][2] for j in atual) >= 8):
            janelas.append((atual, src_ant == src and t0 - fim_ant <= 0.4)); atual = []
        atual.append(i); fim_ant, src_ant = t0 + d, src
    if atual:
        janelas.append((atual, False))
    nivel_j = []
    for js, _ in janelas:
        e = np.concatenate([energias(*L.A[j][:3]) for j in js])
        if len(e) < 12:
            nivel_j.append(nivel_clip[L.A[js[0]][0]]); continue
        e = e[e >= np.percentile(e, 30)]
        nivel_j.append(db(np.sqrt(e.mean())))
    alvo_voz = float(np.median(nivel_j)) if nivel_j else 0
    g_peca, g_ant, segue = {}, None, False
    for (js, continua), nv in zip(janelas, nivel_j):
        g = float(np.clip(alvo_voz - nv, -9, 9))
        if segue and g_ant is not None:
            g = float(np.clip(g, g_ant - 3, g_ant + 3))
        for j in js:
            g_peca[j] = g
        g_ant, segue = g, continua
    for k_, (src, ini, d, t0, ganho) in enumerate(L.A):
        x = cache_clip[src]
        g_n = g_peca[k_]
        i0s = int(round(ini * SR)); a = x[i0s:i0s + int(round(d * SR))].copy() * 10 ** ((ganho + g_n) / 20)
        f = min(int(0.012 * SR), len(a) // 2); r = np.linspace(0, 1, f)[:, None]
        a[:f] *= r; a[-f:] *= r[::-1]
        i0 = int(round(t0 * SR)); i1 = min(n, i0 + len(a))
        voz[i0:i1] += a[: i1 - i0]
    for t0, t1 in L.fala_t:
        mask[int(t0 * SR):int(t1 * SR)] = True
    jan = int(0.05 * SR)
    m = n // jan * jan
    rms = np.sqrt((voz[:m, 0].reshape(-1, jan) ** 2).mean(1))
    mj = mask[:m:jan]
    ativos = rms[mj & (rms > np.percentile(rms[mj], 95) * 10 ** (-12 / 20))]
    fala_db = db(np.sqrt((ativos ** 2).mean()))

    amb = np.zeros((n, 2), np.float32)
    for src, ini, d, t0, rel in L.AMB:
        a = filtra(le_audio(clip(src), ini, d), "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,highpass=f=100")
        a *= 10 ** ((fala_db + rel - db(np.sqrt((a ** 2).mean()))) / 20)
        f = int(0.08 * SR); r = np.linspace(0, 1, f)[:, None]
        a[:f] *= r; a[-f:] *= r[::-1]
        i0 = int(round(t0 * SR)); i1 = min(n, i0 + len(a))
        amb[i0:i1] += a[: i1 - i0]

    tri = np.zeros((n, 2), np.float32)
    passo = int(0.01 * SR)

    def T(x):
        """tempo no vídeo: número, nome de marca ou (marca, deslocamento)"""
        if isinstance(x, (tuple, list)):
            return L.marcas[x[0]] + x[1]
        return L.marcas[x] if isinstance(x, str) else x

    for tr in TRILHAS:
        de, ate = T(tr["de"]), min(T(tr["ate"]) + tr.get("passa", 0), total)
        d = ate - de
        if tr.get("cinema"):
            x = cama_cinema(tr["cinema"], d, de, T)
            src0 = 0
        else:
            src0 = tr["src"] - (T(tr["alinha"]) - de) if "alinha" in tr else tr["src"]
            x = le_audio(tr["arq"], src0, d)
        x_db = db(np.sqrt((x[x.any(1)] ** 2).mean())) if x.any() else -90
        i0 = int(round(de * SR)); k = len(x)
        mk = mask[i0:i0 + k]
        livre, sob = tr.get("livre", -5), tr.get("sob", 13)   # dB contra a fala: sem voz / com voz por cima
        alvo = np.where(mk, fala_db - sob, fala_db + livre) - x_db
        for item in tr.get("nivel", []):     # trechos com nível próprio: (de, até, livre[, sob]). O sob próprio é pro
            a_, b_, g_ = item[:3]               # momento em que a música manda (a reação dela no Mini Cooper, 15/11:
            s_ = item[3] if len(item) > 3 else sob   # "tá muito baixa"): o grito também conta como fala
            j0, j1 = max(int(T(a_) * SR) - i0, 0), max(int(T(b_) * SR) - i0, 0)
            alvo[j0:j1] = np.where(mk[j0:j1], fala_db - s_, fala_db + g_) - x_db
        al = alvo[::passo]; g = np.empty_like(al); g[0] = al[0]
        for i in range(1, len(al)):
            kk = 0.01 / 0.08 if al[i] < g[i - 1] else 0.01 / 0.35
            g[i] = g[i - 1] + (al[i] - g[i - 1]) * min(1, kk)
        ganho = 10 ** (np.interp(np.arange(k), np.arange(len(g)) * passo, g) / 20)
        for a_, b_ in tr.get("silencio", []):                 # a música some (a porta abrindo, o "parou tudo")
            j0, j1 = int(T(a_) * SR) - i0, int(T(b_) * SR) - i0
            r = int(0.15 * SR)
            env = np.ones(k)
            env[max(j0, 0):max(j1, 0)] = 0
            if 0 < j0 < k:
                env[max(j0 - r, 0):j0] = np.minimum(env[max(j0 - r, 0):j0], np.linspace(1, 0, j0 - max(j0 - r, 0)))
            if 0 <= j1 < k:
                env[j1:j1 + r] = np.minimum(env[j1:j1 + r], np.linspace(0, 1, len(env[j1:j1 + r])))
            ganho *= env
        fi, fo = int(tr.get("fade_in", 0.05) * SR), int(tr.get("fade_out", 1.4) * SR)
        ganho[:fi] *= np.linspace(0, 1, fi)
        y = x * ganho[:, None]
        if tr.get("abafa"):                                    # entra abafada e abre até o tempo forte
            f0, dd = tr["abafa"]
            m_ = min(int(dd * SR), k)
            y[:m_] = som_cinema.abre(y[:m_], f0, 16000)
        if tr.get("fim") == "tape":                            # sai freando como fita, no corte cômico
            m_ = int(0.6 * SR)
            if k > m_ * 2:
                y[k - m_:] = som_cinema.tape_stop(y[k - m_:], 0.6)
        else:
            y[-fo:] *= np.linspace(1, 0, fo)[:, None]
        tri[i0:i0 + k] += y

    fx = np.zeros((n, 2), np.float32)
    for t, nome, rel in L.FX:
        f = nome if nome.startswith("/") else gerado(nome) if nome.startswith("gen:") else os.path.join(SFX, nome)
        e = le_audio(f, 0, dur(f))
        e *= 10 ** ((fala_db + rel - db(np.sqrt((e ** 2).mean()))) / 20)
        i0 = int(round(t * SR)); i1 = min(n, i0 + len(e))
        if 0 <= i0 < n:
            fx[i0:i1] += e[: i1 - i0]

    mix = voz + amb + tri + fx
    r_t = np.sqrt((tri[:m, 0].reshape(-1, jan) ** 2).mean(1))
    fj = mj & (rms > np.percentile(rms[mj], 95) * 10 ** (-12 / 20))
    abaixo = fala_db - db(np.sqrt((r_t[fj] ** 2).mean()))
    med = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af",
                          "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                         input=mix.astype(np.float32).tobytes(), capture_output=True).stderr.decode()
    j = json.loads(med[med.rindex("{"): med.rindex("}") + 1])
    final = filtra(mix, f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
                        f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:"
                        f"linear=true,aresample={SR}")
    if os.environ.get("STEMS"):
        for nome, x in (("voz", voz), ("trilha", tri), ("fx", fx), ("amb", amb)):
            sf.write(os.path.join(CACHE, f"stem_{nome}.wav"), x, SR, subtype="FLOAT")
    return final, abaixo


# ======================================================================= composição

def _entra(a, d):
    return f"pow(1-clip((t-{a:.3f})/{d},0,1),4)"


def _sai(b, d):
    return f"pow(clip((t-{b - d:.3f})/{d},0,1),2)"


def render_qr(arqs, n, q, chave):
    """o L do QR como um pedaço só: o trecho do vídeo encolhe pro canto (0,6 s, curva suave) por cima do fundo do L e
    as peças entram por cima. Três entradas, todas começando no 0 (o QR dentro do filtro grande travava o ffmpeg)."""
    dur = n / FPS
    seq, _, _ = cards.qr(os.path.join(GRAF, "qr"), chave, round(dur, 3), W, H, S, FPS, MARCA, q["chamada"], q["cta"],
                         sub=q.get("sub"), foto=q.get("foto", "bruno-autoridade.png"))
    fundo = cards.qr_painel(GRAF, W, H, S, MARCA)
    sig = hashlib.md5(fontes.relativo(json.dumps([arqs, n, seq, fundo, ESC])).encode()).hexdigest()[:14]
    out = os.path.join(TRECHOS, f"qr_{sig}.mov")
    if os.path.exists(out):
        return out
    lista = out + ".txt"
    open(lista, "w").write("".join(f"file '{c}'\nduration {m / FPS:.6f}\n" for c, m in arqs))
    e = f"min(clip(t/0.6,0,1),clip(({dur:.3f}-t)/0.6,0,1))"
    sc = f"(1-{1 - cards.QR_SC:.3f}*({e})*({e})*(3-2*({e})))"
    fc = (f"[0:v]setpts=PTS-STARTPTS,scale=w='trunc({W}*{sc}/2)*2':h='trunc({H}*{sc}/2)*2':eval=frame:flags=bicubic[qs];"
          f"[1:v]format=yuv420p,setpts=PTS-STARTPTS[qf];[qf][qs]overlay=0:0:eof_action=pass[ql];"
          f"[2:v]format=rgba,setpts=PTS-STARTPTS[qp];[ql][qp]overlay=0:0:eof_action=pass")
    if ESC == 2:
        enc = ["-vf", "format=p010le", "-c:v", "hevc_videotoolbox", "-b:v", "110M", "-tag:v", "hvc1"]
        fc += ",format=p010le[v]"
        enc = ["-c:v", "hevc_videotoolbox", "-b:v", "110M", "-tag:v", "hvc1"]
    else:
        fc += ",format=yuv422p10le[v]"
        enc = ["-c:v", "prores_ks", "-profile:v", "2"]
    sh(["ffmpeg", "-v", "error", "-y", "-reinit_filter", "0", "-f", "concat", "-safe", "0", "-i", lista,
        "-loop", "1", "-framerate", FPS_S, "-t", f"{dur + 0.3:.3f}", "-i", fundo,
        "-framerate", FPS_S, "-start_number", "0", "-i", seq,
        "-filter_complex", fc, "-map", "[v]", "-frames:v", str(n), "-r", FPS_S, "-dn", "-map_metadata", "-1", "-write_tmcd", "0",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", *enc, out + ".tmp.mov"])
    os.replace(out + ".tmp.mov", out)
    os.remove(lista)
    return out


def compoe(L, total_n, wav, out):
    """compõe em blocos de ~90 s. Um filtro só com a base, dezenas de letreiros e os L do QR (64 entradas) travava o
    ffmpeg com 0% de CPU no meio do vídeo; em blocos cada filtro abre poucas entradas. O corte entre blocos cai onde
    nenhuma camada está na tela; os blocos se juntam sem recomprimir e o som entra inteiro no fim."""
    pedacos = []
    for a, m, q in L.V:
        pedacos.append(render_fundo(q["fundo"], m) if "fundo" in q else render(q, m))
    # o L do QR: começa e termina na borda de um pedaço e vira um pedaço só, no lugar dos que cobre
    unid = [(a, m, arq) for (a, m, _), arq in zip(L.V, pedacos)]
    for qi, qr_ in enumerate(L.QR):
        na, nb = nq(qr_["a"]), nq(qr_["b"])
        i0 = min(range(len(unid)), key=lambda i: abs(unid[i][0] - na))
        s0 = unid[i0][0]
        i1 = min(range(i0, len(unid)), key=lambda i: abs(unid[i][0] + unid[i][1] - (s0 + nb - na)))
        s1 = unid[i1][0] + unid[i1][1]
        seg = render_qr([(u[2], u[1]) for u in unid[i0:i1 + 1]], s1 - s0, qr_["q"], f"qr{qi}")
        unid = unid[:i0] + [(s0, s1 - s0, seg)] + unid[i1 + 1:]
        print(f"  QR {qi}: {s0 / FPS:.1f} a {s1 / FPS:.1f} s", flush=True)
    total = total_n / FPS
    pasta = os.path.join(CACHE, os.path.basename(out) + ".blocos")
    os.makedirs(pasta, exist_ok=True)
    # nada de -ss dentro da lista: o salto no concat entrega os quadros com o tempo embolado e o fim dos blocos sumia.
    # O corte entre blocos cai na borda de uma unidade e fora de qualquer letreiro; cada bloco tem a lista só dele.
    ocup = [(c["a"] - 0.2, c["b"] + 0.2) for c in L.G]
    livre = lambda t: not any(a <= t <= b for a, b in ocup)
    bordas = [a for a, m, _ in unid if livre(a / FPS)]
    cortes, alvo = [0], 90.0
    while alvo < total - 40:
        cand = [n for n in bordas if alvo * FPS <= n <= (alvo + 60) * FPS]
        if not cand:
            alvo += 30; continue
        cortes.append(cand[0])
        alvo = cand[0] / FPS + 90
    cortes.append(total_n)

    def lista(n0, n1, nome):
        """as unidades inteiras que cobrem [n0, n1) e o quadro do começo da primeira"""
        ps = [(a, m, arq) for a, m, arq in unid if a + m > n0 and a < n1]
        arq_l = os.path.join(pasta, nome + ".txt")
        open(arq_l, "w").write("".join(f"file '{c}'\nduration {m / FPS:.6f}\n" for _, m, c in ps))
        return arq_l, ps[0][0]

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(2) as ex:
        blocos = list(ex.map(lambda i: compoe_bloco(L, lista, cortes[i], cortes[i + 1], total_n, pasta, i),
                             range(len(cortes) - 1)))
    lista_b = os.path.join(pasta, "blocos.txt")
    open(lista_b, "w").write("".join(f"file '{c}'\n" for c in blocos))
    sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista_b, "-i", wav, "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-t", f"{total:.4f}", "-movflags", "+faststart", lista_b + ".mp4"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    os.replace(lista_b + ".mp4", out)   # o render/ só vê o vídeo inteiro: a exportação pro Drive não pega arquivo pela metade


def compoe_bloco(L, lista, n0, n1, total_n, pasta, i):
    c0, c1 = n0 / FPS, n1 / FPS
    saida = os.path.join(pasta, f"{i:03d}.mp4")
    lb, p0 = lista(n0, n1, f"{i:03d}")
    ins = ["-reinit_filter", "0", "-f", "concat", "-safe", "0", "-i", lb]
    fc, ant, k = [f"[0:v]trim=start_frame={n0 - p0},setpts=PTS-STARTPTS[b0]"], "[b0]", 1
    for c in L.G:
        if c["b"] <= c0 or c["a"] >= c1:
            continue
        a, b = c["a"] - c0, c["b"] - c0
        a0 = max(a, 0)
        if c.get("seq"):      # sequência desenhada quadro a quadro (insight, nome, glossário): o movimento está nos PNGs
            ins += ["-framerate", FPS_S, "-start_number", str(max(0, int(round(-a * FPS)))), "-i", c["seq"]]
            fc.append(f"[{k}:v]format=rgba,setpts=PTS-STARTPTS+{a0:.4f}/TB[l{k}]")
            x, y = c["pos"]
            fc.append(f"{ant}[l{k}]overlay=x={x}:y={y}:eof_action=pass:enable='between(t,{a0:.3f},{b:.3f})'[v{k}]")
            ant = f"[v{k}]"; k += 1
            continue
        ins += ["-loop", "1", "-framerate", FPS_S, "-t", f"{b - a0 + 0.1:.3f}", "-i", c["png"]]
        fc.append(f"[{k}:v]format=rgba,setpts=PTS-STARTPTS+{a0:.4f}/TB,"
                  f"fade=t=in:st={a:.3f}:d={min(0.3, c['din']):.3f}:alpha=1,"
                  f"fade=t=out:st={b - c['dout']:.3f}:d={c['dout']:.3f}:alpha=1[l{k}]")
        x, y = c["pos"]
        mv = f"{c['dist']}*({_entra(a, c['din'])}+{_sai(b, c['dout'])})"
        # deslize lento o tempo todo (texto parado na tela parece travado, 15/11); o véu de tela cheia fica parado
        dv = "0" if tuple(c["pos"]) == (0, 0) else f"{14 * S}*(t-{a:.3f})/{max(b - a, 0.1):.3f}"
        xe, ye = {"esq": (f"{x}-{mv}-{dv}", f"{y}"), "dir": (f"{x}+{mv}+{dv}", f"{y}")}.get(
            c["mov"], (f"{x}", f"{y}+{mv}-{dv}" if c["mov"] == "sobe" else f"{y}-{dv}"))
        fc.append(f"{ant}[l{k}]overlay=x='{xe}':y='{ye}':eval=frame:eof_action=pass:enable='between(t,{a0:.3f},{b:.3f})'[v{k}]")
        ant = f"[v{k}]"; k += 1
    fim = []
    if n0 == 0:
        fim.append("fade=t=in:st=0:d=0.25")
    if n1 == total_n:
        fim.append(f"fade=t=out:st={c1 - c0 - 0.6:.3f}:d=0.6")
    fc.append(f"{ant}{','.join(fim + ['format=yuv420p'])}[vf]")
    if ESC == 2:
        enc = ["-c:v", "hevc_videotoolbox", "-b:v", "80M", "-tag:v", "hvc1", "-profile:v", "main"]
    else:
        enc = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high"]
    script = saida + ".filtro.txt"
    open(script, "w").write(";\n".join(fc))
    sh(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex_script", script, "-map", "[vf]", "-an",
        "-frames:v", str(n1 - n0), "-r", FPS_S, *enc, saida])
    print(f"  bloco {i}: {c0:.1f} a {c1:.1f} s, {k} entradas", flush=True)
    return saida


if __name__ == "__main__":
    from linha_yt import ROTEIRO, TRILHAS
    if os.environ.get("ATE") or os.environ.get("DE"):   # teste parcial: de uma marca até outra (fora) -> cache/teste.mp4
        ini_ = next(i for i, b_ in enumerate(ROTEIRO) if b_.get("marca") == os.environ["DE"]) if os.environ.get("DE") else 0
        corte = next(i for i, b_ in enumerate(ROTEIRO) if b_.get("marca") == os.environ["ATE"]) if os.environ.get("ATE") else len(ROTEIRO)
        ROTEIRO = ROTEIRO[ini_:corte] + ([dict(tipo="fim", dur=1.0)] if corte < len(ROTEIRO) else [])
        SAIDA = os.path.join(CACHE, "teste.mp4")
    L = monta_linha(ROTEIRO)
    if os.environ.get("ATE") or os.environ.get("DE"):
        def _tem(x):
            x = x[0] if isinstance(x, (tuple, list)) else x
            return not isinstance(x, str) or x in L.marcas
        TRILHAS = [dict(t, ate="fim") if not _tem(t["ate"]) else t for t in TRILHAS
                   if _tem(t["de"]) and _tem(t.get("alinha", 0)) and all(_tem(a) for a, _ in t.get("silencio", []))]
    total_n = L.t
    total = total_n / FPS
    print(f"duração {int(total // 60)} min {total % 60:.1f} s, {len(L.V)} pedaços, {len(L.G)} letreiros, marcas {L.marcas}", flush=True)
    linha = fontes.relativo(json.dumps(dict(V=L.V, A=L.A, G=[{k: v for k, v in g.items()} for g in L.G], marcas=L.marcas),
                                       indent=0, default=str))
    open(os.path.join(CACHE, "linha.json"), "w").write(linha)
    if not (os.environ.get("ATE") or os.environ.get("DE")):   # a linha do filme inteiro vai pro git (o teste parcial não)
        open(os.path.join(fontes.DADOS, "linha.json"), "w").write(linha)
    if os.environ.get("SO_LINHA"):
        sys.exit()
    som, abaixo = monta_som(L, total, TRILHAS)
    wav = os.path.join(CACHE, f"som{H}.wav")
    sf.write(wav, som, SR, subtype="PCM_24")
    print(f"som ok: trilha {abaixo:.1f} dB abaixo da voz", flush=True)
    compoe(L, total_n, wav, SAIDA)
    print("ok", SAIDA, flush=True)
