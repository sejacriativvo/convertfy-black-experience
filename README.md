# Black Experience: o filme

O filme dos dois dias do Black Experience da Convertfy (11 e 12/11/2026) pro YouTube, editado por script com o Claude Code. Tudo que define o vídeo está aqui: o roteiro, o motor que monta, as transcrições, a música, os efeitos e a marca. Os vídeos (o bruto das câmeras e o filme pronto) ficam no Drive, porque o maior clipe tem 16 GB e o GitHub não aceita arquivo acima de 100 MB.

- **Filme pronto:** pasta `render/` do Drive ([abrir](https://drive.google.com/drive/folders/1RkGZTTGUiUtwuPBUnYUWd_a9r1V7RNXj))
- **Bruto:** pasta `bruto/` do mesmo Drive (FX30 dos dois dias, drone e Mini Cooper), índice em `midia.json`

## Começar (uma vez, num Mac com chip Apple)

1. Instale o [Homebrew](https://brew.sh) e o [Claude Code](https://claude.com/claude-code).
2. Clone e prepare:
   ```sh
   git clone https://github.com/sejacriativvo/convertfy-black-experience.git
   cd convertfy-black-experience
   sh bin/instalar.sh
   ```
   Ele instala ffmpeg, rclone e Python, pede login do Google uma vez (a conta com acesso à pasta do Drive) e baixa o bruto que o roteiro usa, cerca de 150 GB. Precisa de uns 250 GB livres contando o cache.
3. A fonte Gilroy (números na tela) é paga e não vem no repositório: instale no Mac.

## Editar

Abra o Claude Code nesta pasta e peça a mudança como pediria a um editor ("no minuto 15:54 põe o nome dele com uma seta", "a música do kart entra mais cedo"). O `CLAUDE.md` ensina o Claude a mexer no roteiro, renderizar e conferir.

## Tudo vai junto, sozinho

No fim de cada resposta do Claude, a edição é exportada sem ninguém pedir: o roteiro e os dados vão pro GitHub, o filme renderizado e qualquer clipe novo vão pro Drive. Quem abrir depois começa de onde o outro parou (`git pull`).
