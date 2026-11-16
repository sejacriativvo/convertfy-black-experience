#!/usr/bin/env python3
"""Traz do Drive os vídeos que ficam fora do git.

    python3 bin/baixar.py            o bruto que o roteiro usa hoje (dados/linha.json), ~150 GB
    python3 bin/baixar.py --tudo     todo o bruto dos dois dias, drone e Mini Cooper, ~230 GB
    python3 bin/baixar.py --render   os vídeos prontos (render/)

Só baixa o que falta ou está diferente (tamanho e md5 conferidos pelo rclone). Pode parar e rodar de novo.
"""
import os, sys, tempfile
import _drive

REPO = _drive.REPO


def baixa(pasta, nomes, indice):
    """só vai pro rclone o que falta ou tem outro tamanho: arquivo inteiro já no disco nem é lido de novo"""
    def tem(n):
        p = os.path.join(REPO, pasta, n)
        return os.path.exists(p) and os.path.getsize(p) == indice[n]["tamanho"]
    falta = [n for n in nomes if not tem(n)]
    print(f"{pasta}/: {len(nomes)} arquivos, faltam {len(falta)}", flush=True)
    if not falta:
        return
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("\n".join(falta) + "\n")
    try:
        _drive.rclone("copy", "-L", f"convertfy:{pasta}", os.path.join(REPO, pasta), "--files-from", f.name,
                      "--transfers", "4", "--drive-chunk-size", "64M", "-P", "--stats-one-line")
    finally:
        os.remove(f.name)


if __name__ == "__main__":
    if not _drive.pronto():
        sys.exit("o rclone ainda não entra no Drive: rode bin/instalar.sh")
    m = _drive.le_midia()
    if "--render" in sys.argv:
        baixa("render", sorted(m["render"]), m["render"])
    else:
        nomes = sorted(m["bruto"]) if "--tudo" in sys.argv else _drive.fontes_do_roteiro()
        fora = [n for n in nomes if n not in m["bruto"]]
        if fora:
            print(f"AVISO: {len(fora)} arquivo(s) do roteiro não estão no Drive ainda (quem tem o bruto roda bin/exportar.py): {fora[:5]}")
        baixa("bruto", [n for n in nomes if n in m["bruto"]], m["bruto"])
    print("pronto")
