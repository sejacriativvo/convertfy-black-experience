"""palavras.py FONTE INI FIM: cada palavra do trecho com o tempo de começo, pra escrever o roteiro.

    python palavras.py 1235 80 100      python palavras.py o11 140 230

Linha nova a cada vão de 0,35 s ou mais (onde uma emenda cabe), com o tamanho do vão e o logprob do segmento.
"""
import sys
import fontes

src = sys.argv[1]
src = int(src) if src.isdigit() else src
a, b = float(sys.argv[2]), float(sys.argv[3])
T = fontes.transcricao().get(fontes.chave(src), [])
ant, linha, lp = None, "", 0
for s in T:
    for w in s.get("words", []):
        if w["end"] < a or w["start"] > b:
            continue
        if ant is not None and w["start"] - ant >= 0.35:
            print(f"{linha}   [{lp:.2f}]\n   ~ vão {w['start'] - ant:.2f}s")
            linha = ""
        if not linha:
            linha = f"{w['start']:7.2f} |"
        linha += f" {w['word'].strip()}·{w['start']:.2f}"
        ant, lp = w["end"], s.get("avg_logprob", 0)
print(f"{linha}   [{lp:.2f}]   fim {ant}")
