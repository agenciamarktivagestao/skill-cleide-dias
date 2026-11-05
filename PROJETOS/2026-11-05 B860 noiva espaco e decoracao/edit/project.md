# B860: noiva, espaço do casamento e decoração (substitui o C8155)

## Sessão 1 (05/11/2026): preview v1
**Pedido:**
- usar o B860 com a mesma legenda e edição do C8155, porque ele tem tomadas importantes;
- sem card final, agora e no padrão da Cleide;
- trilha calma e sofisticada como a do 6A5B, e neste vídeo a própria trilha do 6A5B, estendida para o vídeo todo.

**Arquivos:**
- `01 ENVIAR AQUI/B860.MOV`: 29,07 s, 2160×3840, 30 fps. É o mesmo áudio do C8155, idêntico amostra a amostra; de 3,6 s a 18,9 s entram tomadas de decoração.
- `REFERENCIAS/trilha_6A5B.MOV`: montagem só com música. São 14,9 s de trilha + 3,7 s mudos; piano em arpejo, Ré maior, ~96 BPM, compasso de 2,51 s.
- O C8155 foi para a pasta do projeto dele.

**Tomadas de decoração** (trocas do bruto):

| Tempo | Tomada |
|---|---|
| 3,60 s | noiva |
| 6,53 s | mesa do bolo |
| 9,20 s | corredor da cerimônia |
| 12,53 s | palco iluminado |
| 15,23 s | hall com espelho |
| 17,47 s | corredor do jardim |
| 18,90 s | volta a Cleide |

**Cortes:**
- respiro de 0,75 s (3,22→3,97: o corte cai na troca Cleide → noiva);
- respiro de 0,44 s (18,56→19,00: jardim → Cleide).
- O respiro de 0,48 s (12,76–13,24) ficou, para não cortar a tomada do palco.
- Fim em 28,53 s, no sorriso: **27,37 s**, sem card final.

**Zoom:**

| Trecho | Zoom |
|---|---|
| gancho | 1,15 → 1,28 |
| tomadas de decoração | 1,0 ↔ 1,07, alternando, centradas |
| CTA | 1,35 → 1,2 |
| fim | 1,2 → 1,3 |

O `headroom` é o mesmo do C8155 (130 px).

**Transições:**
- desfoque nos 2 cortes e nas 5 trocas de tomada (estas mais leves e sem som);
- brilho de luz na entrada (2,93 s) e na saída (17,53 s) das imagens de decoração.

**Legenda:** a mesma do C8155. Nas imagens de decoração fica centrada (y 1040). A frase da antiga tela clara virou legenda ("para criar um projeto" / "que *valoriza*" / "cada espaço"), para não cobrir as tomadas.

**Lista em pílulas:** "A entrada / A cerimônia / Os pontos de destaque" sobre o corredor da cerimônia e o palco (8,73–12,47 s).

**Trilha:** 6A5B estendida pelo `music_extend.py` de 14,87 s para 27,34 s.
- Emendas: repete 4 compassos (12,81 → 2,87 s, forma de onda 0,82) e 1 compasso (6,82 → 4,29 s, 0,80).
- O final original fica no fim do vídeo.
- Conferido: sem estalo nem salto de nível nas emendas.
- Nível: −18 dB (≈17 dB abaixo da fala) e +6 dB depois da última palavra.

**Efeitos:** 7, todos suaves: brilho no "Noiva!", 2 sopros nos cortes, 3 toques nas pílulas e o clique.

**Revisão:**
- `selfeval` tudo OK: 821 quadros, sincronismo −0,5 ms, margem OK, legenda 20/20, cor igual ao bruto (0,14 nível), −14,4 LUFS / −1,9 dBTP.
- Corrigido antes de mandar: a legenda das tomadas de decoração saía picada ("criar" / "cada" / "espaço" sozinhos). A causa era um bloco de 3 linhas e uma quebra no tempo errado.

**Aguardando:** retorno do preview e confirmação da licença da trilha (se for música comercial).

## Sessão 1, ajuste 1 (05/11/2026): preview v2
**Pedido:** "as legendas coloque uma sombra atrás para visualizar melhor".

**Feito:**
- A legenda ganhou sombra projetada firme embaixo das letras e uma mancha escura suave atrás do bloco inteiro (letras engrossadas e desfocadas, 62 %).
- O texto das pílulas também ganhou a sombra projetada.
- Antes de aplicar, testei 3 intensidades sobre o vestido da noiva, a mesa de flores e a camisa da Cleide.
- O `selfeval` passou de novo (821 quadros, margem OK, −14,4 LUFS).
- A versão anterior ficou em `preview_v1.mp4` / `edl_v1.json`.
