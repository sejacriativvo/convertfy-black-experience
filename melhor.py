"""melhor.py: o melhor trecho de cada take de apoio (pedido de 15/11: "certifique-se que pegou os melhores frames").

Pra cada imagem de apoio do roteiro (broll e cobertura), mede o clipe inteiro a 6 quadros por segundo numa cópia
pequena: nitidez (variância do laplaciano, contra a mediana do próprio clipe), tremida (diferença entre quadros
seguidos) e exposição. Nota de um trecho = nitidez média - penalidade de tremida e de quadro estourado ou escuro.
Compara o trecho escolhido com o melhor trecho do mesmo tamanho dentro do clipe (fora o primeiro e o último
0,4 s, onde a câmera liga e desliga). Sai a lista dos que dá pra melhorar, com o ss sugerido.

    python melhor.py            -> relatório (cache/melhor.json guarda as medidas por clipe)
"""
import os, sys, json, subprocess
import numpy as np
from scipy import ndimage

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import fontes
from linha_yt import ROTEIRO

AM = 6.0                                  # quadros por segundo na medida
CACHE = os.path.join(AQUI, "dados", "analise", "melhor.json")
med = json.load(open(CACHE)) if os.path.exists(CACHE) else {}


def mede(src):
    k = fontes.chave(src)
    if k in med:
        return med[k]
    raw = subprocess.run(["ffmpeg", "-v", "error", *fontes.flags(src), "-i", fontes.caminho(src), "-vf",
                          f"fps={AM},scale=320:180,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    q = np.frombuffer(raw, np.uint8).reshape(-1, 180, 320).astype(np.float32)
    nit = [float(ndimage.laplace(f).var()) for f in q]
    mov = [0.0] + [float(np.abs(q[i] - q[i - 1]).mean()) for i in range(1, len(q))]
    luz = [float(f.mean()) for f in q]
    med[k] = dict(nit=nit, mov=mov, luz=luz)
    json.dump(med, open(CACHE, "w"))
    return med[k]


def nota(m, i0, i1):
    nit = np.array(m["nit"][i0:i1]); mov = np.array(m["mov"][i0:i1]); luz = np.array(m["luz"][i0:i1])
    if len(nit) == 0:
        return -99
    ref = np.median(m["nit"]) or 1
    tremida = np.percentile(mov, 90) / (np.median(m["mov"]) + 1)
    exp = np.mean((luz < 25) | (luz > 235))
    return float(np.mean(nit) / ref - 0.35 * max(tremida - 1.5, 0) - 2 * exp)


def tomadas():
    """(rótulo, clipe, ss, duração na fonte) de cada imagem de apoio do roteiro"""
    for k, b in enumerate(ROTEIRO):
        if b["tipo"] == "broll":
            bat = 60 / b["bpm"] if "bpm" in b else 1
            for t in b["tomadas"]:
                op = t[3] if len(t) > 3 else {}
                lento = op.get("lento", b.get("lento", True)) and fontes.fps(t[0]) > 50
                yield (f"bloco {k} {b.get('marca', '')}", t[0], t[1], t[2] * bat * (0.5 if lento else 1))
        for cob in b.get("cobertura", []):
            a, c = cob[0], cob[1]
            if isinstance(cob[2], list):
                passo = (c - a) / len(cob[2])
                for pl in cob[2]:
                    yield (f"bloco {k} cobertura", pl[0], pl[1], passo * (0.5 if fontes.fps(pl[0]) > 50 else 1))
            else:
                lento = (cob[4] if len(cob) > 4 else True) and fontes.fps(cob[2]) > 50
                yield (f"bloco {k} cobertura", cob[2], cob[3], (c - a) * (0.5 if lento else 1))


melhorar = []
for rot, src, ss, d in tomadas():
    m = mede(src)
    n = len(m["nit"])
    w = max(int(round(d * AM)), 1)
    i0 = int(round(ss * AM))
    atual = nota(m, i0, i0 + w)
    borda = int(0.4 * AM)
    cands = [(nota(m, j, j + w), j) for j in range(borda, max(n - w - borda, borda) + 1)]
    best, jb = max(cands) if cands else (atual, i0)
    marca = "!!" if best - atual > 0.25 else "  "
    if marca == "!!":
        melhorar.append(dict(rot=rot, src=src, ss=ss, d=round(d, 2), atual=round(atual, 2), melhor=round(best, 2),
                             ss_melhor=round(jb / AM, 2)))
    print(f"{marca} {rot:28s} {str(src):>6} ss {ss:6.2f} ({d:4.1f}s)  nota {atual:5.2f}  melhor {best:5.2f} em {jb / AM:6.2f}", flush=True)
json.dump(melhorar, open(os.path.join(AQUI, "dados", "analise", "melhorar.json"), "w"), indent=1)
print(f"{len(melhorar)} tomadas dá pra melhorar")
