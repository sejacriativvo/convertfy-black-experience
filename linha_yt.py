"""O roteiro do vídeo do YouTube. Mexer aqui e rodar yt.py.

Fonte (fontes.py): int NNNN = breno.NNNN.MP4 (FX30, dias 11 e 12); "d477" = drone; "o11"/"o12" = Osmo da entrega do
Mini Cooper; "cel" = iPhone da entrega (o som vem do Osmo: tempo no 0011 = tempo no iPhone + fontes.sync_cel).
Tempos em segundos do arquivo bruto (transcricao.json, Whisper large-v3; palavras.py mostra cada palavra com o tempo).
Toda emenda é puxada pro vão de silêncio do lado certo da palavra (respiros.vale); dentro da fala sai a respiração
(respiros.pedacos_vad), só fica 0,15 s entre as palavras.
fala:  fonte, ini, fim, tira=[(a, b)] (trecho que sai), j / l (corte J ou L na entrada), respira=False (momento:
       nada sai de dentro), cobertura=[(a, b, clipe, ss[, lento])] ou [(a, b, [(clipe, ss), ...])] (imagem de outro
       clipe por cima da voz, tempos da fala), insights=[dict(t, rotulo, modo, ...)], quadro (z, cx, cy), z (zoom fixo).
broll: tomadas=[(clipe, ss, duração[, opções])] (duração em batidas se tiver bpm; opções: lento, quadro, som=dB do som
       ambiente contra a fala), vo=[(fonte, a, b, deslocamento)] (voz de outro clipe por cima).
Em qualquer bloco: marca, titulo, cartela=dict(texto=(esq, meio, dir)), fx=[(t, arquivo ou "gen:...", dB)].

Revisão de 13/11: sem card de número, sem horário, sem capítulo, sem nome na tela; insight da Convertfy na fala; logo
Black Experience no drop e a da Convertfy no fim; corte só em fim de raciocínio.
Revisão de 14/11: apoio = gente de perto conversando e rindo, só onde ilustra; nada de comida (mosca), chão de piscina ou
céu; câmera lenta só no que foi gravado a 60p; hot seat com corpo; resenha entre as entrevistas.
Revisão de 15/11, manhã: conversa só no microfone da câmera sai (logprob do Whisper pior que -0,33); emenda em silêncio
de verdade.

Revisão de 15/11, tarde (pedido do Matheus: o vídeo completo, os DOIS dias, "um tesão de assistir", ninguém pensa em
pular): cara de filme, no molde do "G4 Valley: Por Trás do Palco" (abertura com 71 cortes no primeiro minuto e frase
forte por cima; depois conversa longa com rajadas de apoio) e do MrBeast (a promessa no começo e a recompensa no fim).
  - Abre com drone, cinema: cama no tom de "Can't Tell Me Nothing" (Fá menor) e a voz do Kanye com reverb de sala até
    o drop na logo (skill trilha-cinematografica).
  - Três laços abertos na abertura e pagos depois: o champanhe de quem mais faturar (o Rafa, 1235), a surpresa do Bruno
    pra namorada (o Mini Cooper rosa, que fica pra depois das expectativas) e o kart.
  - Música por momento: "Die With A Smile" no Mini Cooper (silêncio quando a porta do baú abre, refrão no "Era o meu
    sonho!"), "Can't Tell Me Nothing" na noite ("Let the champagne splash" em cima da rolha), "Lovely Day" no dia 2,
    "Bandoleros" no kart (com a música freando na piada da bebida alcoólica). Entrevista fica seca.
  - Respiração sai de dentro da fala (Silero VAD + energia), palavra nunca.
  - Enquadramento padrão (pedido no meio da revisão): rosto com o mesmo tamanho em toda fala, olhos a 36% da altura,
    âncora fixa por bloco (yt.ROSTO_AB / ROSTO_FE / OLHOS).
  - Cartela de dia no desenho da referência: data · DIA N · evento, numa linha só.

Revisão de 15/11, noite ("tá dessincronizado", "pega os melhores quadros", "sem cortar começo e fim de palavra"):
  - Apoio no trecho mais nítido e sem tremida de cada clipe (melhor.py mede nitidez, tremida e exposição); só fica onde
    a cena pede o quadro (a cara de tédio no vídeo de segurança, a risada).
  - Emenda conferida no vídeo pronto (emendas_final.py: voz alta colada no corte). Onde não há silêncio entre duas
    palavras o vale buscava o do outro lado e entrava palavra solta ("conhecer. Ai, amor", "top 3. Eu", "Não. Quanto
    tempo"): esses cortes estão em fixos=[...], no ponto mais baixo medido entre as duas palavras.

Revisão de 15/11, madrugada (a lista do Matheus: drone sem os melhores movimentos, áudio ruim, entrevistas seguidas,
pouca graça, Mini Cooper picotado e música fora da reação, dia 1 grande e dia 2 pequeno, texto travado):
  - Drone escolhido pelo movimento (drone.py): afastamento na casa, perseguição do kart, passagem lateral, órbita.
  - Nada de som de microfone longe fora a entrega (lá é a voz dela ou nada): saíram 1350, a voz do futevôlei, o 1403,
    o "desgramado me girou", o fim do troféu e o pingue-pongue de 1305.
  - Expectativa: só o Luan e o Rafa, com resenha no meio; o Miguel e o Gui vão pra noite, antes do telão.
  - Mini Cooper inteiro e em ordem (o11 e o12 são o mesmo Osmo, o12 = o11 - 242; o segundo ângulo é o iPhone):
    "ontem eu chorei" -> "você desconfiou?" -> "último romântico" -> "o carro era da Isa" -> a Barbie.
  - Mais graça: o "garçom", o Bruno imitando o dono de loja, os erros de gravação ("corta essa parte aí"), o designer
    que só atende call às 3 da tarde, as apostas do kart pagas no placar (Luan 2º, Vitinho 3º, Matheus 7º).
  - Dia 2 maior: resenha de onde veio cada um, depoimentos com número (2 mil dólares por dia, empresa em 2x, o dia
    salvo do Luiz, +30%), sempre com resenha entre um e outro.
"""
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
MUS = os.path.join(AQUI, "musica")
CTMN = os.path.join(MUS, "cant-tell-me-nothing.wav")      # Fá menor, 80,7 BPM, drop 6,171 s, "Let the champagne splash" 150,0 s
DWAS = os.path.join(MUS, "die-with-a-smile.wav")          # refrão "If the world was ending" em 44,5 s
LOVELY = os.path.join(MUS, "lovely-day.wav")               # 99 BPM, "lovely day" em 55,3 s
BANDO = os.path.join(MUS, "bandoleros.wav")                # 117,5 BPM, a batida cai no "Aunque digan" em 18,0 s


def cel(t_osmo):
    """o quadro do iPhone que corresponde ao segundo t do Osmo 0011"""
    return t_osmo - (44.22 if t_osmo < 85 + 44.22 else 48.73)


ROTEIRO = [
    # ================================================================ ABERTURA: drone, a promessa, os três laços
    dict(tipo="broll", marca="gancho", tomadas=[("d477", 3.0, 3.6)]),                # o drone se afastando, a casa aparece
    dict(tipo="fala", marca="co_b", fonte=1229, ini=8.80, fim=14.36, respira=False,
         cobertura=[(8.80, 14.36, [(1196, 0.0), (1220, 8.0)])]),                    # "o faturamento em tempo real"
    dict(tipo="fala", marca="co_c", fonte=1294, ini=53.24, fim=57.16, respira=False,     # "Eles venderam 90 mil em um minuto."
         insights=[dict(t=55.94, rotulo="Uma loja na Black", g="R$ 90 MIL", p="em um minuto", dur=1.6)]),
    dict(tipo="fala", marca="co_d", fonte=1235, ini=89.02, fim=93.70, respira=False,
         cobertura=[(92.50, 93.70, 1314, 14.6, False)]),                            # "...vai ter direito a estourar, ó"
    dict(tipo="fala", marca="co_e", fonte="o11", ini=114.86, fim=116.95, respira=False),   # "Mas antes, eu preparei uma surpresa"
    dict(tipo="fala", marca="co_f", fonte="o11", ini=191.05, fim=192.00, respira=False),   # "Mentira!"
    dict(tipo="broll", tomadas=[("d493", 5.0, 1.8)]),                                # o drone caçando o kart na reta
    dict(tipo="fala", marca="co_h", fonte=1401, ini=37.40, fim=39.75, respira=False,
         cobertura=[(37.40, 39.75, 1400, 7.2, False)]),                             # "O kartismo é um esporte de risco."
    dict(tipo="broll", tomadas=[(1405, 0.6, 1.1, {"som": -6}), (1409, 0.6, 1.0, {"som": -6})]),
    dict(tipo="fala", marca="co_j", fonte=1414, ini=0.0, fim=2.72, respira=False),        # "Eu rodei, logo na outra curva me rodaram também"
    # a voz do Kanye com reverb ("La, la, la, la, wait till I get my money right") vem da cama de cinema, sem fala por cima
    dict(tipo="broll", marca="co_voz", tomadas=[("d483", 2.0, 3.3), ("d485", 1.5, 3.1)]),

    # ---------------------------------------------------------------- drop: gente de perto, a logo por cima
    dict(tipo="broll", marca="drop", bpm=80.75,
         tomadas=[(1242, 1.6, 4), (1206, 1.8, 3), (1193, 0.5, 2), (1197, 0.3, 2), (1202, 30.0, 2), (1247, 0.7, 3)],
         titulo=dict(kicker="CONVERTFY  ·  11.11.2026", dur=5.2, em=0.1), fx=[(0.0, "gen:boom", -10)]),

    # ================================================================ DIA 1
    dict(tipo="broll", marca="dia1", tomadas=[("d478", 9.0, 4.4)],
         cartela=dict(texto=("11 DE NOVEMBRO DE 2026", "DIA 1", "BLACK EXPERIENCE"), em=0.5, dur=3.4)),
    dict(tipo="fala", marca="abertura", fonte=1229, ini=1.58, fim=38.75, tira=[(18.07, 31.52)], j=0.6,
         nome=("Bruno", "Convertfy, anfitrião do Black Experience"), nome_em=0.6,
         glossario=[(16.9, "Data dupla", "dia em que o número do dia repete o do mês, como o 11/11. As lojas criam uma "
                                       "promoção e um pico de vendas nesse dia.")],
         cobertura=[(6.66, 8.58, [(1173, 0.4), (1201, 12.8)]),                      # "os 30 maiores clientes" (o nome antes, 16/11)
                    (31.52, 38.28, [(1255, 178.0), (1250, 9.5), (1248, 5.0)])],     # "durante um hot seat"
         insights=[dict(t=6.82, rotulo="11.11 · Black Experience", g="30 CLIENTES",
                        p="os maiores da Convertfy, numa casa só")]),
    # o Bruno recebe a turma na porta de casa e anuncia a surpresa... e a gente corta (o laço do Mini Cooper)
    dict(tipo="fala", marca="boas_vindas", fonte="o11", ini=91.98, fim=122.16, tira=[(101.70, 106.66)],
         cobertura=[(107.0, 112.0, "cel", cel(107.0), False)]),
    dict(tipo="broll", marca="corte_surpresa", tomadas=[("d479", 5.0, 1.4)], fx=[(0.0, "whoosh-grande-1.mp3", -14)]),

    # ---------------------------------------------------------------- duas apostas pro dia, com resenha no meio
    dict(tipo="fala", marca="expectativas", fonte=1230, j=1.0, ini=6.26, fim=30.22, tira=[(19.42, 21.88)],
         nome=("Luan", "cliente da Convertfy há mais de um ano"),
         glossario=[(14.10, "E-mail marketing", "os e-mails automáticos da loja: trazem de volta quem visitou e não "
                                                "comprou, e fazem quem já comprou voltar.")],
         insights=[dict(t=10.66, rotulo="Expectativa do Luan", g="US$ 25 MIL", p="de faturamento, num dia só"),
                   dict(t=25.76, modo="versus", rotulo="Quanto vem do e-mail", g="60%", g2="62%", n1="Bruno",
                        n2="Luan", em2=3.75, p="a aposta pro fim do dia", dur=4.4)]),
    dict(tipo="broll", tomadas=[(1202, 16.5, 2.0, {"lento": False, "som": -14}), (1204, 9.0, 1.8, {"lento": False, "som": -14})]),
    # o Rafa: a pergunta e a virada de percepção; o prêmio do champanhe e a mão segurando a campanha
    dict(tipo="fala", fonte=1235, ini=4.60, fim=105.80, j=0.5, tira=[(14.10, 27.84), (38.36, 43.58), (51.95, 86.76)],
         nome=("Rafa Dino", "o dinossauro do mercado"), nome_em=1.2,
         insights=[dict(t=11.20, rotulo="Rafa Dino", g="6 DÍGITOS", p="em dólar, todo mês"),
                   dict(t=50.14, rotulo="1º mês com e-mail", g="15%", p="do faturamento já veio do e-mail")]),

    # ================================================================ O MINI COOPER (o laço da surpresa, pago, inteiro)
    # o caminhão-baú chega; "fruto de anos de trabalho", "ela não sabe que carro que é", "qual que é o seu chute?"
    dict(tipo="fala", marca="mini", fonte="o11", ini=148.08, fim=186.70, fixos=[186.70],
         tira=[(149.20, 155.50), (169.40, 175.20)],
         cobertura=[(155.62, 159.10, "cel", cel(155.62), False),                    # o baú encostando
                    (165.30, 169.20, "cel", cel(165.30), False)]),
    # a porta abre e ela vê: som contínuo do Osmo, a imagem alterna com o iPhone de frente
    dict(tipo="fala", marca="porta", fonte="o11", ini=186.70, fim=233.58, fixos=[186.70], respira=False,
         tira=[(214.10, 215.90), (224.30, 227.20)],
         cobertura=[(186.80, 191.00, "cel", cel(186.80), False),                    # o baú abrindo
                    (197.60, 200.40, "cel", 148.87, False),                         # o Mini rosa lá dentro
                    (208.00, 211.40, "cel", cel(208.00), False)]),
    # "como que eu vou abastecer isso?" e o "você desconfiou?": ontem ela voltou chateada achando que o carro tinha ido
    dict(tipo="fala", fonte="o12", ini=0.0, fim=2.90, respira=False),
    dict(tipo="fala", fonte="o12", ini=63.60, fim=88.55, tira=[(73.53, 76.98)]),
    dict(tipo="fala", fonte="o12", ini=95.65, fim=100.47),                               # "eu ia ter que gravar muitos vídeos pra pagar isso"
    # o carro de perto, com o refrão
    dict(tipo="broll", marca="mini_carro", tomadas=[("o12", 123.7, 2.6), ("d481", 3.5, 3.0), ("o12", 129.8, 2.4),
                                                     ("d480", 6.0, 3.0), ("o12", 133.0, 2.2)]),
    dict(tipo="fala", fonte="o12", j=1.0, ini=138.62, fim=144.79, fixos=[138.62, 144.79], tira=[(140.45, 143.35)]),   # "um Mini Cooper rosa... tem até um buquê"
    dict(tipo="fala", fonte="o12", ini=154.62, fim=170.65, tira=[(162.26, 166.30)]),     # "a minha cara era o Mini Cooper rosa... o último romântico"
    # o fecho do fio: o carro era da Isa ("você só pode vender ele se for pra mim")
    dict(tipo="fala", fonte="o12", ini=235.50, fim=242.42, fixos=[242.42]),             # o "deixa eu colocar a lapela" vem colado
    dict(tipo="fala", fonte="o12", ini=247.25, fim=252.32),                              # "não tem como ser triste com o Mini Cooper rosa"
    dict(tipo="fala", marca="barbie", fonte="o12", ini=383.24, fim=387.85, tira=[(385.40, 386.10)]),   # "a Barbie de Lagoa Santa"

    # ================================================================ O HOT SEAT
    dict(tipo="fala", marca="hotseat", fonte=1255, ini=0.0, fim=78.54, tira=[(4.14, 59.70)],
         glossario=[(0.6, "Hot seat", "um participante abre um problema real do negócio e a roda inteira "
                                      "responde, sem ego.")],
         quadro=[(1.19, 0.53, 0.45), (1.5, 0.53, 0.45)], fx=[(0.0, "whoosh-1.mp3", -18)]),
    dict(tipo="fala", fonte=1255, ini=104.13, fixos=[104.13], fim=143.70, j=0.6,
         quadro=[(1.19, 0.50, 0.47), (1.5, 0.50, 0.47)],
         cobertura=[(128.0, 130.2, 1259, 3.8)],
         insights=[dict(t=120.98, modo="frase", rotulo="Hot seat",
                        linhas=[("VENDER POUCO", 0.15, False), ("É SINTOMA", 0.49, True)], dur=2.8)]),
    # o Bruno imitando o dono de loja: "esse mês tá ruim, não funciona mais, esse mercado é uma merda"
    dict(tipo="fala", fonte=1256, ini=546.14, fim=560.30, quadro=[(1.0, 0.5, 0.5), (1.19, 0.40, 0.50)]),
    dict(tipo="fala", fonte=1255, ini=164.80, fim=228.62, tira=[(167.60, 171.50), (177.10, 217.70)],
         quadro=[(1.19, 0.53, 0.45), (1.5, 0.53, 0.43)],
         insights=[dict(t=165.28, modo="frase", rotulo="Regra do hot seat",
                        linhas=[("EGO", 0.15, False), ("ZERO", 0.35, True)], dur=2.4)]),
    # o Igor abre o problema dele e o diferencial (buy one, get one); e a frase da roda: quantidade de criativo
    dict(tipo="fala", fonte=1256, ini=670.50, fim=716.40, tira=[(681.95, 692.70)],
         quadro=[(1.0, 0.5, 0.5), (1.19, 0.30, 0.50)],
         glossario=[(699.5, "Buy one, get one", "a oferta leve dois, pague um: o cliente sente que levou mais pelo mesmo preço.")]),
    dict(tipo="fala", fonte=1256, ini=228.46, fim=234.50, quadro=[(1.0, 0.5, 0.5), (1.19, 0.62, 0.48)],
         insights=[dict(t=232.96, modo="frase", rotulo="Hot seat",
                        linhas=[("QUANTIDADE", 0.15, False), ("DE CRIATIVO", 0.40, True)], dur=2.6)]),
    # o Bruno pra roda: o cliente que ficou com um milhão de dólares travado ("louco, desequilibrado, porra, maluco")
    # e no 9 de novembro fez 550 mil de lucro
    dict(tipo="fala", fonte=1260, ini=18.92, fim=62.45, tira=[(34.40, 51.10)],
         quadro=[(1.0, 0.5, 0.5), (1.19, 0.40, 0.50)],
         insights=[dict(t=27.54, rotulo="Travado no bloqueio", g="US$ 1 MILHÃO", p="e zero reais na conta", dur=2.8),
                   dict(t=61.24, rotulo="9 de novembro", g="R$ 550 MIL", p="de lucro num dia só", dur=2.8)]),

    # ================================================================ A NOITE
    dict(tipo="broll", marca="noite", tomadas=[("d485", 22.0, 3.0), (1272, 1.5, 2.2), (1287, 20.0, 2.2), (1281, 1.5, 2.0)]),   # 15/11: o drone de cima da casa à noite ficou feio
    # a picanha com folha de ouro: "procedimento pra cliente é ouro, não tem abóbora, é picanha"
    dict(tipo="fala", fonte=1270, j=1.0, ini=32.38, fim=53.58, tira=[(33.80, 36.70), (37.70, 42.40), (43.45, 47.10)],
         cobertura=[(36.70, 43.45, 1267, 1.5, False)]),
    dict(tipo="fala", fonte=1270, ini=185.30, fim=194.90,                              # "você acha que eu sou garçom, caralho?"
         cobertura=[(185.30, 189.40, 1269, 6.5, False)]),
    dict(tipo="fala", fonte=1270, ini=222.20, fim=234.16,                              # "nunca nem comi picanha... nem abóbora"
         cobertura=[(222.20, 226.50, 1266, 3.0, False)]),
    # o Miguel e o Gui: "vai ser bater 100k no dia", e o telão respondendo
    dict(tipo="fala", fonte=1243, ini=9.74, fim=29.20, j=0.6, tira=[(14.10, 16.85)],
         nome=("Miguel e Gui", "o primeiro 11.11 com a Convertfy"),
         insights=[dict(t=20.12, rotulo="Meta do dia", g="100K", p="de faturamento no 11.11")]),
    dict(tipo="fala", marca="telao", fonte=1292, ini=14.38, fim=69.78, z=1.0, tira=[(19.70, 26.50), (32.40, 58.70)],
         insights=[dict(t=29.42, rotulo="Uma venda só", g="R$ 25 MIL", p="caindo ao vivo no telão")]),
    dict(tipo="fala", fonte=1294, ini=46.16, fim=84.96, tira=[(51.30, 53.20), (57.20, 79.80)],   # "venderam 90 mil em um minuto... batia um milhão"
         insights=[dict(t=55.94, rotulo="Uma loja na Black", g="R$ 90 MIL", p="em um minuto", dur=2.4)]),
    dict(tipo="fala", fonte=1300, ini=101.84, fim=105.30,                              # "só hoje, gerados pelo e-mail, mais de 45%"
         insights=[dict(t=104.06, rotulo="Só hoje, pelo e-mail", g="45%", de=15, p="normal é 15 a 18%", dur=2.0)]),
    # volume de teste é rei; e BR ou global? "suma do Brasil, vem pro drop global"
    dict(tipo="fala", fonte=1305, ini=117.92, fim=174.80, tira=[(121.56, 157.04)],
         glossario=[(160.78, "Drop global", "loja online que vende pro exterior, em dólar, e o fornecedor manda o "
                                            "produto direto pro cliente.")]),
    # margem: 25% no tráfego direto, 80% na venda do e-mail
    dict(tipo="fala", fonte=1302, ini=79.96, fim=120.45, tira=[(90.80, 95.30), (99.10, 116.25)],
         insights=[dict(t=84.98, modo="versus", rotulo="Margem por venda", g="25%", g2="80%", n1="tráfego direto",
                        n2="e-mail", em2=5.0, p="", dur=6.0)]),
    # o Igor: "uma semana sem vender, o cara entra em surto"... 40% das vendas do primeiro mês
    dict(tipo="fala", fonte=1309, ini=75.74, fim=132.45, tira=[(95.60, 127.00)],
         nome=("Igor Ferreira", "primeiro mês com a Convertfy"),
         insights=[dict(t=93.20, rotulo="Igor, 1º mês", g="40%", p="das vendas vieram da Convertfy", dur=2.6)]),
    dict(tipo="broll", tomadas=[("d485", 4.0, 2.4), (1288, 12.0, 2.2, {"lento": False, "som": -14})]),           # a festa de cima e uma mesa
    # o Rinhazinho no pingue-pongue de números, e o "pra ontem, mano... brabíssimo"
    dict(tipo="fala", marca="rinhazinho", fonte=1306, j=1.0, ini=84.14, fim=139.05, fixos=[84.14], tira=[(107.80, 118.30)],
         nome=("Rinhazinho", "começou agora no drop global"),
         qr=dict(em=118.40, dur=9.0, chamada=[[("+15% a 25% de faturamento", "b")], [("em 30 dias. ", "b"), ("Ou você não paga.", "i")]],
                 cta=("ESCANEIE O QR CODE", "E RECEBA SEU", "DIAGNÓSTICO GRATUITO"),
                 sub="Diagnóstico gratuito pra lojas acima de R$200 mil/mês"),
         insights=[dict(t=97.66, modo="antes", rotulo="Rinhazinho, 1º mês", a="US$ 400/DIA", g="US$ 40 MIL",
                        depois_em=0.99, p="nos últimos 30 dias", dur=3.8),
                   dict(t=105.88, rotulo="Só do e-mail", g="23%", p="do faturamento no primeiro mês", dur=2.4)]),
    # as apostas pra 2027: a IA substitui o gestor de tráfego? "isso com certeza" x "substituir em si não, né?"
    dict(tipo="fala", marca="apostas", fonte=1231, ini=80.62, fim=89.16),
    dict(tipo="fala", fonte=1236, ini=46.92, fim=48.42, respira=False, fx=[(1.4, "erro.mp3", -26)]),
    dict(tipo="fala", fonte=1245, ini=7.34, fim=90.20, tira=[(19.88, 83.98)],
         nome=("Gui", "+10 milhões no drop global, com o sócio"), nome_em=0.3,
         insights=[dict(t=87.58, modo="antes", rotulo="Aposta pra 2027", a="30", g="100", de=30, depois_em=2.5,
                        p="colaboradores no ano que vem", dur=3.6)]),
    # a aposta pra 2027 com prenda ("se errar, vai pular na piscina") e a piada da sardinha
    dict(tipo="fala", marca="fim_apostas", fonte=1310, ini=2.22, fim=28.72, tira=[(9.88, 14.40)], fixos=[14.40],
         insights=[dict(t=22.30, modo="frase", rotulo="Aposta pra 2027",
                        linhas=[("E-MAIL", 0.15, False), ("MARKETING", 0.40, True)], dur=2.4)]),
    # o placar do telão no fim da noite e o champanhe, com "Let the champagne splash" em cima da rolha (16,5 s do 1314)
    dict(tipo="broll", marca="champanhe", tomadas=[(1292, 6.0, 1.6, {"quadro": (1.5, 0.34, 0.36)}), (1314, 14.6, 1.3),
                                                   (1314, 16.5, 2.6), (1315, 0.0, 2.2), (1314, 37.3, 2.4)]),
    # o fim do dia 1, com o spoiler do dia 2
    dict(tipo="fala", marca="fim_dia1", fonte=1316, j=0.9, ini=2.60, fim=24.72, tira=[(7.10, 21.90)],
         cobertura=[(3.0, 6.9, [(1296, 6.3), (1220, 9.5)])]),

    # ================================================================ DIA 2 (manhã: resenha, depoimento, resenha)
    dict(tipo="broll", marca="dia2", tomadas=[(1338, 0.5, 3.6), (1340, 2.0, 2.4)],
         cartela=dict(texto=("12 DE NOVEMBRO DE 2026", "DIA 2", "BLACK EXPERIENCE"), em=0.3, dur=3.2)),
    dict(tipo="broll", marca="dia2_chegada", tomadas=[(1318, 12.0, 3), (1321, 3.0, 3), (1322, 8.3, 2), (1324, 5.0, 3),
                                                       (1320, 5.0, 3), (1319, 16.8, 2)], bpm=99.38),
    # o bastidor: a casa, a "dona Onça" e as 45 camisas em seis dias
    dict(tipo="fala", fonte=1387, j=1.2, ini=44.78, fim=107.75, tira=[(58.30, 87.65)]),
    # o clima do segundo dia: "hoje ficou mais íntimo... zero ego, todo mundo falando o problema real"
    # (15/11: sem pergunta de quem filma e sem erro de gravação; parecia depoimento combinado)
    dict(tipo="fala", fonte=1362, ini=7.62, fim=27.97, fixos=[27.97]),
    # a feijoada: "a Ana cozinha demais" (o arquivo nasce com 0,4 s de imagem parada: a mesa por cima) e o pão de queijo
    dict(tipo="fala", fonte=1353, ini=0.0, fim=17.78, tira=[(1.10, 4.55), (8.55, 12.55)],
         cobertura=[(0.0, 0.9, 1357, 1.0, False)]),
    dict(tipo="fala", fonte=1360, ini=48.34, fim=56.90),
    # o menino do PlayStation: de 300 dólares por dia a 2 mil em duas semanas, e o 11.11
    dict(tipo="fala", fonte=1374, ini=95.22, fim=160.95, tira=[(115.22, 129.76)],
         nome=("O menino do PlayStation", "dois meses de operação"), nome_em=0.2,
         insights=[dict(t=136.6, modo="antes", rotulo="Duas semanas de Convertfy", a="US$ 300/DIA", g="US$ 2 MIL",
                        depois_em=0.9, p="por dia", dur=2.6),
                   dict(t=147.98, modo="antes", rotulo="Menino do PlayStation", a="R$ 3 MIL", g="R$ 300 MIL",
                        depois_em=3.4, p="de caixa, e hoje de faturamento", dur=5.0)]),
    dict(tipo="fala", fonte=1374, ini=203.40, fim=217.42, fixos=[217.42],                            # "ontem, 40% do faturamento foi por e-mail"
         insights=[dict(t=204.84, rotulo="Ontem, no 11.11", g="40%", p="do faturamento veio do e-mail", dur=2.6)]),
    # a altinha valendo e o futevôlei, só com música; a bicicleta do 1379 (1,62 s: a câmera já fechou nele) é o pico
    dict(tipo="fala", fonte=1368, ini=66.76, fim=85.56, tira=[(67.20, 71.34), (74.76, 76.24)]),
    dict(tipo="broll", marca="futevolei", tomadas=[(1383, 2.0, 2.4), (1378, 4.0, 2.0), (1380, 2.0, 2.0), (1379, 1.62, 1.7),
                                                    (1381, 1.0, 2.2)],
         fx=[(6.55, "swish-3.mp3", -15), (6.80, "grave-1.mp3", -17)]),
    # o Miguel: "duplica o seu lucro... é isso que você deixa na mesa... crescer a nossa empresa em 2x"
    dict(tipo="fala", fonte=1372, j=1.0, ini=237.42, fim=269.85,
         nome=("Miguel", "drop global desde 2019"),
         insights=[dict(t=256.9, modo="frase", rotulo="Com a Convertfy", linhas=[("A EMPRESA", 0.15, False), ("EM 2X", 0.40, True)],
                        p="sem aumentar a estrutura", dur=2.4)]),
    # o designer que nunca atendeu call de vídeo ("só às 3 da tarde, depois da feira") e ele montando um e-mail
    # (16/11: "coloca o nome dele puxando uma setinha... contextualizar num textinho, numa barrinha"). Enquadramento
    # fixo enquanto a seta aponta; o resto segue normal até "é sob gestão dele"
    dict(tipo="fala", fonte=1389, ini=145.54, fim=153.54, quadro=(1.10, 0.47, 0.41),
         destaque=dict(nome="Rick", papel="designer da Convertfy há 3 anos", alvo=(0.30, 0.24), em=0.3, dur=7.0,
                       texto="Ninguém do time conhecia o rosto dele: ele nunca atendeu uma ligação de vídeo.")),
    dict(tipo="fala", fonte=1389, ini=154.12, fim=174.12),
    dict(tipo="fala", fonte=1370, ini=4.96, fim=19.53, fixos=[19.53]),
    # o Luiz: "eu não acreditava"... "hoje a operação tava na baixa, ele já resolveu"... 100 mil... "não perco mais nenhum"
    dict(tipo="fala", fonte=1382, ini=72.74, fim=135.80, tira=[(83.75, 88.35), (92.50, 94.80), (107.15, 122.90)],
         nome=("Luiz", "cliente da Convertfy há um mês"), nome_em=0.4,
         insights=[dict(t=89.6, rotulo="Do faturamento do Luiz", g="21 A 25%", p="vem do e-mail", dur=2.4),
                   dict(t=125.08, rotulo="Esse mês, com a Convertfy", g="R$ 100 MIL", p="de faturamento", dur=2.4)]),
    dict(tipo="fala", fonte=1382, ini=263.86, fim=269.22),                           # "não perco mais nenhum... isso aqui é muito insano"
    # o Vitinho: o Uno de uma buzina por dia e a bronca de irmão na cozinha
    dict(tipo="fala", fonte=1336, ini=36.72, fim=131.95, tira=[(55.90, 82.82), (93.34, 111.16)],
         nome=("Vitinho", "amigo do Bruno desde antes do digital")),
    # o Lucas: 70% de uma loja no 11.11 e +30% todo mês
    dict(tipo="fala", fonte=1385, ini=88.12, fim=98.18,
         nome=("Lucas", "cliente da Convertfy há 2 a 3 meses"), nome_em=0.4,
         insights=[dict(t=96.14, rotulo="Uma loja no 11.11", g="70%", p="do faturamento veio da Convertfy", dur=2.0)]),
    dict(tipo="fala", fonte=1385, ini=135.88, fim=149.16,
         insights=[dict(t=146.0, modo="antes", rotulo="Lucas, todo mês", a="US$ 50 MIL", g="+30%", depois_em=1.4,
                        p="de faturamento com a Convertfy", dur=3.0)]),
    # o Bruno: "não destravei, não. Eu faço porque é obrigado"
    dict(tipo="fala", fonte=1386, ini=35.66, fim=43.50),
    # de Uberlândia: "um dos melhores investimentos da empresa"... "o Single Day veio da ideia do Bruno"
    dict(tipo="fala", fonte=1376, ini=34.52, fim=91.80, tira=[(46.26, 71.78)],
         insights=[dict(t=79.88, modo="frase", rotulo="Ideia do Bruno", linhas=[("SINGLE", 0.05, False), ("DAY", 0.25, True)],
                        p="uma das datas que mais vendem no mês", dur=3.2)]),
    # o chamado pro time, com o QR, e o "no próximo, quero você sentado no carro rosa"
    dict(tipo="fala", fonte=1365, ini=94.04, fim=121.54, tira=[(108.00, 116.70)],
         qr=dict(em=95.0, dur=9.0, chamada=[[("Quanto sua base está", "b")], [("deixando ", "b"), ("na mesa?", "i")]],
                 cta=("ESCANEIE O QR CODE", "E RECEBA A PROJEÇÃO", "DE RECEITA DA SUA LOJA"))),

    # ================================================================ O KART
    dict(tipo="fala", fonte=1389, ini=0.0, fim=19.82, tira=[(2.06, 3.06), (8.98, 15.46)],   # "agora chegou o kart. Tem até troféu, tá?"
         cobertura=[(0.0, 1.1, "d486", 16.5, False)],
         fx=[(0.0, "whoosh-1.mp3", -18)]),
    dict(tipo="fala", fonte=1389, ini=52.86, fim=55.38),                             # "Amor, pegou o troféu?"
    dict(tipo="fala", fonte=1389, ini=308.52, fim=313.30),                          # "é igual fechamento de escola"
    dict(tipo="broll", marca="kart", tomadas=[("d487", 12.0, 3.0), (1391, 0.5, 1.8), ("d486", 16.5, 2.6), (1396, 1.0, 1.6)]),
    # a bolsa de apostas: "tem troféu, tá?", o Vitinho no top 3, "os mais magrinhos é que vão ganhar", o Matheus
    dict(tipo="fala", marca="apostas_kart", fonte=1393, j=1.2, ini=1.70, fim=140.80,
         tira=[(7.60, 8.64), (16.68, 19.44), (24.81, 86.76), (102.40, 125.54), (130.72, 133.08)], fixos=[24.81]),
    dict(tipo="fala", fonte=1394, ini=114.10, fim=124.74, tira=[(117.28, 122.14)]),   # "eu tinha 100 kg... deu lá que eu peso 100"
    dict(tipo="fala", fonte=1397, ini=22.26, fim=28.80),                              # "capacete, protetor de pescoço, colete e macacão"
    dict(tipo="broll", tomadas=[(1395, 84.0, 2.6, {"som": -12})]),
    dict(tipo="fala", fonte=1394, j=0.8, ini=171.84, fim=185.91, fixos=[185.91], tira=[(174.56, 180.98)]),  # "eu tinha 10 anos"... "é só no frear"
    dict(tipo="fala", fonte=1398, ini=2.12, fim=24.12, tira=[(12.00, 18.52)]),       # "tá igual o comercial da Bosch"
    # 220 cavalos contra 13 cv
    dict(tipo="fala", fonte=1351, ini=20.58, fim=27.52),
    dict(tipo="fala", fonte=1401, ini=6.28, fim=16.68, fixos=[16.68], respira=False, fx=[(10.0, "neg-1.mp3", -24)],
         cobertura=[(6.28, 16.64, 1401, 21.7, False)]),
    # o vídeo de segurança da pista em cima das caras de tédio... e a bebida alcoólica
    dict(tipo="fala", marca="seguranca", fonte=1401, ini=36.78, fim=42.30, respira=False,
         cobertura=[(36.78, 39.70, 1401, 25.0, False), (39.70, 42.30, 1400, 6.5, False)]),
    dict(tipo="fala", fonte=1402, ini=46.88, fim=52.02, fixos=[52.02],                               # "tomada de tempo e corrida"
         glossario=[(50.9, "Tomada de tempo", "as voltas cronometradas antes da corrida: quem faz o melhor tempo larga na frente.")]),
    dict(tipo="fala", fonte=1394, ini=185.98, fim=187.18, fixos=[185.98, 187.18], respira=False),             # "É, vai ser engraçado demais."
    # a largada: a batida de "Bandoleros" cai aqui. Drone com movimento firme, sem céu estourado
    dict(tipo="broll", marca="largada", bpm=117.45,
         tomadas=[("d495", 27.8, 4), (1405, 1.6, 2, {"som": -9}), (1406, 0.8, 2, {"som": -9}), ("d493", 2.0, 4),
                  (1407, 0.8, 2, {"som": -9}), ("d497", 4.0, 4), (1408, 0.48, 2, {"som": -9}), ("d498", 70.0, 4),
                  (1409, 0.6, 2, {"som": -9}), ("d490", 22.5, 4), (1410, 0.48, 2, {"som": -9}), ("d498", 83.5, 4),
                  (1412, 10.3, 2, {"som": -9}), ("d493", 10.0, 4), ("d500", 1.0, 4), (1411, 0.8, 4)]),
    # quem rodou, quem ganhou
    dict(tipo="fala", marca="pos_corrida", fonte=1414, j=0.8, ini=0.0, fim=8.50, tira=[(2.72, 5.22)], fx=[(0.0, "giro-1.mp3", -22)]),
    dict(tipo="fala", fonte=1414, ini=22.18, fim=25.68),                             # "esse cara, achei que você tinha rodado"
    dict(tipo="fala", fonte=1413, ini=86.60, fim=108.64, tira=[(93.86, 97.26)]),       # "fui eu que ganhei mesmo"... "rodei umas duas"
    # o placar paga as apostas: Luan 2º, Vitinho 3º, o Matheus "baixinho" 7º
    dict(tipo="broll", marca="placar", tomadas=[(1416, 4.0, 2.4)], fx=[(0.0, "confete-1.mp3", -20)]),
    dict(tipo="fala", fonte=1393, ini=86.76, fim=88.64, respira=False, fx=[(1.9, "ding-1.mp3", -20)],
         insights=[dict(t=88.0, modo="frase", rotulo="Placar", linhas=[("LUAN", 0.05, False), ("2º LUGAR", 0.25, True)], dur=1.6)]),
    dict(tipo="fala", fonte=1393, ini=21.80, fim=24.81, fixos=[24.81], respira=False, fx=[(3.0, "ding-2.mp3", -20)],
         insights=[dict(t=23.4, modo="frase", rotulo="Placar", linhas=[("VITINHO", 0.05, False), ("3º LUGAR", 0.25, True)], dur=1.6)]),
    dict(tipo="fala", fonte=1393, ini=92.20, fim=95.44, respira=False, fx=[(3.3, "neg-1.mp3", -20)],
         insights=[dict(t=94.4, modo="frase", rotulo="Placar", linhas=[("MATHEUS", 0.05, False), ("7º LUGAR", 0.25, True)], dur=1.6)]),
    dict(tipo="broll", tomadas=[(1418, 0.5, 1.4), (1419, 1.0, 1.4)]),
    dict(tipo="fala", marca="trofeu", fonte=1420, j=1.0, ini=1.68, fim=25.52, tira=[(7.06, 17.58), (20.70, 24.18)],
         fx=[(0.0, "conquista-1.mp3", -22)]),                                         # "o mais low profile da turma ganhou"

    # ================================================================ O FIM
    dict(tipo="broll", marca="fim_video", tomadas=[("d501", 4.0, 10.4)],
         vo=[(1317, 59.36, 63.95, 1.0)],                                              # "o próximo vai ser maior que esse"
         qr=dict(em=0.4, dur=9.6, chamada=[[("Diagnóstico ", "b"), ("gratuito", "i"), (" da sua loja", "b")]],
                 cta=("ESCANEIE O QR CODE", "E AGENDE SEU", "DIAGNÓSTICO GRATUITO"),
                 sub="Projeção de receita de 90 dias em 30 minutos de call", foto="equipe-recorte.png")),
    dict(tipo="fim", dur=3.5),
]

TRILHAS = [
    # a intro de cinema até o drop: drone no tom, golpe em cada frase, a voz do Kanye com reverb, risers no drop
    dict(cinema=dict(drone=[41, 48, 56], drop="drop", abre=3.0,
                     golpes=[("co_b", 65), ("co_c", 68), ("co_d", 72), ("co_e", 65), ("co_h", 68), ("co_j", 72)],
                     voz=(os.path.join(MUS, "prep", "ctmn-voz.wav"), 0.0, 5.95)),
         de="gancho", ate="drop", passa=2.6, livre=-6, sob=14, fade_in=0.05, fade_out=0.3,
         nivel=[("co_voz", ("drop", 2.6), -1)]),
    # o drop de "Can't Tell Me Nothing" na logo: sai de dentro do cinema (filtro abrindo em 0,6 s, a cauda do eco por
    # baixo), segue por baixo da cartela e some na primeira fala do Bruno
    dict(arq=CTMN, src=6.171, alinha="drop", de="drop", ate="abertura", passa=2.5, livre=0, fade_in=0.01, fade_out=2.5,
         abafa=(420, 0.6)),
    # o Mini Cooper: verso baixinho no caminho, respira 1,2 s antes de ela ver, e o refrão "If the world was ending"
    # (44,5 s) cai junto do primeiro "Mentira!" dela (o11 191,0 s = porta + 4,30), alto: a música manda na reação
    # (15/11: "não ficou sincronizada com a reação e está muito baixa")
    dict(arq=DWAS, src=44.3, alinha=("porta", 4.10), de="mini", ate="barbie", passa=6.0, livre=-8, sob=17,
         fade_in=1.5, fade_out=4.0, silencio=[(("porta", 2.9), ("porta", 4.15))],
         nivel=[(("porta", 4.15), ("porta", 30.0), 0, 6), ("mini_carro", ("mini_carro", 13.2), 0)]),
    # a noite e o champanhe: "Let the champagne splash" (150,0 s) em cima da rolha
    dict(arq=CTMN, src=126.2, de="noite", ate="telao", passa=1.5, livre=-3, fade_in=0.4, fade_out=1.5),
    dict(arq=CTMN, src=150.0, alinha=("champanhe", 2.9), de="champanhe", ate="fim_dia1", passa=2.0, livre=-2,
         fade_in=0.6, fade_out=2.0, abafa=(500, 2.9)),
    # as apostas pra 2027: o instrumental de "Can't Tell Me Nothing" (sem a voz do Kanye) por baixo das falas
    dict(arq=os.path.join(MUS, "ctmn-instrumental-54s.wav"), src=0.0, de="apostas", ate="fim_apostas", passa=8.0,
         livre=-6, sob=19, fade_in=1.0, fade_out=2.5),
    # o dia 2 de "Lovely Day": a manhã chegando; volta no refrão ("lovely day", 55,3 s) na bola rolando
    dict(arq=LOVELY, src=0.6, de="dia2", ate="dia2_chegada", passa=14.0, livre=-5, sob=16, fade_in=0.8, fade_out=3.0),
    dict(arq=LOVELY, src=55.3, alinha="futevolei", de=("futevolei", -4.0), ate="futevolei", passa=10.0, livre=0, sob=14,
         fade_in=1.5, fade_out=2.5),
    # o kart: a intro de "Bandoleros" no macacão e no briefing, freia na bebida alcoólica; a batida cai na largada
    dict(arq=BANDO, src=0.0, de="kart", ate=("largada", -4.0), livre=-4, sob=15, fade_in=0.3, fade_out=1.5),
    dict(arq=BANDO, src=18.0, alinha="largada", de=("largada", -4.0), ate="trofeu", passa=4.0, livre=0, sob=16, fade_in=1.5,
         fade_out=3.0),
    # o fim: "Can't Tell Me Nothing" volta no drone da pista
    dict(arq=CTMN, src=54.2, de="fim_video", ate="fim", passa=3.5, livre=-2, sob=14, fade_in=1.0, fade_out=3.0),
]
