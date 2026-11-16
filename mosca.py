"""mosca.py NNNN [ini fim]: procura inseto (mancha pequena e escura que se mexe sozinha) num clipe.
Alinha cada par de quadros pelo movimento global (a câmera anda), subtrai, e guarda manchas de 15 a 900 px
(em 1920 de largura) mais escuras que o entorno. Saída: segundos suspeitos + recortes em mosca/NNNN_t.jpg"""
import os, sys, subprocess, json
import numpy as np, cv2
import fontes
LUT = fontes.LUT_SLOG
AQUI = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(AQUI, "cache", "mosca")
W, H, FPS = 1920, 1080, 15

def quadros(n, ini=None, fim=None):
    f = fontes.caminho(int(n))
    cmd = ["ffmpeg", "-v", "error", "-hwaccel", "videotoolbox"]
    if ini is not None: cmd += ["-ss", str(ini), "-t", str(fim - ini)]
    cmd += ["-i", f, "-vf", f"fps={FPS},scale={W}:{H},lut3d=file='{LUT}'", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3: break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)

def analisa(n, ini=None, fim=None):
    os.makedirs(OUT, exist_ok=True)
    ant, achados, i = None, [], 0
    t0 = ini or 0
    for q in quadros(n, ini, fim):
        g = cv2.GaussianBlur(cv2.cvtColor(q, cv2.COLOR_BGR2GRAY).astype(np.float32), (3, 3), 0)
        if ant is not None:
            # alinhamento global (translação + escala/rotação leve)
            try:
                M = cv2.estimateAffinePartial2D(*_pontos(ant, g))[0]
            except Exception:
                M = None
            if M is None: M = np.float32([[1, 0, 0], [0, 1, 0]])
            al = cv2.warpAffine(ant, M, (W, H), borderMode=cv2.BORDER_REPLICATE)
            d = g - al                      # negativo = ficou mais escuro agora (algo escuro chegou)
            # fundo de diferença local (paralaxe, borda): só conta o que destoa da vizinhança
            local = cv2.blur(np.abs(d), (61, 61))
            m = ((d < -28) & (np.abs(d) > 4 * local + 10)).astype(np.uint8)
            m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
            k, lab, st, cen = cv2.connectedComponentsWithStats(m)
            for j in range(1, k):
                a = st[j, 4]; w_, h_ = st[j, 2], st[j, 3]
                if 12 <= a <= 900 and max(w_, h_) <= 60 and max(w_, h_) / max(1, min(w_, h_)) < 4:
                    x, y = cen[j]
                    viz = g[max(0, int(y) - 30):int(y) + 30, max(0, int(x) - 30):int(x) + 30]
                    if g[int(y), int(x)] < np.median(viz) - 25:
                        achados.append((round(t0 + i / FPS, 2), int(x), int(y), int(a)))
        ant = g; i += 1
    # um inseto aparece em vários quadros seguidos, andando: agrupa por tempo
    seq = []
    for t, x, y, a in achados:
        if seq and t - seq[-1][-1][0] <= 0.3 and np.hypot(x - seq[-1][-1][1], y - seq[-1][-1][2]) < 200:
            seq[-1].append((t, x, y, a))
        else:
            seq.append([(t, x, y, a)])
    seq = [s for s in seq if len(s) >= 3]
    return seq

def _pontos(a, b):
    a8, b8 = a.astype(np.uint8), b.astype(np.uint8)
    p0 = cv2.goodFeaturesToTrack(a8, 400, 0.01, 20)
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a8, b8, p0, None)
    ok = st.ravel() == 1
    return p0[ok], p1[ok]

def recortes(n, seq):
    for s in seq:
        t, x, y, a = s[len(s) // 2]
        f = fontes.caminho(int(n))
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", f, "-frames:v", "1", "-vf",
                              f"scale={W}:{H},lut3d=file='{LUT}'", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                             capture_output=True).stdout
        q = np.frombuffer(raw, np.uint8).reshape(H, W, 3).copy()
        x0, y0 = max(0, x - 120), max(0, y - 120)
        c = cv2.resize(q[y0:y0 + 240, x0:x0 + 240], (480, 480), interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(f"{OUT}/{n}_{t:.2f}.jpg", c)

if __name__ == "__main__":
    n = int(sys.argv[1]); ini = float(sys.argv[2]) if len(sys.argv) > 2 else None; fim = float(sys.argv[3]) if len(sys.argv) > 3 else None
    seq = analisa(n, ini, fim)
    recortes(n, seq)
    print(json.dumps({"clipe": n, "suspeitas": [[s[0][0], s[-1][0], s[0][1], s[0][2], len(s)] for s in seq]}))
