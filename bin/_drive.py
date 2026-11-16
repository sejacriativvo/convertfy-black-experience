"""O Drive do projeto pelo rclone: a pasta "Convertfy · Black Experience (edição)", com bruto/ e render/ dentro.

Cada máquina entra com a própria conta Google pelo remote `convertfy:` do rclone (bin/instalar.sh cria). Se existir
~/.config/convertfy-black-experience/rclone-env (executável que imprime RCLONE_CONFIG_CONVERTFY_*=...), ele vale no
lugar do remote salvo: é como o Mac do Matheus usa o token da Criativvo.
"""
import os, sys, json, subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
MIDIA = os.path.join(REPO, "midia.json")
PASTA = "1RkGZTTGUiUtwuPBUnYUWd_a9r1V7RNXj"   # Convertfy · Black Experience (edição), no Drive da Criativvo
LINK = f"https://drive.google.com/drive/folders/{PASTA}"
_ENV_LOCAL = os.path.expanduser("~/.config/convertfy-black-experience/rclone-env")


def _env():
    env = dict(os.environ)
    if os.access(_ENV_LOCAL, os.X_OK):
        for ln in subprocess.run([_ENV_LOCAL], capture_output=True, text=True, check=True).stdout.splitlines():
            k, _, v = ln.partition("=")
            env[k] = v
    return env


def rclone(*args, captura=False):
    cmd = ["rclone", *args, "--drive-root-folder-id", PASTA]
    r = subprocess.run(cmd, env=_env(), capture_output=captura, text=True)
    if r.returncode:
        raise RuntimeError(f"rclone {' '.join(args[:2])} falhou" + (f": {r.stderr.strip()[-400:]}" if captura else ""))
    return r.stdout if captura else None


def pronto():
    """o rclone existe e tem como entrar no Drive"""
    try:
        subprocess.run(["rclone", "version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    if os.access(_ENV_LOCAL, os.X_OK):
        return True
    return "convertfy:" in subprocess.run(["rclone", "listremotes"], capture_output=True, text=True).stdout.split()


def lista():
    """{caminho no Drive: dict(id, tamanho, md5)} de tudo que está na pasta do projeto"""
    out = {}
    for f in json.loads(rclone("lsjson", "-R", "--files-only", "--hash", "--hash-type", "md5", "convertfy:", captura=True)):
        out[f["Path"]] = dict(id=f.get("ID"), tamanho=f["Size"], md5=(f.get("Hashes") or {}).get("md5"))
    return out


def le_midia():
    return json.load(open(MIDIA)) if os.path.exists(MIDIA) else dict(drive=dict(pasta=PASTA, link=LINK), bruto={}, render={})


def fontes_do_roteiro():
    """as fontes que a linha do tempo do filme usa (dados/linha.json, gravada pelo yt.py), como caminho dentro de bruto/"""
    import fontes
    L = json.load(open(os.path.join(REPO, "dados", "linha.json")))
    srcs = {q["src"] for _, _, q in L["V"] if "src" in q} | {a[0] for a in L["A"]}
    return sorted({fontes.relativo_bruto(s) for s in srcs})
