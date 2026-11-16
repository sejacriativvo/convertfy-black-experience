#!/usr/bin/env python3
"""Granulado de filme sutil + leve vinheta. Pos-processamento, nao vai no prompt.

Uso: python3 grain.py entrada.png saida.jpg [amount] [vignette]
     amount   default 6.0  (abaixo de 4 quase nao aparece, acima de 10 fica sujo)
     vignette default 0.10 (0 desliga)
"""
import sys, pathlib
from PIL import Image, ImageFilter
import numpy as np


def grain(src, dst, amount=6.0, softness=0.5, vignette=0.10, seed=7):
    im = Image.open(src).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    h, w, _ = a.shape
    rng = np.random.default_rng(seed)

    # ruido monocromatico (grao de filme e majoritariamente luminancia)
    n = rng.normal(0.0, 1.0, (h, w)).astype(np.float32)
    if softness > 0:
        n = np.asarray(
            Image.fromarray(((n * 40) + 128).clip(0, 255).astype(np.uint8))
            .filter(ImageFilter.GaussianBlur(softness)),
            dtype=np.float32,
        )
        n = (n - 128) / 40.0

    # grao pesa mais nos meios-tons e some nas altas luzes, como filme de verdade
    lum = a.mean(axis=2) / 255.0
    weight = (1.0 - (2.0 * lum - 1.0) ** 2) * 0.75 + 0.25
    a += (n * amount * weight)[:, :, None]

    # vinheta discreta
    if vignette > 0:
        yy, xx = np.mgrid[0:h, 0:w]
        cy, cx = h / 2, w / 2
        r = np.sqrt(((yy - cy) / cy) ** 2 + ((xx - cx) / cx) ** 2) / np.sqrt(2)
        a *= (1.0 - vignette * (r ** 2.2))[:, :, None]

    out = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    pathlib.Path(dst).parent.mkdir(parents=True, exist_ok=True)
    out.save(dst, quality=95, subsampling=0)
    print(f"OK {dst} {out.size}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    src, dst = sys.argv[1], sys.argv[2]
    amt = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
    vig = float(sys.argv[4]) if len(sys.argv) > 4 else 0.10
    grain(src, dst, amount=amt, vignette=vig)
