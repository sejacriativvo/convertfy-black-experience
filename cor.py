"""cor_de(arquivo): o filtro de cor de um arquivo do bruto, o mesmo do vídeo pronto (fontes.cor). O enquadra.py
extrai os quadros já nessa cor, então o Vision acha os rostos na imagem que vai pra tela."""
import fontes


def cor_de(fonte):
    return fontes.cor(fontes.src_de(fonte))
