"""emendas_final.py [video.mp4]: confere cada emenda de fala do vídeo PRONTO (palavra cortada no começo ou no fim).

Emenda = onde um pedaço de fala acaba e o seguinte não continua do mesmo ponto do mesmo clipe. Três sinais:
  som      a voz no ponto exato do corte, na fonte (±20 ms), entre o fundo (0) e a fala (1) do lugar (±3 s).
           Corte com a voz ainda alta é palavra pela metade, diga o que disser a transcrição
  palavra  palavra do Whisper da fonte que o corte atravessa (fica entre 15% e 85% dela dentro do pedaço)
  ouvido   o vídeo pronto inteiro transcrito UMA vez e alinhado com o texto esperado: palavra que sumiu, mudou ou
           sobrou a menos de 0,4 s da emenda
A marcação de tempo do Whisper tem folga de ~0,1 s e ele ouve a mesma palavra dos dois lados de um corte, por isso a
versão que comparava "última palavra ouvida" com "última palavra do roteiro" acusava 247 de 341 emendas boas
(15/11). Aqui só o som condena: !! é voz alta colada no corte, ?  é transcrição desconfiada com o corte em silêncio.
Sai cache/emendas.json com tudo.
"""
import os, sys, json, re, subprocess, tempfile, difflib
import numpy as np
import mlx_whisper
import fontes, respiros

AQUI = os.path.dirname(os.path.abspath(__file__))
VIDEO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, "render", "black-experience-1080p.mp4")
L = json.load(open(os.path.join(AQUI, "cache", "linha.json")))
A = sorted(L["A"], key=lambda x: x[3])
T = fontes.transcricao()
norm = lambda w: re.sub(r"[^\w]", "", w).lower()
VOZ_ALTA = 0.5
PERTO = 0.4


def palavras(src):
    return [(w["start"], w["end"], norm(w["word"])) for s in T.get(fontes.chave(src), []) for w in s.get("words", [])]


def ouvido():
    """o vídeo pronto transcrito inteiro, guardado pelo tamanho e data do arquivo"""
    st = os.stat(VIDEO)
    marca = f"{st.st_size}-{int(st.st_mtime)}"
    arq = os.path.join(AQUI, "cache", "ouvido-final.json")
    if os.path.exists(arq):
        c = json.load(open(arq))
        if c["marca"] == marca:
            return c["palavras"]
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", VIDEO, "-vn", "-ac", "1", "-ar", "16000", f.name], check=True)
        r = mlx_whisper.transcribe(f.name, path_or_hf_repo="mlx-community/whisper-large-v3-mlx", language="pt",
                                   word_timestamps=True, condition_on_previous_text=False)
    pal = [(w["start"], w["end"], norm(w["word"])) for s in r["segments"] for w in s.get("words", []) if norm(w["word"])]
    json.dump(dict(marca=marca, palavras=pal), open(arq, "w"))
    return pal


# o texto esperado: cada palavra da fonte que fica pelo menos metade dentro de um pedaço, no tempo do vídeo
esperado, fragmentos = [], []
for src, i, d, t, _ in A:
    for w0, w1, w in palavras(src):
        ov = min(w1, i + d) - max(w0, i)
        if ov <= 0 or not w:
            continue
        fr = ov / max(w1 - w0, 0.01)
        if fr >= 0.5:
            esperado.append((t + max(w0, i) - i, w))
        if 0.15 < fr < 0.85 and w1 - w0 > 0.12:
            fragmentos.append((t + max(w0, i) - i, w, round(fr, 2)))
esperado.sort()
ouv = ouvido()

# alinha esperado x ouvido; o que não bate vira um instante suspeito (grafia parecida conta como igual)
sm = difflib.SequenceMatcher(None, [w for _, w in esperado], [w for _, _, w in ouv], autojunk=False)
suspeitos = []
for op, a0, a1, b0, b1 in sm.get_opcodes():
    if op == "equal":
        continue
    if op == "replace" and a1 - a0 == b1 - b0 and all(
            difflib.SequenceMatcher(None, esperado[a0 + k][1], ouv[b0 + k][2]).ratio() >= 0.6 for k in range(a1 - a0)):
        continue
    tempos = [esperado[k][0] for k in range(a0, a1)] + [ouv[k][0] for k in range(b0, b1)]
    if not tempos and 0 < a0 < len(esperado):
        tempos = [esperado[a0][0]]
    txt = f"'{' '.join(w for _, w in esperado[a0:a1])}' -> '{' '.join(x[2] for x in ouv[b0:b1])}'"
    suspeitos += [(x, txt) for x in tempos]

res, n = [], 0
for k in range(len(A) - 1):
    s1, i1, d1, t1, _ = A[k]
    s2, i2, d2, t2, _ = A[k + 1]
    if s1 == s2 and abs(i1 + d1 - i2) < 0.02:
        continue
    n += 1
    corte = t1 + d1
    som_fim, som_ini = respiros.nivel(s1, i1 + d1, "fim"), respiros.nivel(s2, i2, "ini")
    lo, hi = min(corte, t2) - PERTO, max(corte, t2) + PERTO
    frag = [f"{w}({fr})" for x, w, fr in fragmentos if lo <= x <= hi]
    ouv_ = sorted({txt for x, txt in suspeitos if lo <= x <= hi})
    alto = [lado for lado, v in (("fim", som_fim), ("começo", som_ini)) if v > VOZ_ALTA]
    sinais = bool(alto) + bool(frag) + bool(ouv_)
    grav = "!!" if alto else ("? " if sinais else "  ")
    r = dict(t=round(corte, 2), de=f"{s1}@{i1 + d1:.2f}", para=f"{s2}@{i2:.2f}", som_fim=round(som_fim, 2),
             som_ini=round(som_ini, 2), fragmento=frag, ouvido=ouv_, grav=grav.strip())
    res.append(r)
    if grav != "  ":
        print(f"{grav} {corte:8.2f}s  {r['de']:>12} -> {r['para']:<12} som fim {som_fim:4.2f} começo {som_ini:4.2f}"
              f"  {' '.join(frag)}  {' | '.join(ouv_)}", flush=True)
json.dump(res, open(os.path.join(AQUI, "cache", "emendas.json"), "w"), indent=1, ensure_ascii=False)
print(f"{n} emendas: {sum(r['grav'] == '!!' for r in res)} com voz alta no corte (!!), {sum(r['grav'] == '?' for r in res)} só com transcrição desconfiada (?)")
