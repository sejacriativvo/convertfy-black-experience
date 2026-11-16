"""Respiração e pausa: acha onde ninguém fala dentro de um trecho e devolve os pedaços que ficam.

Duas faixas (voz 250-4000 Hz e chiado do S acima de 4,5 kHz), envelope de 10 ms, contra o piso de ruído do
CLIPE INTEIRO (a casa tinha som ambiente e conversa no fundo). A pausa só vira corte se as duas faixas ficarem
perto do piso. Só corta pausa longa (0,6 s ou mais), deixando 0,25 s depois da fala e 0,14 s antes da próxima:
respiração curta fica, que é ritmo de quem fala. O corte não encosta em palavra nenhuma do Whisper (começo e fim).
"""
import os, json, subprocess
import numpy as np
from scipy.signal import butter, sosfiltfilt
import fontes

AQUI = os.path.dirname(os.path.abspath(__file__))
SR = 16000
MINIMO = 0.60        # pausa menor que isso fica
SOBRA_ANTES = 0.25   # silêncio que fica depois da palavra anterior (cauda de "-ção" e "-ão" é baixa e longa)
SOBRA_DEPOIS = 0.14  # silêncio que fica antes da próxima palavra
_AUD, _PISO, _TR = {}, {}, None


def _audio(src):
    if src not in _AUD:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", fontes.caminho(src), "-map", "0:a:0", "-ac", "1",
                              "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
        x = np.frombuffer(raw, np.float32)
        j = int(0.01 * SR)
        out = []
        for lo, hi in ((250, 4000), (4500, None)):
            sos = butter(4, [lo, hi], "bandpass", fs=SR, output="sos") if hi else butter(4, lo, "highpass", fs=SR, output="sos")
            y = sosfiltfilt(sos, x)
            n = len(y) // j
            out.append(10 * np.log10(np.mean(y[:n * j].reshape(n, j) ** 2, axis=1) + 1e-12))
        _AUD[src] = out
    return _AUD[src]


def _palavras(src):
    global _TR
    if _TR is None:
        _TR = fontes.transcricao()
    return [(w["start"], w["end"]) for s in _TR.get(fontes.chave(src), []) for w in s.get("words", [])]


def pedacos(src, a, b, minimo=MINIMO):
    """[(ini, fim)] dentro de [a, b] sem as pausas"""
    v, s = _audio(src)
    i0, i1 = int(a * 100), int(b * 100)
    vv, ss = v[i0:i1], s[i0:i1]
    piso_v, piso_s = np.percentile(v, 4), np.percentile(s, 4)
    fala_v = np.percentile(vv, 90)
    lim_v = max(piso_v + 7, fala_v - 24)
    lim_s = max(piso_s + 7, np.percentile(ss, 90) - 22)
    quieto = (vv < lim_v) & (ss < lim_s)
    palavras = [(w0, w1) for w0, w1 in _palavras(src) if w1 >= a and w0 <= b]
    cortes, k = [], 0
    while k < len(quieto):
        if not quieto[k]:
            k += 1; continue
        m = k
        while m < len(quieto) and quieto[m]:
            m += 1
        p0, p1 = a + k / 100, a + m / 100
        if p1 - p0 >= minimo and k > 0 and m < len(quieto):
            ca, cb = p0 + SOBRA_ANTES, p1 - SOBRA_DEPOIS
            if cb - ca > 0.15 and not any(w0 < cb + 0.06 and w1 > ca - 0.10 for w0, w1 in palavras):
                cortes.append((ca, cb))
        k = m
    out, pos = [], a
    for ca, cb in cortes:
        out.append((pos, ca)); pos = cb
    out.append((pos, b))
    return [(x, y) for x, y in out if y - x > 0.12]


def _limites(src, a, b):
    """silêncio = até 8 dB acima do fundo local (percentil 10 em ±3 s): a festa tinha conversa no fundo o tempo
    todo, então o piso do clipe inteiro nunca é alcançado entre duas palavras"""
    v, s = _audio(src)
    j0, j1 = max(int((a - 3) * 100), 0), min(int((b + 3) * 100), len(v))
    return np.percentile(v[j0:j1], 10) + 8, np.percentile(s[j0:j1], 10) + 8


def quieto(src, a, b):
    """máscara de 10 ms em [a, b] (voz e chiado do S no fundo) e o índice do primeiro quadro"""
    v, s = _audio(src)
    lim_v, lim_s = _limites(src, a, b)
    i0, i1 = max(int(a * 100), 0), min(int(b * 100), len(v))
    return (v[i0:i1] < lim_v) & (s[i0:i1] < lim_s), i0


def vale(src, t, lado=None, r=0.45):
    """a emenda cai num silêncio de verdade (50 ms ou mais no fundo), nunca no fechamento de um P ou T.

    O Whisper erra a borda da palavra em até 0,15 s, então o tempo escrito é só o rumo:
    lado="fim" (último quadro que fica) procura o PRIMEIRO silêncio a partir de t, depois da última palavra;
    lado="ini" (primeiro quadro que fica) procura o ÚLTIMO silêncio até t, antes da primeira palavra.
    Nos dois casos, 40 ms depois do começo do vão: logo depois da palavra de antes, longe do ataque da próxima."""
    v, s = _audio(src)
    q, i0 = quieto(src, t - r, t + r)
    e = np.maximum(v, s - 6)
    vaos, k = [], 0
    while k < len(q):
        if not q[k]:
            k += 1; continue
        m = k
        while m < len(q) and q[m]:
            m += 1
        if m - k >= 5:
            vaos.append((i0 + k, i0 + m))
        k = m
    ti = int(t * 100)
    if lado == "fim":
        vaos = [x for x in vaos if x[1] > ti - 3][:1]
    elif lado == "ini":
        vaos = [x for x in vaos if x[0] < ti + 3][-1:]
    else:
        vaos = sorted(vaos, key=lambda x: min(abs(x[0] - ti), abs(x[1] - ti)))[:1]
    if not vaos:
        # sem vão: o ponto mais baixo (média de 30 ms) do lado certo, que é onde uma palavra solta a outra
        es = np.convolve(e, np.ones(3) / 3, mode="same")
        j0, j1 = (ti - 2, ti + 35) if lado == "fim" else (ti - 35, ti + 2) if lado == "ini" else (ti - 10, ti + 10)
        j0 = max(j0, 0)
        print(f"  ! emenda sem vão: {src} em {t:.2f}s ({lado})")
        return (j0 + int(np.argmin(es[j0:j1]))) / 100 + 0.005
    k, m = vaos[0]
    if lado == "fim":        # cedo no vão: guarda a cauda da palavra e não encosta no ataque da próxima
        return (k + min(4, (m - k) // 2)) / 100 + 0.005
    if lado == "ini":        # cedo no vão também: palavra que começa baixinho ("Se você...") some no fundo da festa
        return (k + min(4, (m - k) // 2)) / 100 + 0.005
    k2, m2 = k + 2, max(m - 2, k + 3)
    return (k2 + int(np.argmin(e[k2:m2]))) / 100 + 0.005



def nivel(src, t, lado):
    """a voz nos 20 ms que ficam colados num corte (fim: os últimos antes de t; ini: os primeiros depois), entre o fundo
    (0) e a fala (1) do lugar (percentis 10 e 90 em ±3 s), na energia da voz ou do chiado do S 6 dB abaixo.
    Acima de ~0,5 é corte com voz soando: palavra pela metade ou ataque comido"""
    v, s = _audio(src)
    e = np.maximum(v, s - 6)
    c = int(round(t * 100))
    j0, j1 = max(c - 300, 0), min(c + 300, len(e))
    fundo, fala = np.percentile(e[j0:j1], 10), np.percentile(e[j0:j1], 90)
    x = e[max(c - 2, 0):max(c, 1)] if lado == "fim" else e[c:c + 2]
    return float((np.max(x) - fundo) / max(fala - fundo, 6))


# ======================================================================= respiração (pedido de 15/11: "corte as respirações melhores")
# A pausa curta e a respiração saem; a palavra nunca. Quem decide onde há fala é o Silero VAD (treinado pra separar
# fala de respiro e ruído), a cada 32 ms. O fim da palavra de antes é medido na energia (a cauda de "-ção" é baixa e o
# VAD às vezes a perde); o começo da próxima ganha folga, porque o VAD atrasa o ataque de "s", "f" e "ch".
# E nenhum corte encosta numa palavra do Whisper.
VAD_FR = 512 / SR
_VAD = {}


def _vad(src):
    if src not in _VAD:
        p = os.path.join(fontes.DADOS, "vad", fontes.chave(src) + ".npy")   # no git: poupa o torch de quem só renderiza
        if not os.path.exists(p):
            import torch
            from silero_vad import load_silero_vad
            m = load_silero_vad()
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", fontes.caminho(src), "-map", "0:a:0", "-ac", "1",
                                  "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
            x = torch.from_numpy(np.frombuffer(raw, np.float32).copy())
            with torch.no_grad():
                pr = [m(x[i:i + 512], SR).item() for i in range(0, len(x) - 512, 512)]
            os.makedirs(os.path.dirname(p), exist_ok=True)
            np.save(p, np.array(pr, np.float32))
        _VAD[src] = np.load(p)
    return _VAD[src]


def fala_vad(src, liga=0.5, desliga=0.3):
    """máscara de fala por quadro de 32 ms, com histerese (liga acima de `liga`, só desliga abaixo de `desliga`)"""
    pr = _vad(src)
    m = np.zeros(len(pr), bool)
    on = False
    for i, p in enumerate(pr):
        on = p > liga if not on else p > desliga
        m[i] = on
    return m


CAUDA = 0.07     # silêncio que fica depois do fim medido da palavra
ATAQUE = 0.08    # silêncio que fica antes do ataque medido da próxima ("s", "f" e "h" começam baixinho)
FRASE = 0.12     # a mais depois de ponto final ou interrogação: o raciocínio respira entre uma frase e outra
CORTE_MIN = 0.12 # tirar menos que isso só cria um pulo de imagem sem ganho de ritmo


def _som(src, i0, i1):
    """quadros de 10 ms com som de fala em [i0, i1): voz 9 dB ou chiado do S 12 dB acima do fundo local
    (percentil 10 em ±3 s, recalculado a cada meio segundo: o barulho da festa muda o tempo todo)"""
    v, s = _audio(src)
    out = np.zeros(max(i1 - i0, 0), bool)
    for c in range(i0, i1, 50):
        j0, j1 = max(c - 300, 0), min(c + 350, len(v))
        fv, fs = np.percentile(v[j0:j1], 10), np.percentile(s[j0:j1], 10)
        e = min(c + 50, i1)
        out[c - i0:e - i0] = (v[c:e] > fv + 9) | (s[c:e] > fs + 12)
    return out


def pedacos_vad(src, a, b):
    """[(ini, fim)] dentro de [a, b] sem respiração nem pausa: entre duas palavras fica CAUDA + ATAQUE de silêncio.
    O vão é medido na energia contra o fundo local; o Silero (fala_vad) confirma que ali não tem fala
    quando o vão é longo, e palavra do Whisper inteira dentro do corte barra o corte."""
    i0, i1 = int(a * 100), int(b * 100)
    som = _som(src, i0, i1)
    tr = fontes.transcricao()
    palavras = [(w["start"], w["end"], w["word"]) for s_ in tr.get(fontes.chave(src), [])
                for w in s_.get("words", []) if w["end"] >= a and w["start"] <= b]
    vad = fala_vad(src)
    cortes, k = [], 0
    while k < len(som):
        if som[k]:
            k += 1; continue
        j = k
        while j < len(som) and not som[j]:
            j += 1
        if k > 0 and j < len(som):
            g0, g1 = (i0 + k) / 100, (i0 + j) / 100
            antes = [w for w in palavras if w[1] <= g0 + 0.20]
            ca = g0 + CAUDA + (FRASE if antes and antes[-1][2].strip()[-1:] in ".?!" else 0)
            cb = g1 - ATAQUE
            perdida = any(ca + 0.05 < w0 and w1 < cb - 0.05 and w1 - w0 > 0.12 for w0, w1, _ in palavras)
            # vão longo com o VAD ligado do começo ao fim = fala baixinha que a energia não pegou
            kv0, kv1 = int((g0 + 0.15) / VAD_FR), int((g1 - 0.15) / VAD_FR)
            falando = g1 - g0 > 0.5 and kv1 > kv0 and vad[kv0:kv1].all()
            if cb - ca >= CORTE_MIN and not perdida and not falando:
                cortes.append((ca, cb))
        k = j
    out, pos = [], a
    for ca, cb in cortes:
        out.append((pos, ca)); pos = cb
    out.append((pos, b))
    return [(x, y) for x, y in out if y - x > 0.08]
