"""conferir.py video.mp4 saida.jpg t1 t2 ...: folha de quadros nos segundos pedidos (3 por linha)"""
import sys, subprocess, io
from PIL import Image, ImageDraw
v, out, ts = sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3:]]
ims = []
for t in ts:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", v, "-frames:v", "1", "-vf", "scale=640:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    im = Image.open(io.BytesIO(raw)).convert("RGB"); ImageDraw.Draw(im).text((6, 6), f"{t:.1f}s", fill=(255, 255, 0)); ims.append(im)
w, h = ims[0].size
s = Image.new("RGB", (w * 3, h * ((len(ims) + 2) // 3)))
for i, im in enumerate(ims): s.paste(im, ((i % 3) * w, (i // 3) * h))
s.save(out, quality=85)
