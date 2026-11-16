---
name: gpt-image2-ratos
description: Gera imagens via gpt-image-2 (OpenAI) usando OAuth do plano ChatGPT do user — sem API key, sem custo direto. Lê ~/.codex/auth.json (login feito uma vez via Codex CLI) e dispara um proxy local openai-oauth que roteia pelo backend Codex. Suporta text-to-image e image-edit (referência em multipart). Toda imagem passa por granulado de filme + vinheta no pós (scripts/grain.py) antes de ser entregue. Setup conversacional do estilo a cada uso. Cerca de 25s por imagem. Use quando o user paga ChatGPT Plus/Pro e não quer cobrar API. Pra iteração rápida ou usuários sem plano pago, usar image-gen-ratos (FAL) ou nanobanana-ratos (Gemini).
---

# gpt-image2-ratos

Skill de geração de imagens via **gpt-image-2** usando **OAuth do plano ChatGPT do user**. Sem API key, sem custo direto — queima limite do plano.

Pra usuários que pagam ChatGPT Plus/Pro/Business/Enterprise. Pra usuários sem plano, redirecionar pra [`/image-gen-ratos`](https://github.com/duduesh/image-gen-ratos) (FAL) ou [`/nanobanana-ratos`](https://github.com/duduesh/nanobanana-ratos) (Gemini).

## Aviso de latência

Cada imagem leva **cerca de 25 segundos** (vs 10-15s no FAL). Eram 60 a 180s até
30/09/2026, quando a imagem ainda era pedida dentro de uma conversa; o endpoint
direto cortou o grosso dessa espera (ver a seção logo abaixo).

Continua valendo avisar antes de gerar uma série: cada imagem queima cota Codex
do plano. Pra 5+ variações de descarte, `image-gen-ratos` (FAL) ainda sai
melhor. Aqui a skill brilha quando é "1 imagem boa final".

## Onde ela roda

Mac, Linux e **Windows**. No Windows tem uma condição: os comandos rodam no **Git Bash**, nunca no Prompt de Comando nem no PowerShell. É o mesmo terminal que o resto do workspace já exige (seção 2c do `COMECE-AQUI.md`), então quem instalou o repositório já tem.

O que muda no Windows, e já está tratado nos comandos abaixo:

| Coisa | Mac / Linux | Windows |
|---|---|---|
| O Python | `python3` | `python` ou `py` |
| Matar o proxy na porta | `lsof` | `netstat` + `taskkill` |

O resto (`curl`, `npx`, `~/.codex/auth.json`, `/tmp`) o Git Bash resolve igual nos dois.

## Setup (primeira vez)

A skill **não tem .env**. Toda a auth vem do `~/.codex/auth.json` que o Codex CLI cria. O fluxo de setup é:

### 1. Verificar pré-requisitos

```bash
test -f ~/.codex/auth.json && echo "OK_AUTH" || echo "NO_AUTH"
command -v node npx >/dev/null && node --version

# O Python não se chama igual nos dois sistemas: no Mac é python3, no Windows
# costuma ser python ou py. Pior: o Windows traz um python3 falso que só abre a
# Microsoft Store, então não basta achar o nome, tem que ver se ele RODA.
PY=""
for c in python3 python py; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" >/dev/null 2>&1; then
    PY="$c"; break
  fi
done
[ -z "$PY" ] && echo "NO_PYTHON" || echo "OK_PYTHON ($PY $("$PY" -c 'import sys;print(".".join(map(str,sys.version_info[:3])))'))"

"$PY" -c "import PIL, numpy" 2>/dev/null && echo "OK_GRAIN_DEPS" || echo "NO_GRAIN_DEPS"
```

Se der `NO_GRAIN_DEPS`, rodar `"$PY" -m pip install --user pillow numpy` (o passo de granulado depende disso).

Se der `NO_PYTHON`, instalar o Python: no Mac `brew install python`, no Windows baixar em [python.org/downloads](https://www.python.org/downloads/) **marcando "Add python.exe to PATH"** na primeira tela do instalador. Sem essa caixa marcada o Git Bash não acha o Python.

**Guardar o `$PY` da sessão.** Todo comando daqui pra frente usa `"$PY"` no lugar de `python3`. Se o terminal for fechado e reaberto, resolver de novo.

### 2. Se `~/.codex/auth.json` NÃO existe

Mostrar ao user:

> Pra usar essa skill tu precisa logar no Codex CLI uma vez (vai abrir o browser). Roda isso no terminal e me avisa quando terminar:
>
> ```bash
> npx @openai/codex login
> ```
>
> Depois disso o token fica salvo em `~/.codex/auth.json` e dura meses. Tu não precisa logar de novo.
>
> Se tu não tem plano ChatGPT pago, essa skill não funciona. Usa `/image-gen-ratos` (FAL, $0.06/imagem) ou `/nanobanana-ratos` (Gemini, grátis) em vez disso.

### 3. Se `~/.codex/auth.json` JÁ existe

Seguir direto pro fluxo de geração. Não precisa de setup adicional.

## Estilo visual (conversacional, NÃO hardcoded)

Igual a `image-gen-ratos`. A skill **não força** nenhum estilo. Cada projeto/marca/canal tem o seu.

No início de cada sessão (a primeira vez que o user pedir imagem na conversa atual), perguntar:

> Como tu quer o estilo? 4 caminhos:
>
> 1. **Livre** — descreve em palavras
> 2. **Brand guide** — cola aqui o teu DNA visual ou aponta pra um arquivo
> 3. **Usar exemplo** — tem exemplos em `~/.claude/skills/gpt-image2-ratos/examples/`
> 4. **Sem estilo** — gera puro, sem calibração

Aplicar o estilo escolhido como contexto/prefixo no prompt em inglês. Não perguntar isso a cada imagem da mesma sessão — só na primeira.

## Modos de operação

### Modo direto

User cola um prompt pronto em inglês. Claude só roda.

### Modo assistido (default quando user só passa tema)

User dá um tema curto. Claude:

1. Se ainda não definiu estilo nesta sessão, pergunta
2. Sugere **3 conceitos distintos** em 2-3 linhas cada
3. Pergunta qual vai
4. Quando user escolher: escreve o prompt em **inglês** com detalhes (lighting, câmera, composição, etc)
5. Roda
6. Mostra

## Aspect ratio e quality

| Aspect | Width x Height | Pra quê |
|---|---|---|
| `1:1` (default) | 1024x1024 | Feed quadrado |
| `4:5` | 1024x1280 | Feed vertical |
| `9:16` | 1024x1792 | Stories, Reels, Shorts |
| `16:9` | 1792x1024 | Thumbnail YouTube, landscape |

**Quality** — afeta latência mais que custo (que é flat dentro do limite do plano):

| Quality | Latência tipica | Quando usar |
|---|---|---|
| `low` | ~60-90s | Rascunho |
| `medium` (default) | ~90-120s | Produção padrão |
| `high` | ~120-180s | Final final |

## O caminho mudou em 30/09/2026 (ler antes de copiar comando velho)

Esta skill pedia a imagem por `/v1/responses`, invocando o `gpt-image-2` como
**ferramenta dentro de um modelo de conversa** (`gpt-5.4-mini` no texto
original). Esse caminho depende de existir na conta um modelo que acione a
ferramenta, e isso quebrou três vezes: o `gpt-5.4-mini` saiu do catálogo em
08/09, o `gpt-5.5` saiu em 30/09, e o que sobrou responde por escrito em vez de
desenhar.

**O `gpt-image-2` tem endpoint próprio no proxy, e é por ele que se pede agora.**
Ali ele é a ferramenta, não um convidado dentro de outro modelo, então catálogo
de conversa mudar não derruba mais nada. De quebra ficou rápido: cerca de 24 s
por imagem contra os 60 a 180 s do caminho antigo.

Dois endereços, um modelo só:

| Caso | Endereço | Corpo |
|---|---|---|
| Desenhar do zero | `/v1/images/generations` | JSON |
| Desenhar sobre referência | `/v1/images/edits` | **multipart**, nunca JSON |

**Não mandar `moderation`.** Este caminho recusa com todas as letras:
`` `moderation` is not supported by ChatGPT OAuth image generation ``, e a
imagem inteira morre em 400. Ele ia junto por hábito do caminho antigo.

**O `size` é pedido mas não é obedecido** (pedi 1024x1536 e veio 1254x1254).
Quem faz a proporção nascer certa é o **enquadramento escrito no prompt**
("Vertical framing, 4:5"), que funciona bem: pedido assim, o retorno veio
1122x1402, que é 4:5 exato. Se o arquivo precisa bater no pixel, recortar no
pós.

## Comando base (text-to-image)

```bash
PORT=10531
OUT_DIR="${OUT_DIR:-/tmp/gpt-image2-out}"
mkdir -p "$OUT_DIR"

# Python da sessão (ver pré-requisitos). Resolve de novo se a variável sumiu.
if [ -z "$PY" ]; then
  for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" >/dev/null 2>&1; then
      PY="$c"; break
    fi
  done
fi
[ -z "$PY" ] && { echo "[skill] Python 3 nao encontrado. Ver a secao de pre-requisitos."; exit 1; }

# 1. Verificar se proxy ja esta rodando
if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/v1/models" 2>/dev/null | grep -qE "^(2|4)"; then
  echo "[skill] proxy ja UP"
else
  echo "[skill] subindo proxy openai-oauth na porta $PORT..."
  npx -y openai-oauth --port "$PORT" > "$OUT_DIR/proxy.log" 2>&1 &
  for i in $(seq 1 30); do
    if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/v1/models" 2>/dev/null | grep -qE "^(2|4)"; then
      echo "[skill] proxy UP (tentativa $i)"
      break
    fi
    sleep 1
  done
fi

# 2. Pedir a imagem. O enquadramento vai NO PROMPT, que e o que a ferramenta
#    respeita de verdade (ver a tabela acima).
curl -sS --max-time 300 -X POST "http://127.0.0.1:$PORT/v1/images/generations" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-image-2","prompt":"PROMPT_AQUI","n":1,"quality":"medium"}' \
  > "$OUT_DIR/resposta.json"

# 3. Extrair o PNG
"$PY" <<'FIM_DO_PYTHON'
import json, base64, pathlib, sys
d = json.loads(pathlib.Path("OUT_DIR_PLACEHOLDER/resposta.json").read_text())
if "data" not in d:
    print(f"ERRO: {str(d)[:400]}", file=sys.stderr)
    sys.exit(1)
out = pathlib.Path("OUTPUT_PATH_PLACEHOLDER")
out.write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
print(f"Salvo: {out} ({out.stat().st_size} bytes)")
FIM_DO_PYTHON
```

Substituir `PROMPT_AQUI`, `OUT_DIR_PLACEHOLDER` e `OUTPUT_PATH_PLACEHOLDER` antes de rodar.

**`OUTPUT_PATH_PLACEHOLDER` é sempre um `.png` de trabalho, terminado em `-raw.png`.** Ele não é a entrega. A entrega é o `.jpg` que sai do passo de granulado abaixo.

**Não matar o proxy** ao final do request. Deixa rodando pra reusar nas próximas imagens da sessão.

Pra parar manualmente:

```bash
# Mac e Linux
lsof -ti:10531 | xargs kill

# Windows, no Git Bash. As duas barras no //PID e //F são propositais: sem elas
# o Git Bash converte a barra num caminho de arquivo e o taskkill recusa.
netstat -ano | grep ":10531" | grep LISTENING | awk '{print $5}' | sort -u | xargs -r -I{} taskkill //PID {} //F
```

## Comando com imagem de referência (image edit)

Outro endereço e, principalmente, **outro formato de corpo**: aqui é
`multipart/form-data`. Mandar JSON devolve
`Image editing requires a multipart/form-data request body`.

O campo é `image[]` (com colchetes) e aceita **até 16 referências** na mesma
edição: é só repetir o `-F`.

```bash
curl -sS --max-time 300 -X POST "http://127.0.0.1:$PORT/v1/images/edits" \
  -F "model=gpt-image-2" \
  -F "image[]=@referencia.png;type=image/png" \
  -F "prompt=Edit/use the reference image(s): PROMPT_AQUI. Vertical framing, 4:5." \
  -F "n=1" \
  -F "quality=medium" \
  > "$OUT_DIR/resposta.json"
```

A extração do PNG é a mesma do comando base: a resposta é um JSON inteiro, com
a imagem em `data[0].b64_json`. **Não é SSE**, então não há evento nenhum pra
varrer, o que também simplificou o script.

## Granulado (passo obrigatório, roda sempre)

**Toda imagem gerada aqui passa por `scripts/grain.py` antes de ser mostrada ou entregue.** Não é opcional, não é enfeite: é o que tira a cara de render de IA e dá textura de foto. Imagem crua do modelo é limpa demais, plástica.

```bash
"$PY" ~/.claude/skills/gpt-image2-ratos/scripts/grain.py saida-raw.png saida.jpg 6.0
```

O `grain.py` em si é Pillow puro e roda igual nos três sistemas. O que muda é só o nome do Python na frente.

O script faz, nessa ordem:

1. Ruído monocromático gaussiano (grão de filme é luminância, não cor)
2. Suavização leve do ruído, pra não virar chuvisco de TV
3. Peso por tom: grão forte nos meios-tons, sumindo nas altas luzes, que é como filme se comporta
4. Vinheta discreta (10%)
5. Salva JPG qualidade 95 sem subsampling de croma, pra não sujar a borda do produto

**Intensidade por tipo de imagem:**

| Tipo | `amount` |
|---|---|
| Foto de produto, cena cinematográfica, retrato, ambiente | `6.0` (default) |
| Imagem já bem escura ou com muita textura | `4.0` |
| Arte gráfica chapada, logo, imagem com texto grande legível | `3.0` e vinheta `0` |

Abaixo de 4 quase não aparece. Acima de 10 fica sujo. Quarto argumento é a vinheta: `... 3.0 0` desliga.

**Fluxo padrão:**

```bash
# 1. gera (comando base acima) -> $OUT_DIR/cena-raw.png
# 2. granula -> entrega
"$PY" ~/.claude/skills/gpt-image2-ratos/scripts/grain.py "$OUT_DIR/cena-raw.png" "$OUT_DIR/cena.jpg" 6.0
```

Mostrar ao user **o `.jpg` granulado**, nunca o `-raw.png`. O raw fica só como fonte pra regranular em outra intensidade sem gastar quota de novo.

**Nunca pedir grão no prompt.** O modelo entrega grão irregular e feio, e ainda gasta detalhe da cena com isso. Grão sempre no pós.

**Quando pular:** só se o user pedir explicitamente ("sem grão", "limpo", "chapado"). Nesse caso entregar o PNG raw direto. Não perguntar toda vez, o default é granulado.

**Dependências:** Pillow e numpy no Python da sessão. Se der `ModuleNotFoundError`, rodar `"$PY" -m pip install --user pillow numpy`.

## Princípios pra escrever o prompt

1. **Em inglês.** O modelo entende PT mas responde melhor a direção técnica em EN. Texto literal na imagem pode ser em PT.
2. **Texto em quotes.** Pra renderizar verbatim: `reads "[texto em português]"`. ~99% accuracy.
3. **Composição, não intenção.** "Medium shot, subject centered, banker lamp backlighting" > "dramatic portrait".
4. **Listar negativos.** "No emojis, no gradients, no stock photo aesthetic".
5. **Specificity vence.** "Space-black MacBook Pro 16-inch M3" > "a laptop".
6. **Referências cinematográficas (se o estilo pedir).** "In the visual style of Severance office scenes".
7. **Produto físico entra com a medida real (regra da casa, 13/11/2026).** Antes de gerar, ache a medida no fabricante (L x A x P em cm e o peso em kg) e escreva no prompt, com a proporção e o tamanho contra a mão (mão adulta: 19 cm por 9 cm). Uma mão só segura até 25 cm e 1,5 kg; até 45 cm e 4 kg vão as duas; acima disso o produto fica apoiado, sem mão. Sem medida, não gera. Nasceu da JBL Xtreme 5 (34,6 cm, 2,9 kg) desenhada numa mão só, com a mão torta. Regra completa no `CLAUDE.md` da raiz do workspace.

## Pós-geração

Rodar o granulado (seção acima) e mostrar o **`.jpg` granulado** ao user. Por causa da latência, perguntar **antes** de fazer outra:
- Aprovou? → pergunta onde salvar/publicar
- Grão forte/fraco demais? → **não regerar.** Rodar `grain.py` de novo no mesmo `-raw.png` com outro `amount`. É instantâneo e não gasta quota
- Quer variação da cena? → ajusta 1 detalhe e roda de novo (avisa que vai levar mais 1-3 min)
- Quer mesma ideia em outro aspect/quality? → rerodar

Não gerar 3 variações em paralelo sem perguntar — cada uma queima quota Codex do plano dele.

## Troubleshooting

**`~/.codex/auth.json` não existe**
User não logou no Codex CLI. Mostrar: `npx @openai/codex login`.

**Proxy não sobe (timeout em 30s)**
Ver `$OUT_DIR/proxy.log`. Causas comuns:
- Porta 10531 ocupada por outro processo. Mac e Linux: `lsof -i :10531`. Windows: `netstat -ano | grep ":10531"`. Matar com o comando da seção do proxy
- Rede lenta no primeiro download do `openai-oauth` (npx baixa antes de rodar)
- Token expirado e refresh falhou: rodar `npx @openai/codex login` de novo

**`401` ou `403` do proxy**
Token OAuth expirou ou foi revogado. User precisa relogar: `npx @openai/codex login`.

**`429` do proxy**
Limite Codex do plano ChatGPT esgotado. Esperar reset (geralmente a cada 5h).

**Imagem não veio (a resposta não tem `data`)**
Ler a mensagem que veio no lugar, ela costuma dizer o que foi. Recusa por
conteúdo pede prompt reescrito; `model ... does not exist` quer dizer que a
conta não libera o `gpt-image-2`, e aí o problema é o plano, não o pedido.

**`400` com `moderation is not supported`**
Tirar o `moderation` do corpo. Este caminho não aceita, ver a tabela do topo.

**`400` com `Image editing requires a multipart/form-data request body`**
Mandou JSON na edição. Referência vai em `-F "image[]=@arquivo.png"`.

**Latência muito maior que 180s**
Status do plano ChatGPT pode estar com fila. Verificar [status.openai.com](https://status.openai.com).

**Imagem em PT com acentos quebrados**
Encurtar a string. Confirmar que tá em quotes: `reads "texto"`.

### Só no Windows

**`python3: command not found`, ou abre a Microsoft Store**
O `python3` do Windows é um atalho falso que só empurra a Store. Resolver o `$PY` pelo laço dos pré-requisitos, que testa se o comando roda de verdade antes de aceitar. Se nenhum dos três servir, instalar o Python de [python.org](https://www.python.org/downloads/) marcando **"Add python.exe to PATH"**.

**`taskkill: The process ... could not be terminated`, ou reclama do argumento**
Faltaram as barras duplas. No Git Bash é `taskkill //PID 1234 //F`, não `/PID`. Com uma barra só, o Git Bash acha que é caminho de arquivo e converte antes de entregar ao Windows.

**`command not found` em curl, mkdir ou awk**
O terminal não é o Git Bash. Prompt de Comando e PowerShell não rodam estes comandos. Abrir o **Git Bash** e repetir. No VS Code: `Terminal > Selecionar Perfil Padrão > Git Bash`.

**O proxy sobe mas o `curl` não conecta**
Firewall do Windows barrando o Node na primeira execução. Aparece uma janela pedindo permissão. Se foi negada sem querer, liberar em Firewall do Windows Defender, Permitir um aplicativo, e marcar o Node.js em rede privada.

**Antivírus apaga o download do `npx`**
Alguns antivírus removem pacote recém-baixado do npm. Se o `proxy.log` acusar arquivo faltando, liberar a pasta do npm cache (`%LOCALAPPDATA%\npm-cache`) no antivírus e rodar de novo.

## Custos reais (atenção)

A skill é "free" no sentido de não cobrar API extra, mas **queima limite do plano ChatGPT**. Por doc oficial da OpenAI, image generation consome limite Codex **3-5x mais rápido** que turn de texto.

Avisar o user no setup:

> Heads up: cada imagem aqui usa parte da tua quota Codex do plano ChatGPT. Se tu também usa Codex CLI pra coding, isso compete pelo mesmo limite. No Plus ($20/mês), tu provavelmente consegue gerar ~6-30 imagens medium em cada janela de 5h, mas isso vai depender do uso normal do Codex.

## Referências

- Exemplos de estilo: `~/.claude/skills/gpt-image2-ratos/examples/`
- [Pacote openai-oauth (proxy local)](https://github.com/EvanZhouDev/openai-oauth)
- [Codex CLI Authentication (OpenAI)](https://developers.openai.com/codex/auth)
- [Codex CLI Features (image generation)](https://developers.openai.com/codex/cli/features)
- Skill complementar (FAL, paga): `/image-gen-ratos`
- Skill complementar (Gemini, grátis): `/nanobanana-ratos`
