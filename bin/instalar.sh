#!/bin/sh
# Prepara um Mac (Apple Silicon) pra editar o filme: programas, Python, acesso ao Drive e o bruto.
# Rodar uma vez, de dentro da pasta do repositório: sh bin/instalar.sh
set -e
R="$(cd "$(dirname "$0")/.." && pwd)"
cd "$R"

command -v brew > /dev/null || { echo "Instale o Homebrew antes: https://brew.sh"; exit 1; }
for p in ffmpeg rclone python@3.12; do brew list "$p" > /dev/null 2>&1 || brew install "$p"; done

PY="$(brew --prefix python@3.12)/bin/python3.12"
[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/pip install -q -r requirements.txt

# rostos pelo Vision do macOS: o binário vem pronto pra Apple Silicon; se não rodar, compila (precisa do Xcode CLT)
if ! ferramentas/pessoas /tmp > /dev/null 2>&1; then
  xcode-select -p > /dev/null 2>&1 || xcode-select --install
  swiftc -O ferramentas/pessoas.swift -o ferramentas/pessoas
fi

# fonte paga que não vai no repositório
for f in Gilroy-Bold.ttf Gilroy-ExtraBold.ttf Gilroy-SemiBold.ttf; do
  [ -f "$HOME/Library/Fonts/$f" ] || [ -f tipografia/$f ] || echo "AVISO: falta a fonte $f (números na tela). Instale a Gilroy no Mac."
done

# Drive: login da sua conta Google uma vez (abre o navegador). A pasta do projeto precisa estar compartilhada com ela.
if [ ! -x "$HOME/.config/convertfy-black-experience/rclone-env" ] && ! rclone listremotes | grep -qx "convertfy:"; then
  rclone config create convertfy drive scope=drive
fi

python3 bin/baixar.py
echo "pronto: abra o Claude Code nesta pasta e peça a mudança (o CLAUDE.md explica o resto)"
