"""fontes.py: de onde vem cada pedaço do vídeo. A chave de fonte que o roteiro usa:

    int NNNN       bruto/fx30/breno.NNNN.MP4: FX30 em S-Log3, dia 11 (1168-1317) e dia 12 (1318-1420)
    "d477"         bruto/drone/DJI_0477.MP4: drone, Rec.709 de fábrica, 29,97p, sem som
    "o11", "o12"   bruto/mini-cooper/osmo/: Osmo Pocket 4 da entrega do Mini Cooper (D-Log, 25p); o som é a lapela do Bruno
    "cel"          bruto/mini-cooper/IMG_0669.MOV: iPhone da entrega (HLG, 30p), imagem de frente, o som vem do Osmo (sync_cel)
    "g:NOME"       bruto/mini-cooper/iphone-geovanna/NOME.MOV: iPhone que filmou a tarde do dia 11

O bruto não vai pro git (o maior clipe tem 16 GB): mora no Drive e o bin/baixar.py traz pra bruto/ (midia.json).

chave(src) é o nome na transcricao.json; cor(src) leva qualquer fonte a Rec.709 com o mesmo acabamento.
"""
import os, subprocess, functools

REPO = os.path.dirname(os.path.abspath(__file__))
BRUTO = os.path.join(REPO, "bruto")
DADOS = os.path.join(REPO, "dados")
LUT_SLOG = os.path.join(REPO, "luts", "SLog3_SGamut3Cine_to_Rec709.cube")
LUT_DLOG = os.path.join(REPO, "luts", "DJI_Pocket4_DLog_to_Rec709_V1.0.cube")
OSMO = {11: "DJI_20261111140731_0011_D.MP4", 12: "DJI_20261111141133_0012_D.MP4"}

# acabamento único: contraste leve, pele sem esverdear (o mesmo do corte aprovado da FX30)
LOOK = "curves=master='0/0.02 0.25/0.24 0.5/0.51 0.75/0.77 1/0.97',eq=saturation=0.84"
# o drone já sai saturado e com contraste de fábrica: só aproxima do resto
# com as altas luzes seguradas: o céu do fim de tarde no kart estourava (15/11, "tem muito sol")
LOOK_DRONE = "curves=master='0/0.03 0.5/0.48 0.85/0.80 1/0.92',eq=saturation=0.9"
# o Osmo e o iPhone da entrega levam o look quente aprovado nos stories (rosa do carro vivo sem estourar), um terço de
# ponto mais baixo e com o branco rolando devagar: o dia nublado deixava o quadro lavado (15/11, "tem muito sol")
LOOK_MINI = ("curves=master='0/0.02 0.25/0.215 0.5/0.465 0.75/0.69 0.9/0.81 1/0.90',"
             "colorbalance=rs=0.02:bs=-0.01:rm=0.035:gm=0.005:bm=-0.03:rh=0.02:bh=-0.025,eq=saturation=1.05")
HLG = "colorspace=all=bt709:iall=bt2020:itrc=bt2020-10:fast=0:format=yuv420p10"


def relativo_bruto(src):
    if isinstance(src, int):
        return f"fx30/breno.{src}.MP4"
    if src.startswith("d"):
        return f"drone/DJI_0{src[1:]}.MP4"
    if src.startswith("o"):
        return f"mini-cooper/osmo/{OSMO[int(src[1:])]}"
    if src == "cel":
        return "mini-cooper/IMG_0669.MOV"
    if src.startswith("g:"):
        return f"mini-cooper/iphone-geovanna/{src[2:]}.MOV"
    raise SystemExit(f"fonte desconhecida: {src}")


def caminho(src):
    arq = os.path.join(BRUTO, relativo_bruto(src))
    if not os.path.exists(arq):
        raise SystemExit(f"falta o bruto {arq}: rode bin/baixar.py (ele traz do Drive o que o roteiro usa)")
    return arq


def src_de(arq):
    """o contrário de caminho(): a chave da fonte a partir do arquivo"""
    nome, pasta = os.path.basename(arq), os.path.basename(os.path.dirname(arq))
    if nome.startswith("breno."):
        return int(nome.split(".")[1])
    if pasta == "drone":
        return "d" + nome[5:8]
    if pasta == "osmo":
        return "o" + str(int(nome.split("_")[2]))
    if nome == "IMG_0669.MOV":
        return "cel"
    if pasta == "iphone-geovanna":
        return "g:" + nome.rsplit(".", 1)[0]
    raise SystemExit(f"arquivo fora do bruto: {arq}")


def relativo(s):
    """tira a pasta do repositório de um caminho ou filtro: as chaves de cache valem em qualquer máquina"""
    return s.replace(REPO + os.sep, "")


def tipo(nome):
    """arquivo de fonte tipográfica: tipografia/ do repositório ou, se não estiver lá, as instaladas no Mac"""
    for p in (os.path.join(REPO, "tipografia", nome), os.path.expanduser(f"~/Library/Fonts/{nome}")):
        if os.path.exists(p):
            return p
    raise SystemExit(f"falta a fonte {nome}: instalar no Mac (a Gilroy é paga e não vai no repositório)")


def chave(src):
    return f"breno.{src}" if isinstance(src, int) else str(src)


@functools.lru_cache(None)
def _probe(src):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=codec_name,width,height,r_frame_rate,color_transfer:format=duration", "-of", "json", caminho(src)],
                       capture_output=True, text=True).stdout
    import json
    j = json.loads(r)
    s = j["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return dict(w=s["width"], h=s["height"], fps=float(n) / float(d), trc=s.get("color_transfer", ""),
                dur=float(j["format"]["duration"]), codec=s.get("codec_name", ""))


def dims(src):
    p = _probe(src)
    return p["w"], p["h"]


def fps(src):
    return _probe(src)["fps"]


def dur(src):
    return _probe(src)["dur"]


def flags(src):
    """o iPhone marca rotação, mas o quadro cru da entrega já está deitado (conferido nos stories)"""
    return ["-noautorotate"] if src == "cel" else []


def cor(src):
    if isinstance(src, int):
        return f"lut3d=file='{LUT_SLOG}':interp=tetrahedral,{LOOK}"
    if src.startswith("d"):
        return LOOK_DRONE
    if src.startswith("o"):
        return f"lut3d=file='{LUT_DLOG}':interp=tetrahedral,{LOOK_MINI}"
    if src == "cel" or _probe(src)["trc"] in ("arib-std-b67", "smpte2084"):
        return f"{HLG},{LOOK_MINI}"
    return LOOK_MINI


def sync_cel(t_cel):
    """tempo no Osmo 0011 = tempo no iPhone + isto (duas sincronias, medidas nos stories: README da pasta)"""
    return 44.22 if t_cel < 85 else 48.73


_TR = None


def transcricao():
    """dados/transcricao.json (Whisper large-v3 de todo o bruto) mais a da entrega do Mini Cooper"""
    global _TR
    if _TR is None:
        import json
        _TR = json.load(open(os.path.join(DADOS, "transcricao.json")))
        for k, f in (("o11", "0011.json"), ("o12", "0012.json"), ("cel", "IMG_0669.json")):
            d = json.load(open(os.path.join(DADOS, "transcricao-mini-cooper", f)))
            _TR[k] = d["segments"] if isinstance(d, dict) else d
    return _TR
