# Modelos de edição da Cleide Dias

Esta pasta tem o **modelo de edição** da Cleide Dias (05/11/2026). **Não apague nem substitua estes arquivos.** Para editar um vídeo novo, copie o modelo para o projeto e trabalhe na cópia.

| Modelo | Quando usar | Situação |
|---|---|---|
| `PADRAO 1 - legenda palavra a palavra/` | Todos os vídeos da Cleide: fala, com ou sem imagens de decoração no meio. Legenda palavra a palavra com cursiva, negrito, pílula e sublinhado; zoom suave; trilha de arquivo estendida | Montado no C8155 (04/11/2026) e no B860 (05/11/2026). O preview v2 do B860 aguarda aprovação |

As regras estão no `ESTILO CLEIDE.md`, na raiz da pasta. A trilha atual é a do `REFERENCIAS/trilha_6A5B.MOV` da pasta de trabalho (ver `TRILHAS/`).

## Começar um vídeo novo
1. **Crie o projeto:** `PROJ="PROJETOS/<AAAA-MM-DD> <nome do arquivo> <tema curto>"`, com as fotos em `$PROJ/fotos/`.
   - **Ainda não mova o bruto:** ele sai de `01 ENVIAR AQUI/` só na aprovação. Até lá, o `"source"` do EDL aponta para ele com o caminho completo.
   - Trilha nova enviada pela agência: em `REFERENCIAS/` (ou no projeto), apontada em `"music": {"file": …}`.
2. **Copie o modelo** para `edit/`:
   ```
   cp -Rp "MODELOS CLEIDE/PADRAO 1 - legenda palavra a palavra/." "$PROJ/edit/"
   ```
   Na pasta de trabalho do Mac, o modelo ainda se chama `MODELO/`: `cp -R MODELO "$PROJ/edit"`.
3. **No `edit/`**, rode com `PY=~/.venvs/edicao/bin/python`:
   - `$PY transcribe.py <bruto>` → `transcript.json` + `transcript.txt` (pt, tempo por palavra; leva segundos). Leia o `transcript.txt` e corrija os nomes (ver `ESTILO CLEIDE.md`).
   - `$PY make_cuts.py <bruto>` → `edl.json`, com os cortes de pausa (≥ 0,3 s) e um zoom suave por tomada. Confira cada corte no áudio: só respiros (abaixo de −45 dB), com ~40 ms de folga.
   - **Olhe os quadros** (extraia alguns com ffmpeg) e meça o alto do cabelo para o `"headroom"`: nada de "teto" em cima da cabeça.
   - **Imagens de decoração no bruto:** ache as trocas de tomada com `ffmpeg -vf "select='gt(scene,0.25)',metadata=print"`. Faça um trecho por tomada com `"broll": true`, `"anchor": [540, 960]`, zoom leve e `"trans_in": {"type": "blur", "blur": 11}`. Corte os respiros de preferência nas trocas de tomada.
   - Complete o `edl.json` copiando os campos do `edl_exemplo.json` do modelo: `"style": "CLD"` na legenda, `"hold": 0` e sem o card `end`.
4. **Plano em português:** duração, cortes, zooms, destaques da legenda, lista/tela clara/brilho e trilha. **Espere a aprovação.** Se o usuário pedir o preview direto, renderize e mostre o plano junto com ele.
5. **Renderize:** `$PY build.py --preview` (um vídeo de 30 s leva ~50 s). Se mudou só script ou asset, use `--force`.
6. **Revise antes de mostrar:** `$PY selfeval.py preview.mp4 base.mkv`, abra o `contact.jpg` e o `card_edges.jpg` e extraia quadros cheios nos destaques. A lista do que conferir está no `LEIA-ME.md` do padrão. Depois, mande o preview ao usuário (no Claude, com `SendUserFile`); ele fica salvo em `$PROJ/edit/preview.mp4`.
7. **Ajustes:** o `build.py` guarda as versões anteriores (`preview_v1.mp4`, `edl_v1.json`, …). A base só é refeita se os cortes, o zoom ou as transições mudarem.
8. **Na aprovação:**
   - `$PY build.py` → `final.mp4`; rode o `selfeval.py` de novo.
   - Salve um hardlink em `02 FINALIZADOS/<AAAA-MM-DD> <nome> <tema>.mp4` (`ln`) e mova o bruto de `01 ENVIAR AQUI/` para `$PROJ/` (atualize o `"source"` do EDL).
   - Registre a sessão em `$PROJ/edit/project.md`: pedido, decisões, ajustes e aprovação.
   - Com a permissão do usuário, apague os intermediários pesados: `base.mkv`, `captions.mov`, `cards/`, `person_mask.mkv` e `mix_raw.wav`.

## Retomar um projeto antigo
Use `$PROJ/edit/edl.json`, o `transcript.json`, os brutos e as fotos do projeto. Se o modelo tiver mudado, copie os scripts novos para `$PROJ/edit/` e rode o `build.py --force`.

## O que mudar no modelo
Quando a agência aprovar uma regra nova, atualize o modelo **e** o `ESTILO CLEIDE.md`. Os projetos antigos continuam com os arquivos que usaram. Um padrão novo (outro estilo de legenda, por exemplo) vira uma pasta `PADRAO 2 - …` ao lado do padrão 1, sem apagar o 1.
