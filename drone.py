"""drone.py: o melhor movimento de cada tomada de drone (pedido de 15/11: "não aproveitou os melhores momentos do drone",
"tem muito sol").

Mede cada clipe DJI a 10 quadros por segundo numa cópia pequena: o movimento da câmera entre quadros seguidos (fluxo
óptico: deslocamento lateral e vertical, aproximação/afastamento pela divergência, giro em volta do ponto pelo
rotacional), o tranco (variação brusca do movimento), o drone parado no ar, e o sol (quadro com área estourada grande).
Nota de um trecho = movimento firme e contínuo, sem tranco, sem parada, sem sol. Sai cache/drone.json e, rodando
direto, a lista dos melhores trechos de cada clipe e folhas/drone-*.jpg com 8 quadros de cada clipe.

    python drone.py            -> mede (cache) e imprime os 3 melhores trechos de 3 s de cada clipe
"""
import os, sys, json, subprocess
import numpy as np
import cv2

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import fontes

AM = 10.0
W, H = 384, 216
CACHE = os.path.join(AQUI, "dados", "analise", "drone.json")
med = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
CLIPES = [f"d{n}" for n in range(477, 502) if n != 496]


def mede(src):
    if src in med:
        return med[src]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", fontes.caminho(src), "-vf",
                          f"fps={AM},scale={W}:{H},{fontes.cor(src)},format=rgb24", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    q = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    cinza = [cv2.cvtColor(f, cv2.COLOR_RGB2GRAY) for f in q]
    ys, xs = np.mgrid[0:H, 0:W]
    xs, ys = (xs - W / 2) / W, (ys - H / 2) / H
    r2 = xs ** 2 + ys ** 2 + 1e-6
    out = dict(dx=[0.0], dy=[0.0], zoom=[0.0], giro=[0.0], luz=[], sol=[])
    for i, f in enumerate(cinza):
        hsv = cv2.cvtColor(q[i], cv2.COLOR_RGB2HSV)
        out["luz"].append(float(f.mean()))
        # sol: pixels quase brancos e pouco saturados, em mancha (não reflexo espalhado)
        estouro = ((hsv[..., 2] > 245) & (hsv[..., 1] < 40)).astype(np.uint8)
        n, _, st, _ = cv2.connectedComponentsWithStats(estouro, 8)
        out["sol"].append(float(st[1:, cv2.CC_STAT_AREA].max() / (W * H)) if n > 1 else 0.0)
        if i == 0:
            continue
        fl = cv2.calcOpticalFlowFarneback(cinza[i - 1], f, None, 0.5, 3, 21, 3, 5, 1.1, 0)
        u, v = fl[..., 0] / W * AM, fl[..., 1] / H * AM          # fração do quadro por segundo
        out["dx"].append(float(np.median(u)))
        out["dy"].append(float(np.median(v)))
        out["zoom"].append(float(np.median((u * xs + v * ys) / r2)))
        out["giro"].append(float(np.median((v * xs - u * ys) / r2)))
    med[src] = out
    json.dump(med, open(CACHE, "w"))
    return out


def trechos(m, dur=3.0):
    """[(nota, ini, descrição)] dos trechos de `dur` segundos, de 0,5 em 0,5 s, fora do primeiro e do último 0,5 s"""
    dx, dy, zm, gr = (np.array(m[k]) for k in ("dx", "dy", "zoom", "giro"))
    vel = np.sqrt(dx ** 2 + dy ** 2 + (0.5 * zm) ** 2 + (0.5 * gr) ** 2)
    sol = np.array(m["sol"])
    w = int(dur * AM)
    out = []
    for i0 in range(int(0.5 * AM), len(vel) - w - int(0.5 * AM), int(0.5 * AM)):
        v = vel[i0:i0 + w]
        mov = float(np.median(v))
        tranco = float(np.percentile(np.abs(np.diff(np.stack([dx, dy, zm, gr])[:, i0:i0 + w], axis=1)).sum(0), 90))
        parado = float(np.mean(v < 0.004))
        s = float(np.max(sol[i0:i0 + w]))
        # movimento bom: entre 1% e 12% do quadro por segundo, firme (tranco baixo contra o próprio movimento)
        nota = min(mov, 0.06) / 0.06 - 1.5 * max(tranco / (mov + 0.01) - 1.2, 0) * 0.3 - 1.2 * parado - 8 * max(s - 0.004, 0)
        tipo = max((("lateral", abs(np.median(dx[i0:i0 + w]))), ("vertical", abs(np.median(dy[i0:i0 + w]))),
                    ("aproxima" if np.median(zm[i0:i0 + w]) > 0 else "afasta", abs(np.median(zm[i0:i0 + w])) * 0.5),
                    ("órbita", abs(np.median(gr[i0:i0 + w])) * 0.5)), key=lambda x: x[1])[0]
        out.append((round(nota, 2), round(i0 / AM, 1), f"{tipo} mov {mov:.3f} tranco {tranco:.3f} parado {parado:.0%} sol {s:.3f}"))
    return sorted(out, reverse=True)


if __name__ == "__main__":
    for src in CLIPES:
        m = mede(src)
        sol = np.array(m["sol"])
        t = trechos(m)
        top, usados = [], []
        for nota, ini, d in t:
            if all(abs(ini - u) >= 3 for u in usados):
                top.append(f"{ini:5.1f}s nota {nota:5.2f} ({d})"); usados.append(ini)
            if len(top) == 3:
                break
        com_sol = np.mean(sol > 0.004)
        print(f"{src} ({len(sol) / AM:4.1f}s, luz {np.mean(m['luz']):5.1f}, sol em {com_sol:.0%} dos quadros)")
        for x in top:
            print("    " + x)
