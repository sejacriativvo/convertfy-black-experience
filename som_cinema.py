"""som_cinema.py: os sons sintetizados do vídeo (sem direito autoral nem crédito) e os efeitos de DJ sobre a música.

Instrumentos copiados do pitch (criativvo/.../pitch-matheus/_gerador/trilha.py), que é o método da skill
trilha-cinematografica adaptado pra vídeo narrado: golpe tonal no médio, riser com pico no último quadro, sub de
impacto, whoosh varrendo. Somados aqui:
  drone(nota, dur)          cama no tom (cordas graves abafadas), pra atravessar a intro do começo ao fim
  tape_stop(x, dur)         a música freando como fita: o corte cômico ("parou tudo")
  abre(x, f0, f1)           passa-baixas varrendo de f0 a f1 Hz: a parte que entra chega abafada e abre no tempo forte
Tudo em 48 kHz, estéreo (n, 2) quando a função devolve estéreo; mono quando o nome não diz o contrário.
"""
import numpy as np
from scipy import signal

SR = 48000
RNG = np.random.default_rng(7)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "lowpass", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "highpass", fs=SR, output="sos"), x)


def st(x, pan=0.0):
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1)


def _ir(seg=4.0, cor=5000):
    n = int(seg * SR)
    ir = RNG.standard_normal((n, 2)) * env_exp(n, seg / 6.0)[:, None]
    ir = np.stack([lp(ir[:, 0], cor), lp(ir[:, 1], cor)], 1)
    ir[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
    return ir / np.sqrt(np.sum(ir ** 2))


IR_SALA = _ir(4.0)          # sala de concerto de 4 s (a regra da skill pra voz cantada)


def reverb(x, mix=0.4, predelay=0.02):
    if x.ndim == 1:
        x = st(x)
    pd = int(predelay * SR)
    w = np.stack([signal.fftconvolve(x[:, c], IR_SALA[:, c])[: len(x)] for c in range(2)], 1)
    w = np.vstack([np.zeros((pd, 2)), w[:len(w) - pd]])
    return x * (1 - mix) + w * mix * 1.4


def piano(nota, dur=2.4, vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR; f0 = hz(nota); x = np.zeros(n)
    for k in range(1, 12):
        fk = f0 * k * np.sqrt(1 + 0.0004 * k * k)
        if fk > 9000:
            break
        x += (0.6 ** (k - 1)) * np.sin(2 * np.pi * fk * t + RNG.random() * 6) * env_exp(n, dur / (1.2 + 0.7 * k))
    ataque = int(0.004 * SR); x[:ataque] *= np.linspace(0, 1, ataque)
    x += lp(RNG.standard_normal(n), 2500) * env_exp(n, 0.012) * 0.15
    return lp(x, 3200) * vel


def golpe(nota, dur=2.0):
    """ping tonal no médio: passa-altas 150 Hz e passa-baixas 2,2 kHz (com sub ele embola)"""
    x = piano(nota, dur); y = piano(nota + 12, dur * 0.7); x[:len(y)] += 0.5 * y
    return lp(hp(x, 150), 2200)


def sub_boom(dur=1.4, f0=110, f1=38):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.08)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.35)


def ruido_rosa(n):
    w = RNG.standard_normal(n)
    b, a = [0.049922035, -0.095993537, 0.050612699, -0.004408786], [1, -2.494956002, 2.017265875, -0.522189400]
    return signal.lfilter(b, a, w) * 6


def whoosh(dur=0.42, f_ini=350, f_pico=2600, pan0=-0.6, pan1=0.6):
    n = int(dur * SR); x = ruido_rosa(n); out = np.zeros(n); bl = 512
    for i in range(0, n, bl):
        p = i / n; fc = f_ini + (f_pico - f_ini) * np.sin(np.pi * min(p * 1.1, 1)) ** 1.5
        seg = bp(x[max(0, i - 2048):i + bl], fc * 0.6, min(fc * 1.6, 20000))[-(min(bl, n - i)):]
        out[i:i + len(seg)] = seg
    out *= np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    a = (np.linspace(pan0, pan1, n) + 1) * np.pi / 4
    return np.stack([out * np.cos(a), out * np.sin(a)], 1)


def riser(dur=2.6):
    """ruído abrindo até o pico no último quadro (sem tom próprio: em cima de música de verdade, desafinaria)"""
    n = int(dur * SR); p = np.arange(n) / n
    ruido = ruido_rosa(n); out = np.zeros(n); bl = 1024
    for i in range(0, n, bl):
        fc = 300 + 7000 * (i / n) ** 2.2
        seg = bp(ruido[max(0, i - 4096):i + bl], fc * 0.5, min(fc * 1.8, 20000))[-(min(bl, n - i)):]
        out[i:i + len(seg)] = seg
    x = out * p ** 2.4
    x[-int(0.012 * SR):] *= np.linspace(1, 0, int(0.012 * SR))
    return x


def drone(notas, dur, abre=4.0):
    """cama no tom: serras levemente desafinadas, abafadas em 700 Hz, entrando em `abre` segundos"""
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for m in notas:
        for dt in (-0.07, 0.0, 0.06):
            f = hz(m) * 2 ** (dt / 12)
            ph = 2 * np.pi * f * t + RNG.random() * 6
            x += signal.sawtooth(ph) * 0.3
    x = lp(lp(x, 700), 900)
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.11 * t)
    x *= lfo * np.clip(t / abre, 0, 1) ** 1.5
    return x / (np.max(np.abs(x)) or 1)


def tape_stop(x, dur=0.55):
    """a música freando como fita: a velocidade cai de 1 a 0 em `dur` segundos (o tom desce junto)"""
    n = int(dur * SR)
    vel = np.linspace(1, 0, n) ** 1.6
    pos = np.cumsum(vel)
    src = x[: int(pos[-1]) + 2]
    i0 = np.floor(pos).astype(int); fr = (pos - i0)[:, None] if x.ndim == 2 else pos - i0
    i0 = np.clip(i0, 0, len(src) - 2)
    y = src[i0] * (1 - fr) + src[i0 + 1] * fr
    fade = np.linspace(1, 0, n) ** 0.5
    return y * (fade[:, None] if x.ndim == 2 else fade)


def abre(x, f0, f1, curva=2.0):
    """passa-baixas que varre de f0 a f1 Hz ao longo de x (em blocos de 20 ms, sem clique)"""
    n = len(x); bl = int(0.02 * SR); out = np.zeros_like(x)
    zi = None
    for i in range(0, n, bl):
        p = (i / max(n - 1, 1)) ** curva
        fc = f0 * (f1 / f0) ** p
        sos = signal.butter(2, min(fc, SR / 2 - 100), "lowpass", fs=SR, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2, x.shape[1])) if x.ndim == 2 else np.zeros((sos.shape[0], 2))
        out[i:i + bl], zi = signal.sosfilt(sos, x[i:i + bl], axis=0, zi=zi)
    return out
