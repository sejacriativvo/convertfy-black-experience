"""triagem.py: folha de triagem, uma linha por clipe com k quadros, pra olhar dezenas de clipes de uma vez.

    python triagem.py nome-da-folha arquivo1 arquivo2 ...   -> folhas/triagem-<nome>-N.jpg (12 clipes por folha)

breno.* (FX30 em S-Log3) passa pela LUT; drone e celular vão como estão. Cada quadro leva o nome curto e o segundo.
"""
import os, sys, io, subprocess
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
import fontes
LUT = fontes.LUT_SLOG
OUT = os.path.join(AQUI, "cache", "folhas")
K, LARG, POR_FOLHA = 5, 384, 12
FONTE = ImageFont.truetype(fontes.tipo("Inter-Bold.otf"), 17)


def dur(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True).stdout or 0)


def quadro(f, t):
    vf = f"scale={LARG}:{LARG * 9 // 16}:force_original_aspect_ratio=decrease,pad={LARG}:{LARG * 9 // 16}:(ow-iw)/2:(oh-ih)/2"
    if os.path.basename(f).startswith("breno."):
        vf += f",lut3d=file='{LUT}'"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", f, "-frames:v", "1", "-vf", vf,
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    try:
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        return Image.new("RGB", (LARG, LARG * 9 // 16))


def linha(f):
    d = dur(f)
    ts = [d * (i + 0.5) / K for i in range(K)]
    nome = os.path.basename(f).replace("breno.", "").rsplit(".", 1)[0]
    ims = []
    for t in ts:
        im = quadro(f, t)
        dr = ImageDraw.Draw(im)
        dr.rectangle([0, 0, 150, 24], fill=(0, 0, 0))
        dr.text((5, 2), f"{nome} {t:.0f}/{d:.0f}s", font=FONTE, fill=(255, 230, 0))
        ims.append(im)
    return ims


if __name__ == "__main__":
    nome, arqs = sys.argv[1], sys.argv[2:]
    os.makedirs(OUT, exist_ok=True)
    with ThreadPoolExecutor(6) as ex:
        linhas = list(ex.map(linha, arqs))
    h = LARG * 9 // 16
    for n0 in range(0, len(linhas), POR_FOLHA):
        bloco = linhas[n0:n0 + POR_FOLHA]
        folha = Image.new("RGB", (LARG * K, h * len(bloco)))
        for r, ims in enumerate(bloco):
            for c, im in enumerate(ims):
                folha.paste(im, (c * LARG, r * h))
        p = os.path.join(OUT, f"triagem-{nome}-{n0 // POR_FOLHA + 1}.jpg")
        folha.save(p, quality=78)
        print(p, flush=True)
