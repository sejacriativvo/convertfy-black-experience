# CLAUDE.md: filme do Black Experience (Convertfy)

O filme dos dois dias do Black Experience (11 e 12/11/2026), o evento em que o Bruno recebeu os 30 maiores clientes da Convertfy em casa, pro canal da Convertfy no YouTube. Horizontal 16:9, 29,97 qps, 23 min 24 s. Editado por script: o roteiro é código, o vídeo sai do motor.

Quem mexe: o Matheus (Criativvo) e o Bruno (Convertfy), cada um com o próprio Claude, os dois neste repositório.

## Antes de mexer

1. `git pull`. O outro lado pode ter mudado o roteiro.
2. `python3 bin/baixar.py` se o roteiro passou a usar clipe que você ainda não tem (ele só baixa o que falta).
3. Ler o topo do `linha_yt.py`: lá está o formato do roteiro e o histórico de cada revisão, com o porquê.

## Onde está cada coisa

| O quê | Onde |
|---|---|
| Roteiro (a ordem, os tempos, as músicas, os letreiros) | `linha_yt.py`: `ROTEIRO` e `TRILHAS` |
| Motor (imagem, som, letreiro, montagem) | `yt.py`; letreiros em `cards.py` e `insight.py`; som de cinema em `som_cinema.py` |
| Fontes de vídeo (chave → arquivo, cor de cada câmera) | `fontes.py` |
| Respiração e emenda | `respiros.py` |
| Enquadramento pelos rostos (Vision do macOS) | `enquadra.py`, `ferramentas/pessoas` |
| Transcrição palavra a palavra (Whisper large-v3) | `dados/transcricao.json`, `dados/transcricao-mini-cooper/`; `palavras.py` mostra |
| Linha do tempo do filme montado | `dados/linha.json` (o yt.py grava a cada montagem inteira) |
| Rostos, respiração e análises já medidas | `dados/rostos/`, `dados/vad/`, `dados/analise/` (drone, nitidez, tremor) |
| Música, efeitos, marca, LUTs, fontes tipográficas | `musica/`, `sfx/`, `marca/`, `luts/`, `tipografia/` |
| Bruto (câmeras) | `bruto/`, fora do git. Mora no Drive, índice em `midia.json` |
| Vídeo pronto | `render/`, fora do git. Vai pro Drive sozinho |
| Cache (pedaços renderizados, letreiros em PNG) | `cache/`, fora do git, regenerável |

Chaves de fonte no roteiro: `1196` = `bruto/fx30/breno.1196.MP4` (Sony FX30, S-Log3, 4K 59,94p; dia 11 vai até 1317, dia 12 de 1318 a 1420), `"d477"` = drone, `"o11"`/`"o12"` = Osmo da entrega do Mini Cooper (o mesmo Osmo em arquivos seguidos, o12 = o11 − 242 s), `"cel"` = iPhone da entrega (o som vem do Osmo, `fontes.sync_cel`).

## Comandos

Tudo de dentro da pasta, com o Python do projeto (`.venv`, criado pelo `bin/instalar.sh`):

```sh
SO_LINHA=1 .venv/bin/python yt.py                  # só monta a linha do tempo e confere duração (segundos)
DE=kart ATE=placar .venv/bin/python yt.py          # teste de um trecho, entre duas marcas -> cache/teste.mp4
ESC=1 caffeinate -i .venv/bin/python yt.py         # filme inteiro em 1080p -> render/black-experience-1080p.mp4
ESC=2 caffeinate -i .venv/bin/python yt.py         # filme inteiro em 4K, a entrega -> render/black-experience-4k.mp4
.venv/bin/python palavras.py 1389 140 160          # palavras com o tempo, pra achar o ponto do corte
```

O primeiro render numa máquina nova refaz o cache inteiro (horas). Depois só o que mudou renderiza de novo.

## Conferência, sempre, antes de dizer que está pronto

1. `.venv/bin/python sync.py`: imagem no quadro certo contra o som. Tem que dar **0 fora do quadro**.
2. `.venv/bin/python emendas_final.py`: voz colada no corte, no vídeo pronto. Emenda suspeita se confere ouvindo, e o que o som não decide vai em `fixos=[...]` no ponto mais baixo entre as duas palavras.
3. Quadro repetido: diferença entre quadros seguidos perto de zero com movimento em volta é travada. Só a cartela final pode ter quadro parado.
4. Abrir os pontos mexidos e olhar: texto fora do rosto, nome inteiro sublinhado, nada cortado.

## Regras de edição (o que já foi decidido, com o porquê no topo do linha_yt.py)

**Ritmo e estrutura**
- O objetivo é retenção: ninguém pode pensar em pular 10 segundos. Referências: "G4 Valley: Por Trás do Palco | O FILME" e MrBeast.
- Abre com drone e cinema: corte rápido, frase forte por cima, a voz do cantor com reverb até o drop na logo.
- Laço aberto no começo, pago depois (o champanhe de quem mais faturar, o Mini Cooper, o kart). Pode quebrar a cronologia se uma fala deixa claro onde estamos.
- Conteúdo intercalado com momento divertido. No máximo duas entrevistas de expectativa seguidas, sempre com resenha no meio. Nunca dois minutos de entrevista seguidos.
- A história emocional vai inteira e na ordem real (a entrega do Mini Cooper), sem cortar pra outro assunto.
- Equilíbrio entre os dois dias.

**Fala e corte**
- Corte só em fim de raciocínio: a fala termina onde a ideia fecha, nunca no número solto antes da conclusão. Nunca tirar a pergunta cuja resposta fica.
- Respiração sai (fica ~0,15 s entre palavras), palavra nunca. Emenda cai em silêncio de verdade, não no ponto mais baixo.
- Conversa gravada só no microfone da câmera não entra com voz (logprob do Whisper pior que −0,33).
- Erro de gravação ("corta essa parte aí", "vou repetir") e a pergunta de quem filma ("você é de onde?") não entram.
- Corte em J: na troca de cena a voz nova entra 0,8 a 1,2 s antes da cara, por cima do último apoio ou drone (nunca de outra pessoa falando). O clipe de antes precisa ter esse tanto de imagem sobrando (`j=` no bloco).

**Imagem**
- Enquadramento igual em toda fala: rosto do mesmo tamanho, olhos a 36% da altura, âncora fixa por bloco.
- Apoio = gente de perto conversando e rindo, só onde ilustra o que é dito. Nada de comida (mosca), chão de piscina, céu estourado.
- Drone escolhido pelo movimento (afastamento, perseguição, passagem lateral, órbita), nunca parado no ar.
- Câmera lenta só no que foi gravado a 60p.
- Take tremido sai, não se conserta. **Nada de estabilizador automático**: o deshake girava o quadro com gente passando e a logo parada por cima denunciava. Zoom digital em imagem de mão no máximo 1,10.
- As câmeras Sony nascem com ~0,4 s de imagem parada: nunca começar plano no quadro 0.
- Em cena de ação, garimpar o clipe inteiro atrás do pico (a bicicleta no futevôlei), não pegar o primeiro trecho limpo.

**Texto na tela**
- Nunca em cima do rosto. Entra e sai animado, desliza devagar (parado parece travado), termina dentro da cena da pessoa.
- Nome + o que a pessoa faz: só o que é dito no vídeo, nada inventado. Fica 4 a 6 s na tela.
- Quem é citado e está no quadro ganha nome, papel, barrinha de contexto e seta que segue a pessoa (`destaque=` no bloco, como o Rick).
- Glossário pra palavra difícil: 2 s + 0,3 s por palavra (5 a 9 s). Número na tela no mínimo 2 s.
- QR no formato L: vídeo encolhe pro canto, QR grande, chamada em negrito + itálico serifado, com a cara da Convertfy.
- Sem travessão em texto de tela; vírgula ou frase nova.

**Som**
- Música por momento, escolhida por quem pede: "Can't Tell Me Nothing" na abertura e na noite, "Die With A Smile" no Mini Cooper, "Lovely Day" no dia 2, "Bandoleros" no kart. Silêncio onde a emoção é o som (a porta abrindo).
- A música bate no pico da reação (o primeiro grito) e fica alta ali. No resto, a voz manda: trilha 13 dB abaixo da fala com ducking, mix em −14 LUFS.
- As músicas são comerciais: no YouTube podem cair no Content ID (anúncio pro dono da música ou bloqueio em algum país).

## Armadilhas técnicas que já custaram caro

- Pedaços com cor diferente entrando no concat do ffmpeg engolem quadro na troca e o som descola. O motor já trata (`-reinit_filter 0`, tudo marcado bt709, `setpts=PTS-STARTPTS`); não tirar.
- `-hwaccel videotoolbox` falha calado no H.264 da FX30 e repete quadro. A FX30 decodifica no processador; o decodificador do Mac só pro HEVC e drone.
- Clipe de 24/25p num vídeo de 29,97 repete quadro: apoio com movimento usa `minterpolate`.
- Pedaço que pede imagem além do fim do arquivo congela o último quadro. O motor puxa o começo pra trás; o J recusa clipe curto.

## Exportação automática (não fazer na mão)

No fim de cada resposta do Claude, o hook `Stop` (`.claude/settings.json` → `bin/exportar-hook.sh`) roda o `bin/exportar.py` em segundo plano:
- clipe novo que o roteiro passou a usar sobe pro `bruto/` do Drive;
- vídeo novo em `render/` sobe pro `render/` do Drive, no mesmo arquivo (o link não muda);
- `midia.json` é refeito e tudo que mudou vira commit, com `pull --rebase` e `push` pro GitHub.

Se falhar (conflito com o que o outro lado subiu, Drive sem acesso), aparece um aviso no próximo fim de resposta e o detalhe fica em `.exportar/log.txt`. Conflito se resolve juntando as duas versões, nunca descartando a do outro. Pra exportar na hora: `python3 bin/exportar.py`.

Versão nova substitui a velha: mesmo arquivo, mesmo nome. Nada de `-v2`; o histórico é o git.
