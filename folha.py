"""folha.py NNNN [NNNN ...] -> folhas/NNNN.jpg: 6 quadros do clipe com a LUT, rotulados com o segundo"""
import os, sys, subprocess, json
from PIL import Image, ImageDraw, ImageFont
import fontes
LUT = fontes.LUT_SLOG
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "folhas")
def dur(f):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f],capture_output=True,text=True).stdout)
def folha(n, k=6, larg=480):
    f = fontes.caminho(int(n)); d = dur(f)
    ts = [d * (i + 0.5) / k for i in range(k)]
    ims = []
    for t in ts:
        raw = subprocess.run(["ffmpeg","-v","error","-ss",f"{t:.2f}","-i",f,"-frames:v","1","-vf",
            f"scale={larg}:-2,lut3d=file='{LUT}'","-f","image2pipe","-vcodec","png","-"],capture_output=True).stdout
        im = Image.open(__import__("io").BytesIO(raw)).convert("RGB")
        ImageDraw.Draw(im).text((8,8), f"{n} @{t:.1f}s / {d:.0f}s", fill=(255,255,0))
        ims.append(im)
    w, h = ims[0].size; cols = 3
    sheet = Image.new("RGB", (w*cols, h*((k+cols-1)//cols)))
    for i, im in enumerate(ims): sheet.paste(im, ((i%cols)*w, (i//cols)*h))
    os.makedirs(OUT, exist_ok=True); sheet.save(f"{OUT}/{n}.jpg", quality=80)
for a in sys.argv[1:]: folha(int(a)); print(a, flush=True)
