"""Enquadramento pelos rostos (Vision, ferramentas/pessoas): quem aparece fica no centro, nunca no canto.

O bruto é 4K e a saída 1080p, então zoom até 2x não perde nada de definição.
fala:   rostos principais centralizados na horizontal, olhos perto de um terço da altura.
apoio:  B-roll com gente centraliza o grupo e aproxima de leve; sem gente fica como está.
"""
import os, subprocess, json, hashlib, shutil
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(AQUI, "dados", "rostos")   # no git: o mesmo enquadramento em qualquer máquina
PESSOAS = os.path.join(AQUI, "ferramentas", "pessoas")
from cor import cor_de
import fontes

Z_MAX = 2.0


def detecta(fonte, ini, dur, amostra=3):
    """[(t, rostos, corpos)] com (cx, cy, w, h) normalizados, origem em cima à esquerda"""
    chave = hashlib.md5(f"{fontes.relativo(fonte)}|{ini:.3f}|{dur:.3f}|{amostra}".encode()).hexdigest()[:12]
    saida = os.path.join(CACHE, chave + ".json")
    if os.path.exists(saida):
        return json.load(open(saida))
    pasta = os.path.join(CACHE, "q_" + chave)
    shutil.rmtree(pasta, ignore_errors=True); os.makedirs(pasta)
    subprocess.run(["ffmpeg", "-v", "error", "-hwaccel", "videotoolbox", "-ss", f"{ini:.3f}", "-t", f"{dur:.3f}",
                    "-i", fonte, "-vf", f"fps={amostra},scale=1280:-2,{cor_de(fonte)}", "-q:v", "3",
                    os.path.join(pasta, "%05d.jpg")], check=True)
    linhas = subprocess.run([PESSOAS, pasta], capture_output=True, text=True, check=True).stdout.strip().splitlines()
    out = []
    for ln in linhas:
        nome, f, p = ln.split("|")
        rost = [list(map(float, x.split())) for x in f.split(";") if x.strip()]
        corp = [list(map(float, x.split())) for x in p.split(";") if x.strip()]
        out.append((ini + (int(nome[:5]) - 1) / amostra, rost, corp))
    shutil.rmtree(pasta, ignore_errors=True)
    os.makedirs(CACHE, exist_ok=True)
    json.dump(out, open(saida, "w"))
    return out


def _principais(rostos):
    """os rostos de quem importa no quadro: os grandes, não o fundo"""
    if not rostos:
        return []
    hmax = max(r[3] for r in rostos)
    return [r for r in rostos if r[3] >= 0.6 * hmax and r[3] >= 0.04]


def grupo(dets, t0=None, t1=None):
    """extensão dos rostos principais no trecho: (x0, x1, cy, w, h) ou None"""
    x0s, x1s, cys, ws, hs = [], [], [], [], []
    if t0 is not None:
        dets = [d for d in dets if t0 <= d[0] <= t1]
    for t, rost, _ in dets:
        pr = _principais(rost)
        if not pr:
            continue
        x0s.append(min(r[0] - r[2] / 2 for r in pr)); x1s.append(max(r[0] + r[2] / 2 for r in pr))
        cys.append(np.mean([r[1] for r in pr])); ws.append(np.median([r[2] for r in pr])); hs.append(np.median([r[3] for r in pr]))
    if len(x0s) < max(1, 0.3 * len(dets)):
        return None
    return (float(np.percentile(x0s, 25)), float(np.percentile(x1s, 75)), float(np.median(cys)),
            float(np.median(ws)), float(np.median(hs)))


def corpos(dets):
    """centro dos corpos (gente de costas não tem rosto): (cx, cy) ou None"""
    cs = [(c[0], c[1]) for _, _, cp in dets for c in cp if c[3] >= 0.3]
    if len(cs) < max(1, 0.3 * len(dets)):
        return None
    a = np.array(cs)
    return float(np.median(a[:, 0])), float(np.median(a[:, 1]))


def centro(g, z, olhos=0.34):
    """centro do recorte que põe o grupo no meio e os rostos a `olhos` da altura"""
    x0, x1, cy, _, _ = g
    cx = (x0 + x1) / 2
    topo = cy - olhos / z
    return cx, topo + 0.5 / z


def zoom_fala(g, zmin=1.12, base=1.0):
    """base < 1: recorte vertical tirado de fonte horizontal (largura do recorte em fração da fonte).
    Aí o plano é o mais justo em que os rostos ainda cabem, sem passar de 1,6x."""
    x0, x1, _, w, h = g
    if base < 1:
        return float(np.clip(base / ((x1 - x0) + 2.4 * w), 1.0, 1.6))
    largura = (x1 - x0) + 2 * 1.5 * w        # rostos + ombros
    z = 0.62 / largura
    z = min(z, 0.2 / h)                       # rosto no máximo 20% da altura no plano aberto
    return float(np.clip(z, zmin, 1.6))


def apoio(fonte, ini, dur_src, base=1.0):
    """(z, cx, cy) pra imagem de apoio; base = largura do recorte sem zoom, em fração da fonte"""
    d = detecta(fonte, ini, max(dur_src, 0.4), amostra=4)
    g = grupo(d)
    if g:
        x0, x1, _, w, h = g
        z = float(np.clip(0.85 / (((x1 - x0) + 2 * 1.8 * w) / base), 1.0, 1.4))
        z = 1.0 if z <= 1.03 else z
        cx, cy = centro(g, z, olhos=0.36)
        return z, cx, cy
    c = corpos(d)
    if c:
        return 1.15, c[0], 0.5
    return 1.0, 0.5, 0.5
