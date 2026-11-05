# Cleide Dias — base para a skill

Acervo montado em 05/11/2026 a partir da pasta `Downloads/Cleide Dias`, no mesmo formato da base da Fire Moda Fitness ([skill-fire-moda-fitness](https://github.com/agenciamarktivagestao/skill-fire-moda-fitness)). A pasta de trabalho não foi alterada. Esta é uma base documental e técnica; a skill instalável ainda deverá ser criada e validada.

Cliente: Cleide Dias, decoração de eventos (casamentos: entrada, cerimônia, pontos de destaque e recepção). Vídeos verticais para Reels, Stories e TikTok.

## Comece aqui

1. [ESTILO CLEIDE.md](ESTILO%20CLEIDE.md): regras da Cleide, com os pedidos da agência de 04 e 05/11/2026.
2. [Resumo visual do padrão](REFERENCIAS/padrao_cleide.jpg): os destaques da legenda e a lista em pílulas, em 8 quadros do B860. Ainda não há manual de marca.
3. [Modelo de edição](MODELOS%20CLEIDE/LEIA-ME.md): padrão 1, legenda palavra a palavra. Preservar e trabalhar em cópias.
4. `PROJETOS/*/edit/project.md`: histórico de pedidos, decisões, ajustes e pendências. Os JSONs guardam receitas e transcrições; versões antigas são contexto histórico.
5. [Orientações para criar a skill](BASE-SKILL/ORIENTACOES.md).
6. [Inventário completo](BASE-SKILL/inventario.json): 139 arquivos encontrados, com situação, motivo da exclusão, tamanho, destino nesta base e SHA-256 dos 103 originais enviados ou adaptados.

## Nomes nesta base

A pasta de trabalho usa nomes curtos. Aqui eles seguem o padrão da Fire:

| Pasta de trabalho | Nesta base |
|---|---|
| `ESTILO.md` | `ESTILO CLEIDE.md`, reorganizado no formato do `ESTILO FIRE.md` |
| `MODELO/` | `MODELOS CLEIDE/PADRAO 1 - legenda palavra a palavra/` |
| `CLAUDE.md`, `AGENTS.md` e `LEIA-ME.md` | este README, os `LEIA-ME.md` de `MODELOS CLEIDE/` e `BASE-SKILL/ORIENTACOES.md` |
| trilha em `REFERENCIAS/` | `TRILHAS/` (só a descrição; ver abaixo) |

No inventário, `enviado` é cópia sem alteração e `adaptado` é um documento cujo conteúdo foi reescrito nos arquivos do campo `destino`. Os scripts, EDLs e históricos foram copiados sem alteração; por isso ainda citam `MODELO/` e `REFERENCIAS/trilha_6A5B.MOV`, os nomes da pasta de trabalho.

## Conteúdo e limites

Foram incluídos documentos, scripts, JSONs, imagens (folhas de contato, quadros das bordas dos cards e margem de segurança) e as fontes Prompt, com o texto da licença OFL.

Não foram incluídos vídeos brutos/finais/previews, áudio intermediário ou específico de projeto, caches e metadados do macOS. Também ficaram de fora:
- `REFERENCIAS/referencia_legenda.mp4`: o vídeo de referência da legenda, de terceiros;
- `REFERENCIAS/trilha_6A5B.MOV`: a trilha "calma e sofisticada" enviada pela agência. É um vídeo de 137 MB (acima do limite de 100 MB do GitHub), e a licença da música não foi confirmada; este repositório é público.

As receitas apontam para essas mídias locais ausentes: este repositório não é um backup integral nem renderiza os projetos sem elas. As fontes da legenda (Helvetica Neue e Brush Script MT) são do macOS e também não vêm aqui; sem elas, o `brand.font()` usa a Prompt.

A integridade dos arquivos copiados é verificada por SHA-256; os JSONs foram analisados. Nenhum script de edição foi executado e nenhuma renderização foi validada nesta montagem.
