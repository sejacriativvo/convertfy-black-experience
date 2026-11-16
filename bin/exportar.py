#!/usr/bin/env python3
"""Leva o estado da edição pro GitHub e pro Drive. Roda sozinho no fim de cada resposta do Claude (bin/exportar-hook.sh,
hook Stop), em segundo plano. Também roda na mão:

    python3 bin/exportar.py          exporta agora
    python3 bin/exportar.py --aviso  imprime o aviso da última exportação que falhou, uma vez (é o que o hook mostra)

1. Bruto: fonte que o roteiro usa e ainda não está no Drive sobe pra bruto/ (clipe novo que entrou na edição).
2. Render: vídeo novo ou mudado em render/ sobe pro render/ do Drive, no mesmo arquivo (o link não muda).
3. midia.json: o índice do Drive (id, tamanho e md5 de cada arquivo) é refeito quando algo subiu.
4. Git: commit de tudo que mudou, pull --rebase (junta com o que o outro lado subiu) e push.

Quem clonou o repositório público sem ser colaborador só lê o GitHub e o Drive: o commit fica no git do Mac dele, o
render fica em render/, e o aviso aparece uma vez (tenta mandar de novo uma vez por dia, caso o acesso tenha chegado).
"""
import os, sys, json, time, datetime, tempfile, subprocess
import _drive

REPO = _drive.REPO
EST = os.path.join(REPO, ".exportar")
ESTADO = os.path.join(EST, "estado.json")     # tamanho e data de cada render já enviado
ULTIMO = os.path.join(EST, "ultimo.json")     # resultado da última exportação
TRAVA = os.path.join(EST, "trava")
LIMITE = 95 * 2 ** 20                          # o GitHub recusa arquivo acima de 100 MB
SO_LEITURA = ("este Mac só lê o GitHub e o Drive do Matheus: a edição fica salva aqui (git local e render/). "
              "Pra mandar de volta, peça acesso de colaborador ao Matheus.")


def negado(msg):
    return any(k in msg for k in ("403", "ermission", "denied", "insufficient", "could not read Username"))


def le_estado():
    return json.load(open(ESTADO)) if os.path.exists(ESTADO) else {}


def so_leitura(onde, marca=False):
    """sem permissão de escrita no GitHub ou no Drive: marca e pula por um dia"""
    est = le_estado()
    sl = est.setdefault("_so_leitura", {})
    if marca:
        sl[onde] = time.time()
        json.dump(est, open(ESTADO, "w"))
    return time.time() - sl.get(onde, 0) < 86400


def git(*a, ok=False):
    r = subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True)
    if r.returncode and not ok:
        raise RuntimeError(f"git {a[0]}: {(r.stderr or r.stdout).strip()[-300:]}")
    return r


def sobe_lista(pasta, nomes):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("\n".join(nomes) + "\n")
    try:
        _drive.rclone("copy", "-L", os.path.join(REPO, pasta), f"convertfy:{pasta}", "--files-from", f.name,
                      "--transfers", "4", "--drive-chunk-size", "64M", captura=True)
    finally:
        os.remove(f.name)


def drive(log, notas):
    if not _drive.pronto():
        log.append("Drive sem acesso pelo rclone (bin/instalar.sh): só o git foi exportado")
        return
    if so_leitura("drive"):
        return
    try:
        sobe(log)
    except RuntimeError as e:
        if not negado(str(e)):
            raise
        so_leitura("drive", marca=True)
        notas.append(SO_LEITURA)


def sobe(log):
    m = _drive.le_midia()
    subiu = False
    falta = [n for n in _drive.fontes_do_roteiro()
             if n not in m["bruto"] and os.path.exists(os.path.join(REPO, "bruto", n))]
    if falta:                                        # confere no Drive antes: o midia.json pode estar velho
        no_drive = _drive.lista()
        falta = [n for n in falta if f"bruto/{n}" not in no_drive]
        subiu = True
    if falta:
        sobe_lista("bruto", falta)
        log.append(f"bruto: {len(falta)} clipe(s) novo(s) no Drive")
    est = le_estado()
    pasta = os.path.join(REPO, "render")
    for nome in sorted(os.listdir(pasta)) if os.path.isdir(pasta) else []:
        if not nome.endswith(".mp4"):
            continue
        st = os.stat(os.path.join(pasta, nome))
        sig = [st.st_size, int(st.st_mtime)]
        if est.get(nome) != sig:
            _drive.rclone("copyto", os.path.join(pasta, nome), f"convertfy:render/{nome}", "--drive-chunk-size", "64M",
                          captura=True)
            est[nome] = sig
            json.dump(est, open(ESTADO, "w"))
            log.append(f"render: {nome} no Drive")
            subiu = True
    if subiu or not os.path.exists(_drive.MIDIA):
        tudo = _drive.lista()
        m["drive"] = dict(pasta=_drive.PASTA, link=_drive.LINK)
        for parte in ("bruto", "render"):
            m[parte] = {k[len(parte) + 1:]: v for k, v in sorted(tudo.items()) if k.startswith(parte + "/")}
        with open(_drive.MIDIA, "w") as f:
            json.dump(m, f, indent=1, ensure_ascii=False)
            f.write("\n")


def github(log, notas):
    if not os.path.isdir(os.path.join(REPO, ".git")):
        return
    git("add", "-A")
    for nome in filter(None, git("diff", "--cached", "--name-only", "-z").stdout.split("\0")):
        p = os.path.join(REPO, nome)
        if os.path.isfile(p) and os.path.getsize(p) > LIMITE:
            git("reset", "-q", "--", nome)
            log.append(f"{nome} tem mais de 95 MB e ficou fora do git (vídeo mora no Drive, em bruto/ ou render/)")
    if git("diff", "--cached", "--quiet", ok=True).returncode:
        nomes = [n for n in git("diff", "--cached", "--name-only").stdout.split("\n") if n]
        resumo = ", ".join(nomes[:4]) + (f" e mais {len(nomes) - 4}" if len(nomes) > 4 else "")
        git("commit", "-q", "-m", f"Exportação automática: {resumo}")
        log.append(f"commit: {resumo}")
    if not git("remote", ok=True).stdout.strip():
        return
    if git("rev-list", "--count", "@{u}..HEAD", ok=True).stdout.strip() in ("", "0") or so_leitura("git"):
        return
    if git("pull", "-q", "--rebase", ok=True).returncode:
        git("rebase", "--abort", ok=True)
        raise RuntimeError("o GitHub tem mudança do outro lado nos mesmos arquivos. Peça pro Claude: "
                           "\"junta as duas versões do Black Experience\" (git pull --rebase e resolver o conflito)")
    r = subprocess.run(["git", "-C", REPO, "push", "-q"], capture_output=True, text=True,
                       env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    if r.returncode and negado(r.stderr):
        so_leitura("git", marca=True)
        notas.append(SO_LEITURA)
    elif r.returncode:
        raise RuntimeError(f"git push: {r.stderr.strip()[-300:]}")
    else:
        log.append("GitHub atualizado")


def aviso():
    if not os.path.exists(ULTIMO):
        return
    u = json.load(open(ULTIMO))
    if (u.get("ok") and not u.get("notas")) or u.get("avisado"):
        return
    u["avisado"] = True
    json.dump(u, open(ULTIMO, "w"), ensure_ascii=False)
    msg = f"a exportação falhou ({u['quando']}): {u['erro']}" if not u.get("ok") else " ".join(dict.fromkeys(u["notas"]))
    print(json.dumps(dict(systemMessage=f"Black Experience: {msg}"), ensure_ascii=False))


if __name__ == "__main__":
    os.makedirs(EST, exist_ok=True)
    if "--aviso" in sys.argv:
        aviso()
        sys.exit()
    try:
        os.mkdir(TRAVA)
    except FileExistsError:
        if datetime.datetime.now().timestamp() - os.path.getmtime(TRAVA) < 6 * 3600:
            sys.exit()                               # outra exportação em andamento (upload de render demora)
        os.utime(TRAVA)
    log, notas, quando = [], [], datetime.datetime.now().strftime("%d/%m %H:%M")
    try:
        drive(log, notas)
        github(log, notas)
        res = dict(ok=True, quando=quando, feito=log, notas=notas)
    except Exception as e:
        res = dict(ok=False, quando=quando, erro=str(e), feito=log, notas=notas)
    finally:
        os.rmdir(TRAVA)
    json.dump(res, open(ULTIMO, "w"), ensure_ascii=False)
    if log or not res["ok"]:
        with open(os.path.join(EST, "log.txt"), "a") as f:
            f.write(f"{quando} {'ok' if res['ok'] else 'ERRO ' + res['erro']}: {'; '.join(log)}\n")
    if "--hook" not in sys.argv:
        print("\n".join(log + notas) or "nada mudou", "" if res["ok"] else f"\nERRO: {res['erro']}")
