"""mosaico.py saida.jpg NNNN... : 3 quadros (início, meio, fim) de cada folha numa linha"""
import sys, os
from PIL import Image
F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "folhas")
out, ns = sys.argv[1], sys.argv[2:]
linhas = []
for n in ns:
    s = Image.open(f"{F}/{n}.jpg"); w, h = s.size[0]//3, s.size[1]//2
    q = [s.crop((0,0,w,h)), s.crop((w*2,0,w*3,h)), s.crop((w*2,h,w*3,h*2))]
    l = Image.new("RGB",(w*3,h)); [l.paste(x.resize((w,h)),(i*w,0)) for i,x in enumerate(q)]
    linhas.append(l.resize((w*3*2//3, h*2//3)))
W, H = linhas[0].size
m = Image.new("RGB",(W*2, H*((len(linhas)+1)//2)))
for i,l in enumerate(linhas): m.paste(l,((i%2)*W,(i//2)*H))
m.save(out, quality=78)
