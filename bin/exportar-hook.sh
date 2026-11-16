#!/bin/sh
# Hook Stop do Claude Code: exporta a edição em segundo plano (bin/exportar.py) e, se a exportação anterior falhou,
# mostra o aviso uma vez. Nunca segura a resposta: upload de render demora.
R="$(cd "$(dirname "$0")/.." && pwd)"
[ -d "$R/.git" ] || exit 0
cat > /dev/null
python3 "$R/bin/exportar.py" --aviso
nohup python3 "$R/bin/exportar.py" --hook > /dev/null 2>&1 &
exit 0
