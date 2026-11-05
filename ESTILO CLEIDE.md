# Estilo de edição: Cleide Dias

Padrão montado em 04/11/2026 no primeiro vídeo da cliente (C8155), a partir da referência de legenda (`REFERENCIAS/referencia_legenda.mp4`), e ajustado em 05/11/2026 no B860 (o mesmo vídeo, com imagens de decoração). **Ainda sem aprovação final:** o preview v2 do B860 aguarda o retorno da agência. Registre aqui tudo o que a cliente aprovar ou recusar.

**Modelo (05/11/2026): `MODELOS CLEIDE/`.** Por enquanto há um padrão de edição. **Não apague nem substitua os arquivos dele**, nem o projeto de onde saiu (`PROJETOS/2026-11-05 B860 noiva espaco e decoracao/`).
- `MODELOS CLEIDE/PADRAO 1 - legenda palavra a palavra/`: legenda palavra a palavra com destaques (cursiva, negrito, pílula e sublinhado), zoom suave contínuo, imagens de decoração e trilha de arquivo estendida (`build.py`).
- Para um vídeo novo, copie a pasta do padrão para `PROJETOS/<projeto>/edit/` e trabalhe na cópia. O passo a passo está em `MODELOS CLEIDE/LEIA-ME.md`.
- O `MODELO/`, o `CLAUDE.md` e o `AGENTS.md` da pasta `Downloads/` são da Central Norte: não usar.
- Resumo visual: `REFERENCIAS/padrao_cleide.jpg`.

Para rodar no Mac: `~/.venvs/edicao/bin/python` e o ffmpeg do Homebrew. A transcrição usa o Parakeet (sherpa-onnx), com os modelos em `~/models`.

## Cliente e marca (ainda sem manual de marca)
- **Cleide Dias:** especialista em decoração de eventos (casamentos: entrada, cerimônia, pontos de destaque e recepção).
- **Tom:** acolhedor, elegante e direto, falando com a noiva.
- **Gravação:** em pé, em casa, na frente de um quadro de flores (rosa/magenta), com camisa clara.
- **CTA falado:** "Clique no WhatsApp e conheça as lindas decorações…".
- **Logo e @ do Instagram:** ainda não vieram. Sem logo fixo e sem card final.

### Cores
- **Branco `#ffffff`:** legenda, com a sombra `#1c1410` atrás (ver Legenda). Sem ela, o branco some na camisa clara da Cleide, no vestido e nas flores brancas.
- **Pílula:** cinza quente translúcido `#544c46` (~70 %), com texto branco.
- **Papel `#f7f3ed`:** fundo da tela clara, com sombras de folhagem `#786c60` balançando devagar.
- **Grafite `#2e2a28`:** texto na tela clara.
- **Champanhe/dourado `#be9a62`:** círculo tracejado da tela clara.
- **Rosé `#e29696` + dourado claro:** só no brilho de luz das transições (combina com as flores do quadro).

### Fontes
- **Helvetica Neue** (macOS): Medium na legenda; Bold nos negritos e no texto da tela clara.
- **Brush Script MT** (macOS): a cursiva grossa dos destaques ("Noiva!", "decoração", "valoriza", "lindas decorações").
- **Fora deste Mac:** as duas são fontes do sistema. Se faltarem, o `brand.font()` usa a Prompt (OFL, em `assets/fonts/` do modelo). Para fontes livres, dá para trocar por Inter + Lobster (Google Fonts), com o OK da agência.

## Nomes e termos (conferir sempre na legenda)
- "Cleide", "Cleide Dias" e "WhatsApp".
- "Clique": no C8155/B860 o motor ouviu "Cli".
- Termos de decoração: entrada, cerimônia, pontos de destaque, recepção e noiva.
- As correções fixas ficam em `FIXES`, no `transcribe.py`. As de um vídeo só vão no EDL, em `"captions": {"fix": {...}}`.

## Margem de segurança
Usar `assets/margem_seguranca.jpeg` do modelo (a mesma de `REFERENCIAS/Margem de segurança.jpeg`). No vídeo de 1080×1920, a área livre vai de x 91 a 988 e de y 100 a 1681. Legenda, pílulas e tela clara ficam sempre dentro dela, e ela nunca aparece no vídeo. O `selfeval.py` confere pelo `bboxes.json`.

## Regras pedidas pela agência
Pedidos de 04 e 05/11/2026. Já estão no modelo, mas falta a aprovação do preview.
- **Não mexer na cor** (04/11): a cor fica idêntica à do bruto, sem filtro, LUT ou ajuste. O `selfeval.py` confere a cor na mesma janela de zoom.
- **Cortar só os respiros**, medidos no áudio (RMS a cada 10–20 ms, respiro abaixo de −45 dB), com ~40 ms de folga de cada lado. Os tempos do transcript são aproximados (±0,15 s); o áudio manda.
  - No C8155/B860 saíram os respiros de 0,75 s e 0,44 s.
  - O de 0,48 s (12,76–13,24 s) ficou no B860, porque cairia no meio da tomada do palco.
- **Legenda no estilo da referência** (04/11), **com sombra atrás** (05/11: "para visualizar melhor"). Ver Padrão 1 › Legenda.
- **Efeitos sonoros simples**, nada exagerado (04/11).
- **Zoom in e zoom out suaves** e **transições suaves** (04/11).
- **Nada de "teto" no alto do vídeo se não tiver título** (04/11):
  - sem logo e sem faixa fixa em cima;
  - enquadramento sem sobra de parede em cima da cabeça.
  - Interpretado assim; confirmar com a agência.
- **Sem card final** (05/11, "não quero card final nos padrões dela"):
  - o vídeo acaba ~0,4–0,5 s depois da última palavra, no sorriso dela, com `"hold": 0` e sem o card `end`;
  - o card final antigo ("Cleide Dias · Decoração de eventos · Fale no WhatsApp") saiu do `cleide_cards.py` do modelo. O código continua no `cleide_cards.py` do projeto C8155, caso volte a ser pedido.
- **Trilha "calma e sofisticada"** (05/11), como a do `REFERENCIAS/trilha_6A5B.MOV` (piano em arpejo, Ré maior, ~96 BPM). No B860, essa mesma trilha foi estendida para o vídeo todo.
- **Imagens de decoração no bruto** (05/11, B860): são importantes, então **nada pode cobri-las** (sem tela clara por cima).
- **C8155 → B860** (05/11): é a mesma fala, mas o B860 tem as tomadas de decoração. O C8155 foi substituído e fica só como histórico.

## Padrão 1: legenda palavra a palavra (modelo atual)
Vertical 1080×1920 a 30 fps (Reels, Stories e TikTok). Modelo em `MODELOS CLEIDE/PADRAO 1 - legenda palavra a palavra/` (`build.py`).

### Imagens de decoração no bruto
- O bruto pode vir já montado com tomadas dos eventos no meio da fala. No B860: noiva, mesa do bolo, corredor da cerimônia, palco, hall e jardim.
- Ache as trocas de tomada com `ffmpeg -vf "select='gt(scene,0.25)',metadata=print"`.
- Faça um trecho do EDL por tomada, com `"broll": true`, emendando sem cortar o áudio.
- Se possível, corte os respiros nas trocas de tomada do próprio bruto.

### Enquadramento e zoom (sem "teto")
- **Zoom suave contínuo:** cada tomada desliza devagar de `zoom` para `zoom_to`, com ease senoidal ao longo do trecho inteiro.
  - Com a Cleide: alterne zoom in e zoom out (1,12 a 1,35), com close (1,3–1,35) no gancho e no CTA.
  - Nas imagens de decoração: zoom bem leve (1,0 ↔ 1,07), `"anchor": [540, 960]`. Alterne in e out, emendando o fim de uma tomada no começo da outra.
- **Cabeça perto do topo:** `"headroom": {"head_src": 330, "head_out": 130, "x": 555}` no EDL.
  - `head_src`: alto do cabelo no bruto (em 1080×1920, zoom 1);
  - `head_out`: onde ele fica no vídeo.
  - O `build.py` calcula o centro de cada quadro para o zoom "girar" em torno da cabeça, sem sobrar parede em cima.
  - Meça o `head_src` de novo a cada gravação nova. Trecho com `"anchor"` (b-roll) ignora o `headroom`.
- Entre trechos com enquadramentos diferentes, o zoom desliza 0,5 s, centrado na emenda.

### Transições
- **Desfoque:** em todo corte (`"trans_in": "blur"` no trecho), a imagem desfoca e volta em 0,4 s, com o pico na emenda. Nos cortes de respiro há um sopro suave.
- **Troca de tomada das imagens de decoração:** também com desfoque, mais leve (`{"type": "blur", "blur": 11}`) e **sem som** (o som entra sozinho só onde o original pula).
- **Brilho de luz (`leak`):** mancha rosé + dourada atravessando a tela em 0,6 s.
  - No máximo 2 por vídeo, sutil (força 0,42): o rosto continua visível.
  - No B860, entrou na entrada e na saída das imagens de decoração.
- **Tela clara:** entra e sai desfocando (0,25 s), com a base desfocando por baixo (`"transitions"`).

### Legenda (`animations/captions_cleide.py`, `"style": "CLD"`)
Tirada de `REFERENCIAS/referencia_legenda.mp4`:
- **Blocos curtos:** 1–2 linhas, até 5 palavras, centralizados.
  - Com a Cleide, ficam **na altura do peito**, a partir de 110 px abaixo do meio do pescoço (`person.json`).
  - Nas imagens de decoração, ficam centrados em y 1040.
- **Palavra a palavra:** cada palavra entra no tempo da fala, desfocada e transparente → nítida (5 quadros). A linha desliza para o centro a cada palavra nova.
- **Letra:** Helvetica Neue Medium 58, branca. Sem vírgula e sem ponto (`?` e `!` ficam).
- **Sombra atrás da legenda** (pedido de 05/11, "para visualizar melhor"):
  - sombra projetada firme embaixo de cada letra;
  - mancha escura suave atrás do bloco inteiro: as letras engrossadas e bem desfocadas, a 62 % (`SHADOW_K` em `captions_cleide.py`);
  - a mancha acompanha as palavras conforme entram e fica embaixo do fundo das pílulas;
  - lê na camisa clara, no vestido branco e nas flores brancas. O halo leve da 1ª versão sumia nas imagens claras.
- **Destaques** (use pouco, 1 por frase no máximo):
  - `script`, **cursiva:** Brush Script 2,45× na linha de baixo, encostando na de cima. Entra desfocada e 12 % maior.
  - `bold`, **negrito:** Helvetica Neue Bold na mesma linha.
  - `pills`, **pílula:** a palavra numa pílula cinza translúcida ("WhatsApp").
  - `underline`, **sublinhado:** traço branco desenhado à mão embaixo da expressão ("o seu casamento").
- **Troca de bloco:** o anterior some desfocando, 2 quadros antes do novo entrar.
- **Ajustes de transcript no EDL:**
  - `fix`: correções;
  - `breaks`: onde começa um bloco (tempo do ORIGINAL). Um bloco que daria 3 linhas é partido e a 3ª linha fica sozinha, então quebre antes;
  - `joins`: a frase continua, apesar do ponto do transcript;
  - `shift`: acerta o tempo das palavras de um trecho.

### Grafismos (`animations/cleide_cards.py`)
- **pills:** lista em pílulas empilhadas; cada uma entra quando é falada (`"sync": true` acha o tempo no transcript).
  - Do pescoço para baixo, ou centrada sobre as imagens de decoração. Esconde a legenda no trecho.
  - Ex.: "A entrada / A cerimônia / Os pontos de destaque".
- **screen:** tela clara com a frase em grafite Bold, palavra a palavra, uma palavra em cursiva (`*palavra*`) e o **círculo tracejado dourado** em volta dela.
  - No máximo 1 por vídeo, numa frase-chave.
  - **Nunca por cima das imagens de decoração.** No B860 ela saiu e virou legenda.
- **leak:** o brilho de luz da transição.
- **Sem card final** (05/11) e **sem logo fixo** no vídeo.

### Som
- **A voz** é a protagonista.
- **Trilha "calma e sofisticada"** (05/11): arquivo de música enviado pela agência, no estilo do `REFERENCIAS/trilha_6A5B.MOV`.
  - No EDL: `"music": {"file": "…", "db": -18, "end_boost_db": 6}`. Sob a fala, a trilha fica ~17 dB abaixo.
  - Se for mais curta que o vídeo, o `music_extend.py` estende sozinho: repete compassos inteiros onde a harmonia e o timbre se repetem, cruza 70 ms e mantém o final original da música.
  - No B860: de 14,9 s para 27,3 s, repetindo 4 compassos (12,81 → 2,87 s) e 1 compasso (6,82 → 4,29 s). O relatório fica em `music_ext.json`.
  - Se a trilha for comercial, o Instagram pode silenciar o post: confirmar a licença com a agência.
  - A trilha sintetizada "calm" (`sound.py`) fica só de reserva, para quando não houver arquivo.
- **Efeitos:** sintetizados, poucos e suaves, ~8–14 dB abaixo da voz, sempre ligados a algo na tela.
  - Brilho (shimmer) na cursiva do gancho.
  - Sopro suave ("air") nos cortes de respiro.
  - Toque leve em cada pílula da lista.
  - Clique no "Clique".
  - As outras cursivas e as trocas de tomada ficam mudas. No B860 foram 7 efeitos em 27 s.
- **Master:** −14 LUFS, pico ≤ −1,5 dBTP.

## Cuidados
- **Nomes certos na legenda** (ver Nomes e termos).
- **Tempos do 2º trecho do transcript:** o transcript divide o áudio em pedaços, e a 1ª palavra de um pedaço pode vir ~0,15 s adiantada. Acerte com `shift`.
- **Legenda picada nas imagens de decoração:** no B860 saíam palavras sozinhas ("criar" / "cada" / "espaço"), por causa de um bloco de 3 linhas e de uma quebra no tempo errado. Confira os `breaks`.
