"""sync.py [video.mp4]: mede se a imagem do vídeo pronto está no quadro certo (o som é montado na mesma linha do tempo).

Em instantes sem letreiro na tela, compara o quadro do mp4 final com o quadro esperado do pedaço do cache e com os
vizinhos (±4 quadros). O deslocamento que dá a menor diferença é o erro de sincronia daquele trecho: 0 = imagem no
lugar; positivo = a imagem está atrasada em relação ao som.
"""
import os, sys, json, subprocess, hashlib
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.argv = sys.argv[:2]
VIDEO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, "render", "black-experience-1080p.mp4")
sys.argv = ["x"]
import yt, fontes

L = json.load(open(os.path.join(AQUI, "cache", "linha.json")))
FPS = yt.FPS
ocup = [(float(g["a"]) - 0.3, float(g["b"]) + 0.3) for g in L["G"]]


def peca(q, m):
    vf = yt.filtro(q) + ",format=yuv422p10le"
    return os.path.join(yt.TRECHOS, yt.chave_peca(q, m, vf, yt.decodifica(q["src"])) + ".mov")


def quadros(arq, n0, k):
    """k quadros a partir do índice n0, em cinza 64x36, escolhidos pelo número (o salto por tempo com +0,001 s caía no
    quadro seguinte e acusava +1 em todo ponto)"""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-vf",
                          f"select='between(n\\,{max(n0, 0)}\\,{max(n0, 0) + k - 1})',scale=64:36,format=gray",
                          "-vsync", "0", "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 36, 64).astype(np.float32)


total = sum(m for a, m, q in L["V"])
amostras = []
for a, m, q in L["V"]:
    if "fundo" in q or m < 40:
        continue
    t = (a + m // 2) / FPS
    if any(x <= t <= y for x, y in ocup):
        continue
    amostras.append((a, m, q))
amostras = amostras[:: max(1, len(amostras) // 40)]
# o vídeo pronto é lido inteiro, pelo número do quadro: o salto por tempo (-ss) no mp4 com quadro B cai um quadro
# adiante e acusava +1 em todo ponto, até no primeiro segundo
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", VIDEO, "-vf", "scale=64:36,format=gray", "-vsync", "0", "-f", "rawvideo", "-"],
                     capture_output=True).stdout
TODO = np.frombuffer(raw, np.uint8).reshape(-1, 36, 64).astype(np.float32)
piores = 0
for a, m, q in amostras:
    n = a + m // 2
    ref = quadros(peca(q, m), m // 2, 1)
    fin = TODO[n - 12:n + 13]
    if not len(ref) or len(fin) < 25:
        print(f"{n / FPS:8.2f}s  sem quadro"); continue
    d = [float(np.abs(f - ref[0]).mean()) for f in fin]
    off = int(np.argmin(d)) - 12
    if sorted(d)[1] - min(d) < 0.15:          # tomada parada: os vizinhos empatam, não dá pra medir
        print(f"   {n / FPS:8.2f}s {str(q['src']):>5}  parado, sem medida"); continue
    piores += off != 0
    print(f"{'  ' if off == 0 else '!!'} {n / FPS:8.2f}s {str(q['src']):>5}  deslocamento {off:+d} quadros  (dif {min(d):.1f})", flush=True)
print(f"{len(amostras)} pontos, {piores} fora do quadro")
