"""emendas.py: confere no áudio bruto cada emenda da linha (cache/linha.json, saída do SO_LINHA=1 yt.py).

Para cada pedaço de fala, olha 30 ms de cada lado do começo e do fim no clipe original. Se o lado que FICA tem voz
(acima do limite de silêncio medido em volta) e o lado que SAI também, a emenda passou no meio de som: palavra cortada.
Pedaços colados (o fim de um é o começo do próximo no mesmo clipe) não contam. Sai lista das emendas suspeitas.
"""
import json, os
import numpy as np
import respiros

AQUI = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(AQUI, "cache", "linha.json")))
A = sorted(L["A"], key=lambda x: x[3])


def som(src, a, b):
    q, _ = respiros.quieto(src, a, b)
    return len(q) and (~q).mean() > 0.5   # mesmo limite de silêncio da emenda (fundo local + 8 dB)


ruins = 0
for i, (src, ini, d, t0, _) in enumerate(A):
    fim = ini + d
    antes = A[i - 1] if i else None
    depois = A[i + 1] if i + 1 < len(A) else None
    colado_ini = antes and antes[0] == src and abs(antes[1] + antes[2] - ini) < 0.02
    colado_fim = depois and depois[0] == src and abs(depois[1] - fim) < 0.02
    for nome, t, fica, sai, colado in (("começo", ini, (ini, ini + 0.03), (ini - 0.03, ini), colado_ini),
                                        ("fim", fim, (fim - 0.03, fim), (fim, fim + 0.03), colado_fim)):
        if colado or t < 0.05:
            continue
        if som(src, *fica) and som(src, *sai):
            ruins += 1
            print(f"  corte no som: {src} {nome} em {t:.2f}s (no vídeo {t0 + (0 if nome == 'começo' else d):.2f}s)")
print(f"{len(A)} pedaços de fala, {ruins} emendas no meio de som")


# segunda conferência: o que o Whisper ouve na borda de cada pedaço, no clipe original. A primeira palavra ouvida
# no começo e a última no fim têm que ser as que o roteiro quer (palavra pela metade vira outra ou some).
import json as _j, re, subprocess, tempfile
import mlx_whisper

import fontes
T = fontes.transcricao()


def ouve(src, a, b):
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(a, 0):.3f}", "-to", f"{b:.3f}", "-i",
                        fontes.caminho(src), "-vn", "-ac", "1", "-ar", "16000", f.name], check=True)
        r = mlx_whisper.transcribe(f.name, path_or_hf_repo="mlx-community/whisper-large-v3-mlx", language="pt")
    return re.sub(r"[^\w\s]", "", r["text"]).lower().split()


def esperado(src, a, b):
    ws = [w["word"] for s in T[fontes.chave(src)] for w in s.get("words", []) if w["start"] >= a - 0.05 and w["end"] <= b + 0.05]
    return re.sub(r"[^\w\s]", "", " ".join(ws)).lower().split()


if os.environ.get("OUVIR"):
    for i, (src, ini, d, t0, _) in enumerate(A):
        fim = ini + d
        antes = A[i - 1] if i else None
        depois = A[i + 1] if i + 1 < len(A) else None
        if not (antes and antes[0] == src and abs(antes[1] + antes[2] - ini) < 0.02):
            o, e = ouve(src, ini, min(ini + 2.5, fim)), esperado(src, ini, min(ini + 2.5, fim))
            ok = o[:1] == e[:1]
            print(f"{'  ' if ok else '!!'} {src} começo {ini:7.2f}: ouvido '{' '.join(o[:4])}' | roteiro '{' '.join(e[:4])}'")
        if not (depois and depois[0] == src and abs(depois[1] - fim) < 0.02):
            o, e = ouve(src, max(fim - 2.5, ini), fim), esperado(src, max(fim - 2.5, ini), fim)
            ok = o[-1:] == e[-1:]
            print(f"{'  ' if ok else '!!'} {src} fim    {fim:7.2f}: ouvido '{' '.join(o[-4:])}' | roteiro '{' '.join(e[-4:])}'")
