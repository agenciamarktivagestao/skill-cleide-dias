# Padrão 1: legenda palavra a palavra

Montado em 04/11/2026 no C8155 e ajustado em 05/11/2026 no B860: sem card final, trilha de arquivo estendida, imagens de decoração e sombra na legenda. Os arquivos são os do `MODELO/` da pasta de trabalho em 05/11/2026, iguais aos do `edit/` do B860 depois do ajuste 1 (preview v2). **Ainda aguarda a aprovação da agência.**

## Como fica
- **Legenda** (`"style": "CLD"`) no estilo de `REFERENCIAS/referencia_legenda.mp4`: blocos curtos, palavra a palavra (desfocada → nítida), Helvetica Neue branca com sombra atrás, na altura do peito (do pescoço para baixo).
- **Destaques:** cursiva grande (Brush Script), negrito, pílula translúcida e sublinhado à mão. No máximo um por frase.
- **Zoom suave contínuo** em cada tomada (1,12–1,35 com a Cleide; 1,0 ↔ 1,07 nas imagens de decoração), com a cabeça perto do topo (`"headroom"`): sem "teto".
- **Imagens de decoração** (`"broll": true`) inteiras, sem nada por cima além da legenda e da lista em pílulas.
- **Transições:** desfoque em cada corte; brilho de luz rosé/dourado, no máximo 2 por vídeo.
- **Grafismos:** lista em pílulas e tela clara com o círculo tracejado dourado (1 por vídeo, nunca sobre as imagens de decoração).
- **Som:** trilha calma de arquivo, estendida até o fim do vídeo, e poucos efeitos suaves.
- Sem card final, sem logo fixo e sem mexer na cor.

## Arquivos
- `build.py`: monta tudo. `--preview` gera o `preview.mp4`; sem a opção, gera o `final.mp4`; `--force` refaz depois de mudar script ou asset.
  - Etapas: base (cortes + zoom suave + desfoque nas transições + quadro congelado) → `person.py` → grafismos e legenda (quando o EDL muda) → mixagem → composição.
  - Ele guarda as versões anteriores: `preview_vN.mp4` + `edl_vN.json`.
- `make_cuts.py`: `edl.json` inicial. Corta as pausas ≥ 0,3 s e põe um zoom suave por tomada. Adapte as constantes a cada vídeo (não copie números de outro projeto).
- `transcribe.py`: transcrição com tempo por palavra (Parakeet TDT 0.6B v3 no sherpa-onnx; reserva: faster-whisper). As correções fixas ficam em `FIXES`.
- `person.py`: rosto quadro a quadro (OpenCV Haar) → `person.json`, para a legenda ficar do pescoço para baixo. Trechos `broll` não procuram rosto. O `build.py` chama sozinho.
- `music_extend.py`: estende a trilha até a duração do vídeo repetindo compassos (cache em `music_ext.wav`, relatório em `music_ext.json`).
- `selfeval.py preview.mp4 base.mkv`: confere quadros, áudio, sincronismo, margem, legenda do pescoço para baixo, cor e loudness, e gera `contact.jpg` e `card_edges.jpg`.
- `animations/captions_cleide.py` (legenda → `captions.mov`) e `animations/cleide_cards.py` (pílulas, tela clara e brilho → `cards/`). A lista de campos de cada um está no começo do arquivo.
- `sound.py`: efeitos sintetizados e a trilha "calm" de reserva. `brand.py`: cores, fontes, margem e utilitários. `frames.py`: grava quadros PIL em vídeo via ffmpeg.
- `assets/`: fontes Prompt (reserva, OFL), `margem_seguranca.jpeg` e `safe_zone_mask.png`.
- `edl_exemplo.json`: o EDL do B860, com `headroom`, trechos de b-roll, `captions` (destaques, `fix`, `breaks`, `joins` e `shift`), lista em pílulas, brilhos e trilha.
  - O `"_leia"` do começo explica de qual vídeo é cada tempo (ORIGINAL ou FINAL) e traz o exemplo da tela clara.
  - O `"source"` é um marcador: troque pelo caminho completo do bruto.

## Trilha no EDL
```
"music": {"file": "../../../REFERENCIAS/trilha_6A5B.MOV", "db": -18, "end_boost_db": 6}
```
- O caminho é relativo ao `edit/` do projeto. O arquivo pode ser um vídeo com a trilha (como o 6A5B) ou só o áudio.
- Testado no B860: a trilha de 14,87 s foi estendida para 27,34 s, sem estalo nem salto de nível. O preview ficou com −14,4 LUFS e pico de −1,9 dBTP.
- Sem `"file"` (ou sem `"music"`), o `build.py` usa a trilha sintetizada "calm" do `sound.py` (−24 dB por padrão).

## Ambiente (Mac)
- Python: `~/.venvs/edicao/bin/python` (Python 3.12 com PIL, numpy, scipy, OpenCV, onnxruntime, sherpa-onnx e PyMuPDF).
- ffmpeg do Homebrew. Ele não tem `drawtext`: texto em imagem sempre via PIL.
- Modelos em `~/models`: Parakeet (transcrição), Haar (rosto) e U²-Net (recorte da pessoa). Se faltarem, os scripts baixam do GitHub na 1ª vez.

## Rodar
```
PY=~/.venvs/edicao/bin/python
$PY build.py --preview
$PY selfeval.py preview.mp4 base.mkv
```
O `selfeval.py` confere:
- quadros = EDL, áudio = vídeo e o sincronismo em cada corte;
- margem de segurança e legenda/pílulas do pescoço para baixo;
- etiquetas BT.709 e a cor igual à do bruto, na mesma janela de zoom;
- −14 LUFS e pico ≤ −1,5 dBTP.

Depois, **abra o `contact.jpg` e o `card_edges.jpg`** e extraia quadros cheios nos destaques. Confira:
- legenda legível na camisa clara e nunca no rosto;
- pílulas sem encostar;
- círculo da tela clara sem cortar as outras linhas;
- brilho de luz sem lavar a imagem;
- nada sobrando em cima da cabeça.

## Detalhes técnicos já resolvidos (não desfazer)
- **Cortes no grid de quadros:** a fonte vira 30 fps antes do `trim` por número de quadro. O áudio de cada trecho é cortado nos mesmos tempos, com `aresample first_pts=0 + apad + atrim`. Desvio medido: 0,5 ms.
- **Concat da base:** depois do `concat` vem `settb=1/30,setpts=N,fps=30:eof_action=pass`, antes do `tpad`. Sem isso, o quadro congelado sumia.
- **Zoom suave (04/11):**
  - o ffmpeg corta numa tela k × 1080×1920 sem zoom, e o `build_base` aplica o zoom de cada quadro com subpixel (`cv2.warpAffine`);
  - dentro do trecho, o zoom vai de `zoom` a `zoom_to` (ease senoidal, escala log);
  - com `"headroom"`, o centro é recalculado a cada quadro para o alto da cabeça ficar parado;
  - entre trechos diferentes, há um ease de 0,5 s centrado na emenda.
- **Desfoque de transição:** aplicado na base, quadro a quadro (`cv2.GaussianBlur`, croma com metade do raio), em sino com o pico na emenda. Os dois quadros da emenda ficam com o mesmo desfoque.
- **Cards:** entram meio quadro antes, com `eof_action=repeat`, e a saída usa `-frames:v` igual ao total do EDL. O brilho (`leak`, `"top"`) vai por cima da legenda.
- **B-roll (05/11):** trecho com `"broll": true` não procura rosto (`person.py`).
  - O detector achava o rosto da noiva, e a suavização "emprestava" o rosto da Cleide às tomadas vizinhas.
  - Nesses trechos, a legenda fica centrada em `cy`.
  - O sopro automático da transição só toca onde o original pula (corte de respiro), não nas trocas de tomada que já vêm no bruto.
- **Trilha estendida (05/11):** o `music_extend.py`:
  - estima o compasso pelas melhores emendas curtas;
  - procura emendas de n compassos em ataques de nota (harmonia + timbre + ritmo, e forma de onda ±25 ms);
  - escolhe 1–2 pulos que somam o que falta, sem pular de dentro dos 2 s finais;
  - cruza 70 ms com potência constante.

  Conferido no B860: sem estalo e sem salto de nível nas emendas.
- **Rosto (`person.py`):** seguido pelo caminho (mediana móvel de ±12 quadros); falsos rostos longe do caminho são descartados.
- **Legenda:** a posição usa o pescoço no intervalo em que o bloco fica na tela (`t`–`t_end` no `bboxes.json`, que o `selfeval.py` também usa). Na mesma tomada, a altura não pula.
- **Cor igual à do bruto:**
  - a entrada do pipe é declarada BT.709 e a saída leva as 3 etiquetas;
  - grafismos RGBA viram vídeo com conversão explícita BT.709;
  - o `selfeval.py` recorta a mesma janela de zoom do bruto e reprova diferença > 0,8 nível.
- **Composição:** `brand._safe_composite` cola sem máscara (com máscara, a transparência saía ao quadrado).
- **Loudnorm:** duas passadas com alvo −2 dBTP, para o AAC não passar de −1,5.
