# Black Experience: o filme

O filme dos dois dias do Black Experience da Convertfy (11 e 12/11/2026) pro YouTube, editado por script com o Claude Code. Tudo que define o vídeo está aqui: o roteiro, o motor que monta, as transcrições, a música, os efeitos, a marca e as skills que usamos. Os vídeos (o bruto das câmeras e o filme pronto) ficam no Drive, porque o maior clipe tem 16 GB e o GitHub não aceita arquivo acima de 100 MB.

- **Filme pronto e bruto:** [pasta no Drive](https://drive.google.com/drive/folders/1RkGZTTGUiUtwuPBUnYUWd_a9r1V7RNXj) (`render/` e `bruto/`), índice em `midia.json`

## Começar (uma vez)

Precisa de um Mac com chip Apple, uns 400 GB livres e o [Claude Code](https://claude.com/claude-code). Cole isto no Claude Code:

> Quero editar o filme do Black Experience da Convertfy. Clona https://github.com/sejacriativvo/convertfy-black-experience.git em ~/convertfy-black-experience e lê o README.md e o CLAUDE.md de lá. Depois roda `sh bin/instalar.sh` em segundo plano: ele instala ffmpeg, rclone e Python, abre o navegador uma vez pro meu login do Google e baixa todos os vídeos do Drive (uns 230 GB, demora). Se faltar o Homebrew, me passa o comando pra eu rodar no Terminal. Quando terminar, abre o filme pronto pra eu assistir e me lembra de abrir o Claude Code dentro da pasta convertfy-black-experience nas próximas vezes.

A fonte Gilroy (números na tela) é paga e não vem no repositório: se o instalador avisar que falta, instale no Mac.

## Editar

Abra o Claude Code dentro da pasta `convertfy-black-experience` e peça como pediria a um editor:

- "no 15:54 tira esse take e põe o do Rick rindo"
- "a música do kart entra 2 segundos antes"
- "renderiza em 4K"

O Claude mexe no roteiro, monta um teste do trecho, mostra, confere sincronia e emenda de fala, e renderiza o filme inteiro em 1080p ou 4K (`render/`). O `CLAUDE.md` tem as regras de edição que já foram decididas e o porquê de cada uma.

## O que vai junto, sozinho

No fim de cada resposta do Claude, a edição é salva no git desta pasta. Quem tem acesso de escrita (o Matheus) manda também pro GitHub e o filme novo pro Drive; quem clonou sem acesso fica com tudo salvo no próprio Mac, e o aviso aparece uma vez. Pra mandar de volta, é só pedir acesso de colaborador ao Matheus.
