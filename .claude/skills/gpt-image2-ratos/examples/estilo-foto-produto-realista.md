# Estilo: foto de produto realista (estúdio, sem neon)

Aprovado pelo Matheus em 13/10/2026, nos criativos de checkout da Hezilex
(10 bancas de R$10.000). Referência viva: `~/Matheus Vareschi/hezilex/criativos/10-bancas/`.

Serve pra qualquer peça de venda onde o objeto (dinheiro, produto, prêmio)
precisa parecer REAL e crível, e quem faz o trabalho agressivo é o texto
por cima, não a imagem.

## A regra de ouro

**A imagem é calma e crível. A agressividade vem da tipografia.**
Imagem com fogo, faísca, neon ou quantidade impossível parece golpe e foi
reprovada duas vezes. Foto de estúdio limpa com o objeto na quantidade
real foi aprovada de primeira.

## DNA do prompt (em inglês)

```
Professional commercial product photograph, shot on a medium-format camera,
80mm lens, f/8, crisp focus, true-to-life colors.
[OBJETO, descrito com precisão física: quantidade exata, medidas reais,
material, detalhes de autenticidade. Ex: "Exactly 10 bundles of real
Brazilian 100-reais banknotes (blue-teal, effigy of the Republic,
'100' in the corners), each bundle about 1 cm thick (100 notes), held by a
plain kraft-paper band"]
[ARRANJO crível: "arranged neatly and believably, like [contexto real]"]
on a matte black stone table. Soft white studio key light from the upper
left with a large softbox, gentle shadows, subtle realistic reflections,
dark charcoal background (#181816) falling off to black. Realistic texture,
slight wear, correct real-world proportions. Calm, premium, credible.
Strictly no neon, no glow, no fire, no sparks, no smoke, no orange light,
no colored gels, no lens flare, no people, no extra text, no logos,
no watermark.
```

## Composição: deixar o espaço do texto vazio no próprio prompt

- **Banner horizontal:** `wide horizontal framing 21:9, the subject occupies
  only the RIGHT 45% of the frame, shot from a 35-degree high angle; the LEFT
  55% is empty dark charcoal background for text. Horizontal framing, 21:9.`
- **Vertical 4:5:** `vertical 4:5 framing, camera at a 40-degree high angle,
  the subject fills the LOWER 50% of the frame, centered; the TOP 50% is empty
  dark charcoal background for headline text. Vertical framing, 4:5.`

## Parâmetros

- `quality: high`
- Granulado `4.0` (fundo escuro), nunca no prompt
- Quantidade **real** do que o texto promete (R$100 mil = 10 maços de R$100). Nada de montanha de dinheiro.

## Montagem da peça (HTML + Chrome headless)

- Fundo `#111`, degradê escuro do lado do texto pra emendar com a foto
- Título bold 700, tracking apertado (-0.045em), palavra-chave em cor sólida da marca
- Selo em pílula, botão sólido, "Sujeito ao regulamento" pequeno
- **Proibido:** text-shadow colorido, drop-shadow, box-shadow com cor, gradiente no texto
- Copy do cliente palavra por palavra
- Conferir o PNG final por imagem: texto nunca encostando no objeto
