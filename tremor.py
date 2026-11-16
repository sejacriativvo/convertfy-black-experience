"""tremor.py [linha.json]: acha tomada tremida ou com zoom de câmera no vídeo (15/11: "aos 14:15 tá tremendo, ele tá
dando zoom ali, tá péssimo, você tá pegando takes errados").

Pra cada pedaço da linha do tempo, mede no trecho da fonte que vai pra tela (10 quadros/s, cópia pequena, fluxo óptico):
  tremor  o vaivém rápido da câmera (o deslocamento de quadro a quadro menos a média móvel de 0,5 s, que é o movimento
          intencional), em fração do quadro VISÍVEL: o zoom digital do enquadramento multiplica o tremor da mão
  zoom    a câmera aproximando ou afastando durante o pedaço (o operador mexendo no zoom)
  arrasto movimento lateral grande sem ser drone (câmera virando no meio da fala)
Sai a lista do pior pro melhor e cache/tremor.json.
"""
import os, sys, json, subprocess
import numpy as np
import cv2

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import fontes

AM, W, H = 10.0, 320, 180
FPS = 30000 / 1001
L = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, "cache", "linha.json")))
CACHE = os.path.join(AQUI, "dados", "analise", "tremor.json")
med = json.load(open(CACHE)) if os.path.exists(CACHE) else {}


def fluxo(src, a, d):
    k = f"{fontes.chave(src)}@{a:.2f}+{d:.2f}"
    if k in med:
        return med[k]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(a, 0):.3f}", *fontes.flags(src), "-i", fontes.caminho(src),
                          "-t", f"{d:.3f}", "-vf", f"fps={AM},scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    q = np.frombuffer(raw, np.uint8).reshape(-1, H, W)
    ys, xs = np.mgrid[0:H, 0:W]
    xs, ys = (xs - W / 2) / W, (ys - H / 2) / H
    r2 = xs ** 2 + ys ** 2 + 1e-6
    dx, dy, zm = [], [], []
    for i in range(1, len(q)):
        f = cv2.calcOpticalFlowFarneback(q[i - 1], q[i], None, 0.5, 3, 15, 3, 5, 1.1, 0)
        u, v = f[..., 0] / W, f[..., 1] / H
        dx.append(float(np.median(u))); dy.append(float(np.median(v)))
        zm.append(float(np.median((u * xs + v * ys) / r2)))
    med[k] = dict(dx=dx, dy=dy, zoom=zm)
    return med[k]


res = []
for a, n, q in L["V"]:
    src = q.get("src")
    if src is None or (isinstance(src, str) and src.startswith("d")) or n < 15:
        continue
    d = n / FPS * (0.5 if q.get("lento") else 1)
    m = fluxo(src, q["ss"], d)
    if len(m["dx"]) < 6:
        continue
    dx, dy, zm = (np.array(m[x]) for x in ("dx", "dy", "zoom"))
    k = 5
    suave = lambda x: np.convolve(x, np.ones(k) / k, mode="same")
    trem = float(np.sqrt(np.mean((dx - suave(dx)) ** 2 + (dy - suave(dy)) ** 2))) * q.get("z", 1.0) * AM
    zoom = float(abs(np.sum(zm)))            # aproximação acumulada no pedaço (fração)
    arrasto = float(np.sqrt(np.sum(dx) ** 2 + np.sum(dy) ** 2)) * q.get("z", 1.0)
    t = a / FPS
    res.append(dict(t=round(t, 2), quando=f"{int(t // 60)}:{t % 60:05.2f}", src=src, ss=round(q["ss"], 2), dur=round(n / FPS, 2),
                    z=round(q.get("z", 1.0), 2), tremor=round(trem, 4), zoom=round(zoom, 3), arrasto=round(arrasto, 3)))
json.dump(med, open(CACHE, "w"))
res.sort(key=lambda r: -(r["tremor"] / 0.012 + r["zoom"] / 0.08 + r["arrasto"] / 0.35))
json.dump(res, open(os.path.join(AQUI, "dados", "analise", "tremor-lista.json"), "w"), indent=1)
ruins = [r for r in res if r["tremor"] > 0.012 or r["zoom"] > 0.08 or r["arrasto"] > 0.35]
for r in ruins:
    print(f"{r['quando']:>9} {str(r['src']):>5} ss {r['ss']:7.2f} ({r['dur']:4.1f}s, z {r['z']:.2f})  tremor {r['tremor']:.4f}  "
          f"zoom {r['zoom']:.3f}  arrasto {r['arrasto']:.3f}")
print(f"{len(res)} pedaços medidos, {len(ruins)} passam do limite")
