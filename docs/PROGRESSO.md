# Progresso do projeto

> Este arquivo é a fonte da verdade sobre o andamento de **todas as partes**.
> Qualquer pessoa (ou IA) que for mexer no código deve LER ESTE ARQUIVO PRIMEIRO.

**Como usar:**
1. Antes de trabalhar numa parte, leia a seção dela aqui e a seção dela em [divisao-tarefas.md](divisao-tarefas.md).
2. Ao terminar cada tarefa: marque o item no checklist, atualize o status, a "última atualização" e o "próximo passo" da parte, e adicione uma entrada no log (no topo).
3. Tarefa nova vai para o checklist. Se algo travar, marque `[!]` e explique nas pendências da parte.
4. Nunca apague entradas do log. Correções viram uma nova entrada.
5. Decisões técnicas (bibliotecas, formatos, nomes) vão para a tabela de decisões.
6. Cada parte mexe só nos próprios arquivos; mudança nos contratos compartilhados é registrada como decisão.

Legenda: [ ] pendente · [~] em andamento · [x] concluído · [!] bloqueado
Ao concluir um item, acrescente na própria linha: data, autor e arquivos alterados.
Ex.: - [x] 3.2 Validar campos obrigatórios do JSON — 2026-10-08, Lucas — `src/preparar_dados.py`

## Visão geral

| Parte | Status | Quem | Última atualização |
|-------|--------|------|--------------------|
| 1 — Dados e unitarização | Concluído (falta só abrir o pull request, tarefa 9.3) | Franklyn/Lucas | 2026-10-07 19:01 |
| 2 — Base de conhecimento e busca | Não iniciado | a definir | — |
| 3 — Geração com LLM e validação | Não iniciado | a definir | — |
| 4 — Orquestração, configuração e Excel | Fica para o final | a definir | — |
| 5 — Avaliação das respostas da IA | Fica para o final | a definir | — |

---

## Parte 1 — Dados e unitarização

### Resumo
- **Objetivo:** entregar as 59 dissertações limpas, com `id` (D001 a D059) e divididas em frases numeradas (F1, F2…), que são as unidades citadas como evidência pela IA. Também montar o corpus de calibração (as 20 dissertações de 2022, de fora das 59).
- **Entradas / Saídas:** `data/brutos/dissertacoes.json` (original, só leitura) → `data/corpus.json` → `list[Dissertacao]` → `list[DissertacaoUnitarizada]`. Tipos conforme a seção 3.1 de [divisao-tarefas.md](divisao-tarefas.md); formato do `corpus.json` na seção 3.2. Funções expostas (seção 3.8): `carregar_corpus(caminho)`, `unitarizar(dissertacao)`, `preparar_corpus(caminho_original, caminho_saida)`.
- **Critério de pronto:**
  - as 59 dissertações estão no `corpus.json`, com `id`, e o relatório de avisos foi gerado e revisado (hoje: 0 avisos);
  - `unitarizar` roda nas 59 sem erro;
  - o corpus de calibração existe;
  - os testes passam.
- **Status geral:** Concluído (falta só abrir o pull request, tarefa 9.3)
- **Última atualização:** 2026-10-07 19:01 — por Franklyn/Lucas

### Checklist

**Etapa 1 — Ambiente e base compartilhada**
- [x] 1.1 Criar a branch `feature/parte-1-dados` a partir da `main` atualizada — 2026-10-07, Franklyn/Lucas — (só git; convenção atualizada em `docs/divisao-tarefas.md`)
- [x] 1.2 Criar o ambiente virtual (`venv/`) e um `requirements.txt` mínimo com o que a Parte 1 usa: `spacy`, o modelo `pt_core_news_sm` e `pytest` — 2026-10-07, Franklyn/Lucas — `requirements.txt`
- [x] 1.3 Instalar e confirmar que funciona: `python -c "import spacy; spacy.load('pt_core_news_sm')"` e `python -m pytest --version` — 2026-10-07, Franklyn/Lucas — (só instalação)
- [x] 1.4 Criar `src/__init__.py` e `src/contratos.py` só com os tipos da Parte 1 (`Dissertacao`, `Frase`, `DissertacaoUnitarizada`), exatamente como na seção 3.1 da divisão — 2026-10-07, Franklyn/Lucas — `src/__init__.py`, `src/contratos.py`
- [x] 1.5 Criar `config.py` só com a seção da Parte 1 (`CAMINHO_ORIGINAL`, `CAMINHO_CORPUS`, `CAMINHO_CALIBRACAO`) — 2026-10-07, Franklyn/Lucas — `config.py`
- [x] 1.6 Criar a pasta `tests/` e confirmar que `python -m pytest` roda — 2026-10-07, Franklyn/Lucas — `pytest.ini`, `tests/test_parte1_contratos.py`

**Etapa 2 — Dados de exemplo (mocks)**
- [x] 2.1 `tests/exemplos/corpus_exemplo.json`: 3 dissertações **inventadas** no formato do `corpus.json` (uma qualitativa, uma quantitativa, uma que não informa o método) — 2026-10-07, Franklyn/Lucas — `tests/exemplos/corpus_exemplo.json`
- [x] 2.2 `tests/exemplos/original_exemplo.json`: as mesmas 3 no formato do original, com casos-problema de propósito — 2026-10-07, Franklyn/Lucas — `tests/exemplos/original_exemplo.json`
- [x] 2.3 `tests/exemplos/frases_exemplo.json`: as 3 já divididas em frases (F1, F2…), definidas à mão, para servir de referência às outras partes — 2026-10-07, Franklyn/Lucas — `tests/exemplos/frases_exemplo.json`

**Etapa 3 — Carregar e validar o corpus (`carregar_corpus`)**
- [x] 3.1 Ler o `corpus.json` e devolver `list[Dissertacao]` — 2026-10-07, Franklyn/Lucas — `src/preparar_dados.py`
- [x] 3.2 Validar: `id` sem repetição; título e resumo não vazios; palavras-chave em lista. Erros com mensagem clara que cita o `id` (ex.: "D017 está sem resumo") — 2026-10-07, Franklyn/Lucas — `src/preparar_dados.py`
- [x] 3.3 Testes: corpus válido carrega; campo faltando, `id` repetido e resumo vazio geram erro com o `id` — 2026-10-07, Franklyn/Lucas — `tests/test_parte1_carregar_corpus.py`

**Etapa 4 — Normalizar o texto (`normalizar_texto`)**
- [x] 4.1 Padronizar Unicode, espaços repetidos e quebras de linha, incluindo as do Windows (`\r\n`), que aparecem nos títulos 6 e 52 — 2026-10-07, Franklyn/Lucas — `src/preparar_dados.py`, `docs/divisao-tarefas.md`
- [x] 4.2 Juntar palavra hifenizada só quando o hífen está **no fim da linha** ("investiga-\nção" → "investigação"), e só entre letras. Não mexer em "NAF- Núcleo", "cirurgião- dentista" nem números ("2022-\n2023") — 2026-10-07, Franklyn/Lucas — `src/preparar_dados.py`
- [x] 4.3 Testes dos casos acima — 2026-10-07, Franklyn/Lucas — `tests/test_parte1_normalizar.py`

**Etapa 5 — Dividir em frases (`unitarizar`)**
- [x] 5.1 Dividir o resumo com spaCy `pt_core_news_sm` e numerar F1, F2… na ordem. Não descartar frases curtas — 2026-10-07, Franklyn/Lucas — `src/unitarizar.py`, `config.py`
- [x] 5.2 Tratar casos difíceis, com teste para cada um: "Segundo Bardin (2016), a análise…", "Dr.", números como "2,5", "Lei n.º 12.318/2010", "et al.", "cf. Prof.", "etc." — 2026-10-07, Franklyn/Lucas — `src/unitarizar.py`, `tests/test_parte1_unitarizar.py`
- [x] 5.3 Rodar nas 59 sem erro e registrar quantas frases cada resumo teve — 2026-10-07, Franklyn/Lucas — `src/unitarizar.py`, `tests/test_parte1_unitarizar.py` (629 frases; 5 a 18 por resumo; contagem no log)

**Etapa 6 — Gerar o `corpus.json` a partir do original (`preparar_corpus`)**
- [x] 6.1 Ler o original e criar os `id` D001 a D059 na ordem do arquivo — 2026-10-07, Franklyn/Lucas — `src/preparar_dados.py`
- [x] 6.2 Transformar as palavras-chave (texto separado por vírgulas) em lista, sem espaços sobrando — 2026-10-07, Franklyn/Lucas — `src/preparar_dados.py`
- [x] 6.3 Normalizar título e resumo com `normalizar_texto` (títulos com quebra de linha: itens 6 e 52) — 2026-10-07, Franklyn/Lucas — `src/preparar_dados.py`
- [x] 6.4 Remover sobras da cópia do PDF ("Palavras-chave: …" no fim do resumo), com teste usando o exemplo da etapa 2 — 2026-10-07, Franklyn/Lucas — `src/preparar_dados.py`, `tests/test_parte1_preparar_corpus.py`
- [x] 6.5 Gravar `data/corpus.json` em UTF-8 e criar o comando `python -m src.preparar_dados` — 2026-10-07, Franklyn/Lucas — `src/preparar_dados.py`, `tests/test_parte1_preparar_corpus.py`, `data/corpus.json`
- [x] 6.6 Rodar com o arquivo **real** (`data/brutos/dissertacoes.json`) e conferir: 59 itens, `id` sem repetição, nenhum campo vazio, `carregar_corpus` aceita o resultado — 2026-10-07, Franklyn/Lucas — `data/corpus.json` (só conferência)

**Etapa 7 — Verificações automáticas**
- [x] 7.1 Relatório de avisos: resumo com "Palavras-chave", "Abstract", "Keywords" ou "Resumo:" no meio do texto; resumo muito curto (< 300 caracteres); resumo sem ponto final; título repetido. Mostrado pelo comando `python -m src.preparar_dados` — 2026-10-07, Franklyn/Lucas — `src/preparar_dados.py`, `tests/test_parte1_preparar_corpus.py`
- [x] 7.2 ~~Conferir contra o PDF as dissertações marcadas pelo relatório~~ — **cancelada** em 2026-10-07 (ver decisões): o JSON é a fonte; o relatório da 7.1 fica para o grupo revisar

**Etapa 8 — Corpus de calibração**
- [x] 8.1 Conseguir dissertações **de fora das 59**, com título, resumo e palavras-chave — 2026-10-07, Franklyn — 20 dissertações de 2022, `data/brutos/calibracao.json`
- [x] 8.2 Gerar `data/calibracao/corpus_calibracao.json` com o mesmo `preparar_corpus` (ids C001…) — 2026-10-07, Franklyn/Lucas — `data/calibracao/corpus_calibracao.json` (gerado por `python -m src.preparar_dados --calibracao`)

**Etapa 9 — Fechamento**
- [x] 9.1 Todos os testes da Parte 1 passam (`python -m pytest tests/`) — 2026-10-07, Franklyn/Lucas — 64 passed
- [x] 9.2 Conferir cada item do critério de pronto — 2026-10-07, Franklyn/Lucas — resultado no log: 3 de 4 itens cumpridos; falta a calibração
- [ ] 9.3 Abrir o pull request `[Parte 1] …` para a `main`, com revisão de outro membro

### Próximo passo
Franklyn pedir o commit e o push da branch `feature/parte-1-dados` e abrir o pull request `[Parte 1] Dados e unitarização`, com revisão de outro membro (tarefa 9.3).

### Pendências e dúvidas em aberto
- Nenhuma no momento.

---

## Partes 2 a 5

O checklist de cada parte é criado aqui, numa seção própria, quando ela começar, a partir da seção da parte em [divisao-tarefas.md](divisao-tarefas.md). As Partes 4 e 5 ficam para o final.

---

## Decisões tomadas

| Data | Parte | Decisão | Motivo | Quem |
|------|-------|---------|--------|------|
| 2026-10-07 | Todas | As Partes 4 e 5 (orquestração, Excel e avaliação) ficam para o final; o trabalho começa pela Parte 1 | Decisão da reunião do grupo | Grupo |
| 2026-10-07 | 1 | A Parte 1 é feita em dupla por Franklyn e Lucas, às vezes no mesmo computador; quando não houver indicação, o autor é registrado como "Franklyn/Lucas" | Decisão da reunião do grupo | Grupo |
| 2026-10-07 | 1 | A Parte 1 cria o mínimo do esqueleto de que precisa: `src/contratos.py` (só os tipos da Parte 1, como na seção 3.1 da divisão), a seção da Parte 1 no `config.py`, um `requirements.txt` inicial e a configuração do pytest | O esqueleto era da Parte 4, que ficou para o final; sem ele a Parte 1 não roda | Franklyn/Lucas |
| 2026-10-07 | 1 | Títulos ficam como no original (inclusive os em maiúsculas); só espaços e quebras de linha são corrigidos | O JSON foi copiado do PDF; manter o texto fiel à fonte | Franklyn/Lucas |
| 2026-10-07 | 1 | O JSON (`data/brutos/dissertacoes.json`) é a fonte; não há conferência contra o PDF (tarefa 7.2 cancelada) | O PDF original não fica disponível; a ideia do projeto é trabalhar só com título, resumo e palavras-chave | Franklyn/Lucas |
| 2026-10-07 | Todas | Branches no padrão `feature/parte-N-tema`; a da Parte 1 é `feature/parte-1-dados` | Nome mais formal que `parte-1`; convenção atualizada na seção 6.2 da divisão | Franklyn/Lucas |
| 2026-10-07 | Todas | Um único arquivo de progresso para todas as partes (`docs/PROGRESSO.md`), em vez de um arquivo por parte; sem README separado por parte | Evitar excesso de arquivos Markdown | Franklyn |
| 2026-10-07 | 1 | O formato do original (`data/brutos/dissertacoes.json`: lista com `titulo`, `resumo` e `palavras_chave` em texto) é o formato real, não mais provisório; se mudar, só `preparar_dissertacoes` precisa ser ajustada | Arquivo real das 59 já está no repositório e foi processado sem erro | Franklyn/Lucas |
| 2026-10-07 | Todas | Dependências com versão fixa no `requirements.txt`: `spacy==3.8.16`, `pt_core_news_sm` 3.8.0 (instalado pelo link oficial do spaCy) e `pytest==9.1.1` | Reprodutibilidade: todos instalam exatamente as mesmas versões | Franklyn/Lucas |
| 2026-10-07 | 1 | `src/contratos.py` criado pela Parte 1 só com `Dissertacao`, `Frase` e `DissertacaoUnitarizada`, idênticos à seção 3.1 da divisão; os tipos das outras partes entram quando elas começarem | Contrato compartilhado: registrar quem criou e o que tem | Franklyn/Lucas |
| 2026-10-07 | 1 | Caminhos do `config.py` montados a partir da pasta do próprio arquivo (`RAIZ`), com `pathlib` | Assim os comandos funcionam de qualquer pasta, sem erro de "arquivo não encontrado" | Franklyn/Lucas |
| 2026-10-07 | 1 | Configuração do pytest em `pytest.ini` (raiz no caminho de importação, testes em `tests/`); arquivos de teste da Parte 1 com o prefixo `test_parte1_` | Rodar `python -m pytest` de qualquer pasta sem erro de importação; saber de que parte é cada teste | Franklyn/Lucas |
| 2026-10-07 | 1 | Dados de exemplo usam ids `E001`, `E002`, `E003` (e não `D…`) | Nunca confundir exemplo inventado com dissertação real | Franklyn/Lucas |
| 2026-10-07 | 1 | `frases_exemplo.json` segue o formato de `DissertacaoUnitarizada`: lista de objetos com `dissertacao` (igual ao `corpus.json`) e `frases` (lista de `{id, texto}`) | É o formato que as Partes 2 e 3 vão ler nos testes delas | Franklyn/Lucas |
| 2026-10-07 | 1 | `carregar_corpus` junta **todos** os problemas numa só mensagem (erro `ErroCorpus`, um problema por linha), em vez de parar no primeiro | Quem conserta o JSON vê tudo de uma vez | Franklyn/Lucas |
| 2026-10-07 | 1 | Campo desconhecido no corpus é erro (ex.: `palavras-chave` com hífen) | Pega erro de digitação que, de outro jeito, passaria em silêncio | Franklyn/Lucas |
| 2026-10-07 | 1 | Normalização Unicode em **NFC**, não NFKC como dizia a divisão (texto da divisão corrigido) | No texto real, o NFKC trocaria "º" por "o" (15 vezes, ex.: "n.º" → "n.o") e "ª" por "a" (4 vezes); o NFC não altera nada | Franklyn/Lucas |
| 2026-10-07 | 1 | Caracteres de controle U+0080 a U+009F são convertidos no símbolo que eram no Windows (cp1252): aspas e apóstrofos curvos | Encontrados 11 no original (títulos 5, 15, 22, 25, 28; palavras-chave 13 e 28), ex.: "Olhos D\x92água" → "Olhos D’água" | Franklyn/Lucas |
| 2026-10-07 | 1 | A junção por hífen de fim de linha só vale com **letras** dos dois lados | Na primeira versão, "2022-\n2023" virou "20222023"; com números, a quebra é mantida como espaço | Franklyn/Lucas |
| 2026-10-07 | 1 | Nome do modelo do spaCy no `config.py` (`MODELO_SPACY`); o modelo é carregado uma vez só e sem os componentes que não usamos (entidades e lematizador) | Reprodutibilidade e velocidade | Franklyn/Lucas |
| 2026-10-07 | 1 | Depois do spaCy, os pedaços são reunidos quando o anterior termina numa abreviação conhecida (lista `ABREVIACOES`) ou quando o seguinte começa com minúscula, "(" ou pontuação. "etc." não entra na lista | O spaCy cortava "Souza et al. | (2019)" e "(cf. | Prof. | Silva, 2020)"; "etc." muitas vezes termina a frase de verdade | Franklyn/Lucas |
| 2026-10-07 | 1 | Uma frase só termina em ". ! ? …" (podendo vir aspas ou parêntese depois); se o pedaço do spaCy não termina assim, ele continua no próximo. Também se junta quando o seguinte começa com minúscula, pontuação ou fechando aspas | No texto real o spaCy cortava em ":", ";", dentro de aspas, em listas numeradas ("1)") e em "Pingo | D’Água" | Franklyn/Lucas |
| 2026-10-07 | 1 | As frases são recortadas do texto pela posição (início e fim), não remontadas com espaço | Juntar pedaços inseria espaços que não existiam (ex.: `“ A igreja`); agora juntar todas as frases reproduz o resumo exatamente | Franklyn/Lucas |
| 2026-10-07 | 1 | `preparar_dissertacoes(original, prefixo="D")` cria o id com prefixo + posição em 3 dígitos; a calibração usará outro prefixo (ex.: `C001`) | A mesma função serve para as 59 e para a calibração, sem misturar ids | Franklyn/Lucas |
| 2026-10-07 | 1 | Palavras-chave mantêm maiúsculas/minúsculas do original (ex.: "enchente", "Instituto terra") | Fidelidade à fonte; padronizar a escrita não é tarefa da preparação | Franklyn/Lucas |
| 2026-10-07 | 1 | O `corpus.json` é gravado em UTF-8 com acentos legíveis (sem `\u00ea`), indentação de 2 espaços e sem o campo `ano` quando não existe; depois de gravar, o próprio `preparar_corpus` relê o arquivo com `carregar_corpus` | Arquivo legível no GitHub e garantia de que o que foi gravado é um corpus válido | Franklyn/Lucas |
| 2026-10-07 | 1 | Avisos não bloqueiam a geração do corpus: só são listados para o grupo revisar. Limite de "resumo curto": 300 caracteres. Também avisa título repetido | O menor resumo real tem 1.138 caracteres; 500 marcava até os exemplos inventados (~450). Título repetido indicaria dissertação colada duas vezes | Franklyn/Lucas |
| 2026-10-07 | 1 | O original da calibração fica em `data/brutos/calibracao.json`, no mesmo formato de `dissertacoes.json`; o preparado vai para `data/calibracao/corpus_calibracao.json` com ids C001…, pelo comando `python -m src.preparar_dados --calibracao` | Mesmo caminho de preparação das 59, sem código novo quando as dissertações chegarem | Franklyn/Lucas |
| 2026-10-07 | 1 | A calibração usa as **20 dissertações de 2022** trazidas pelo Franklyn (e não só 3 a 5); ids C001 a C020 | Mais exemplos para testar o prompt; nenhuma coincide com as 59 (título e resumo conferidos) | Franklyn/Lucas |
| 2026-10-07 | 1 | Como no corpus das 59, só a lista das dissertações vai para `data/brutos/calibracao.json`; a exportação do phpMyAdmin, que traz o nome do banco de dados da hospedagem, fica fora do git | Repositório público: nenhum dado de servidor ou hospedagem | Franklyn/Lucas |
| 2026-10-07 | 1 | Acrescentado o ponto final nos resumos D057 e D059 **direto no original** (`data/brutos/dissertacoes.json`), com autorização do Franklyn. A preparação continua sem acrescentar texto por conta própria | O texto estava completo e só faltava o ponto; corrigir na fonte, como foi feito com o D048, mantém o código fiel ao original | Franklyn/Lucas |

## Registro de auditoria (log)

Entradas em ordem cronológica, a mais recente no TOPO. Cada entrada indica a parte.

### 2026-10-07 19:01 — Franklyn/Lucas — Parte 1
- **Feito:** resolvidos os 2 avisos do corpus: com autorização do Franklyn, acrescentado o ponto final no fim dos resumos D057 e D059 no original. Regenerado o `corpus.json`. Atualizada a observação no planejamento (seção 6.1). Critério de pronto da Parte 1 todo cumprido.
- **Arquivos:** `data/brutos/dissertacoes.json` (2 linhas), `data/corpus.json` (regenerado), `docs/PLANEJAMENTO_TCC.md`
- **Testes:** `git diff` do original mostra só as 2 linhas dos resumos alteradas; `python -m src.preparar_dados` → 59 dissertações, 287 palavras-chave, **0 avisos**; as mesmas 629 frases (D057: 11, D059: 17); nenhuma frase termina fora de ". ! ? …"; `python -m pytest -q` → 64 passed.
- **Observações / problemas:** critério de pronto: (1) corpus com id e avisos revisados — cumprido; (2) unitarização nas 59 — cumprido; (3) calibração — cumprido; (4) testes — cumprido. Falta só o pull request.

### 2026-10-07 18:59 — Franklyn/Lucas — Parte 1
- **Feito:** tarefas 8.1 e 8.2: o Franklyn trouxe as 20 dissertações de 2022 numa exportação do phpMyAdmin. Conferido que nenhuma tem título ou resumo igual a uma das 59 e que nenhuma se repete. Gravada só a lista em `data/brutos/calibracao.json` (conteúdo idêntico) e gerado o corpus de calibração. Atualizados o planejamento, a divisão de tarefas, o resumo do projeto e o `AGENTS.md`, que falavam em "3 a 5 dissertações".
- **Arquivos:** `data/brutos/calibracao.json`, `data/calibracao/corpus_calibracao.json` (gerado), `docs/PLANEJAMENTO_TCC.md`, `docs/divisao-tarefas.md`, `docs/CONTEXTO_DO_PROJETO.md`, `AGENTS.md`
- **Testes:** `python -m src.preparar_dados --calibracao` → 20 dissertações (C001 a C020), 85 palavras-chave, 0 avisos. Unitarização: 212 frases (4 a 23 por resumo; a de 23 é a C003, um resumo longo, conferido), nenhuma frase suspeita, juntar as frases reproduz cada resumo. `python -m pytest -q` → 64 passed. O nome do banco não aparece em nenhum arquivo do repositório.
- **Observações / problemas:** Etapa 8 concluída. Do critério de pronto falta só a revisão dos avisos pelo grupo.

### 2026-10-07 18:47 — Franklyn/Lucas — Parte 1
- **Feito:** tarefas 9.1 e 9.2: rodada a suíte completa e conferido o critério de pronto da Parte 1. (1) 59 dissertações no `corpus.json`, com id: **cumprido**; relatório de avisos gerado (2 avisos), falta a revisão pelo grupo. (2) `unitarizar` roda nas 59 sem erro: **cumprido** (629 frases). (3) Corpus de calibração existe: **não cumprido**, bloqueado na 8.1 (código pronto). (4) Os testes passam: **cumprido**.
- **Arquivos:** nenhum alterado (só conferência)
- **Testes:** `python -m pytest tests/` → 64 passed; `python -m src.preparar_dados` gera o mesmo `corpus.json`; `git status` mostra o original `data/brutos/dissertacoes.json` sem alteração e o `venv/` fora do git.
- **Observações / problemas:** a Parte 1 só fica "Concluído" depois da calibração. Nada foi commitado ainda; commit e pull request só quando o Franklyn pedir.

### 2026-10-07 18:47 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 8.2 (parcial): adiantado o código da calibração enquanto a 8.1 está bloqueada. Acrescentados `CAMINHO_ORIGINAL_CALIBRACAO` ao `config.py` e a opção `--calibracao` ao comando, com mensagem clara quando o arquivo ainda não existe. O comando passou a mostrar caminhos de forma robusta (a primeira versão do teste falhou por isso).
- **Arquivos:** `config.py`, `src/preparar_dados.py`, `tests/test_parte1_preparar_corpus.py`
- **Testes:** `python -m pytest -q` → 64 passed (novo teste: o comando com `--calibracao`, usando o exemplo, gera C001 a C003). `python -m src.preparar_dados --calibracao` sem o arquivo → "Arquivo não encontrado: data\brutos\calibracao.json". O comando normal continua gerando o mesmo `corpus.json`.
- **Observações / problemas:** 8.1 continua bloqueada: depende do grupo conseguir as 3 a 5 dissertações de fora das 59.

### 2026-10-07 18:46 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 7.1: criada `verificar_corpus`, que lista avisos (termos de outra parte do PDF no resumo, resumo curto, sem ponto final, título repetido), e o comando `python -m src.preparar_dados` passou a mostrá-los. Primeira versão usava limite de 500 caracteres e marcava os exemplos inventados; baixado para 300. Criados 6 testes dos avisos.
- **Arquivos:** `src/preparar_dados.py`, `tests/test_parte1_preparar_corpus.py`
- **Testes:** `python -m pytest -q` → 63 passed. No corpus real: 2 avisos, D057 e D059 sem ponto final (os mesmos já conhecidos). O `corpus.json` gerado continua idêntico.
- **Observações / problemas:** Etapa 7 concluída (a 7.2 foi cancelada). Uma cópia temporária foi feita por engano em `/tmp` durante a conferência e apagada em seguida.

### 2026-10-07 18:45 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 6.6: conferido o `data/corpus.json` gerado a partir do original real.
- **Arquivos:** nenhum alterado (só conferência de `data/corpus.json`)
- **Testes:** `carregar_corpus` aceita o arquivo; 59 itens; ids D001 a D059 em sequência e sem repetição; nenhum título, resumo ou lista de palavras-chave vazio; mesma ordem do original; cada resumo é exatamente o original normalizado (nada perdido); a unitarização dá as mesmas 629 frases da tarefa 5.3, dissertação por dissertação; `git status` mostra o original sem alteração.
- **Observações / problemas:** Etapa 6 concluída. O formato do JSON deixou de ser provisório (ver pendências).

### 2026-10-07 18:44 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 6.5: criadas `preparar_corpus(caminho_original, caminho_saida, prefixo)`, que grava o JSON e confere o resultado, e o comando `python -m src.preparar_dados`, que usa os caminhos do `config.py`. Gerado o `data/corpus.json` real. Acrescentado teste que grava num arquivo temporário e confere o conteúdo.
- **Arquivos:** `src/preparar_dados.py`, `tests/test_parte1_preparar_corpus.py`, `data/corpus.json` (gerado)
- **Testes:** `python -m src.preparar_dados` → "59 dissertações (D001 a D059), 287 palavras-chave"; `python -m pytest -q` → 57 passed.
- **Observações / problemas:** o comando precisa ser rodado da raiz do repositório (é assim que o `python -m` encontra o pacote `src`).

### 2026-10-07 18:44 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 6.4: criada `limpar_resumo`, que normaliza o resumo e corta do "Palavras-chave:" (ou "Palavras chave", "Palavra-chave", qualquer maiúscula/minúscula) até o fim. Criados os testes da preparação, incluindo o principal: o `original_exemplo.json` (cheio de problemas) preparado vira exatamente o `corpus_exemplo.json`.
- **Arquivos:** `src/preparar_dados.py`, `tests/test_parte1_preparar_corpus.py`
- **Testes:** `python -m pytest -q` → 56 passed. No original real nenhum resumo é cortado (a sobra do D048 já tinha sido corrigida no JSON novo).
- **Observações / problemas:** nenhum.

### 2026-10-07 18:43 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 6.3: `preparar_dissertacoes` passou a normalizar título e resumo.
- **Arquivos:** `src/preparar_dados.py`
- **Testes:** no original real: D006 e D052 sem quebra de linha; D005 e D028 com aspas/apóstrofo consertados; em nenhum título, resumo ou palavra-chave sobrou quebra de linha, caractere de controle, espaço duplo ou espaço nas pontas.
- **Observações / problemas:** nenhum.

### 2026-10-07 18:43 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 6.2: criada `separar_palavras_chave`, que separa por vírgula (e ponto e vírgula, por garantia), normaliza cada termo (inclusive as aspas do Windows) e descarta vazios. `preparar_dissertacoes` passou a usá-la.
- **Arquivos:** `src/preparar_dados.py`
- **Testes:** exemplos com espaço duplo e vírgula sobrando saem limpos; "Resolução SEE/MG nº 4.701/2022" fica inteiro; no original real: 287 termos (mesmo total da contagem bruta), de 3 a 7 por dissertação; "Programa olhos d‘água" (D013) sai com o apóstrofo consertado.
- **Observações / problemas:** nenhum.

### 2026-10-07 18:42 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 6.1: criada `preparar_dissertacoes`, que confere o formato do original (lista; cada item com `titulo`, `resumo` e `palavras_chave` em texto; erro `ErroOriginal` listando todos os problemas) e cria uma `Dissertacao` por item com id na ordem do arquivo. As palavras-chave ainda ficam como o texto inteiro dentro da lista (a 6.2 separa).
- **Arquivos:** `src/preparar_dados.py`
- **Testes:** no original real: 59 dissertações, D001 a D059, sem id repetido; o 48º é "EMBORNAL DE SABERES E FAZERES…" = D048; com prefixo "C" sai C001…; item sem campos gera erro citando a posição.
- **Observações / problemas:** nenhum.

### 2026-10-07 18:42 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 5.3: unitarização rodada nas 59 reais (montadas direto do original normalizado, porque o `corpus.json` só sai na etapa 6). A primeira rodada achou problemas que os exemplos não tinham: cortes dentro de citações entre aspas (D005, D046), depois de ":"/";", em listas numeradas (D021, D036, D057) e em "Pingo | D’Água" (D002), além de espaço inserido ao juntar pedaços. Corrigido com a regra de fim de frase e o recorte por posição. Acrescentados 4 testes com textos inventados parecidos com esses casos.
- **Arquivos:** `src/unitarizar.py`, `tests/test_parte1_unitarizar.py`
- **Testes:** `python -m pytest -q` → 46 passed. Nas 59: sem erro; 629 frases; mínimo 5, mediana 10, máximo 18; juntar as frases reproduz cada resumo exatamente; nenhuma frase termina fora de ". ! ? …", exceto a última de D057 e D059 (resumos sem ponto final, já conhecidos). Frases por resumo: 001:9, 002:14, 003:10, 004:7, 005:9, 006:7, 007:16, 008:13, 009:13, 010:18, 011:15, 012:14, 013:10, 014:12, 015:14, 016:7, 017:6, 018:6, 019:6, 020:12, 021:11, 022:8, 023:10, 024:15, 025:12, 026:14, 027:11, 028:10, 029:5, 030:15, 031:8, 032:11, 033:6, 034:14, 035:8, 036:12, 037:17, 038:11, 039:13, 040:10, 041:8, 042:8, 043:16, 044:8, 045:12, 046:6, 047:10, 048:7, 049:11, 050:16, 051:12, 052:10, 053:10, 054:5, 055:8, 056:9, 057:11, 058:6, 059:17.
- **Observações / problemas:** duas frases muito longas (D024 F11 com 845 caracteres e D050 F10 com 682) foram conferidas: são listas de temáticas separadas por ";" com um único ponto final, ou seja, uma frase só mesmo. Os números podem mudar levemente quando o `corpus.json` for gerado (etapa 6), por causa da remoção de sobras. Etapa 5 concluída.

### 2026-10-07 18:39 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 5.2: testados 11 casos difíceis direto no spaCy. Ele acertou "Bardin (2016)", "Dr.", "2,5", "Lei n.º", "EUA", "i.e.", "p. 23" e "etc." no fim de frase, mas errou "et al. (2019)" e "(cf. Prof. Silva, 2020)". Acrescentada a regra de reunir pedaços cortados errado. Criados os testes da unitarização: os casos difíceis, frase curta não descartada, os 3 exemplos iguais ao gabarito feito à mão, ids sequenciais e nenhuma palavra perdida.
- **Arquivos:** `src/unitarizar.py`, `tests/test_parte1_unitarizar.py`
- **Testes:** `python -m pytest -q` → 42 passed. Os 3 exemplos agora batem exatamente com `frases_exemplo.json` (antes, E002 saía com 7 frases).
- **Observações / problemas:** se aparecer outra abreviação que o spaCy corte errado, basta acrescentá-la em `ABREVIACOES` e criar um teste.

### 2026-10-07 18:38 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 5.1: criado `src/unitarizar.py` com `dividir_em_frases(texto)` e `unitarizar(dissertacao)`, que devolve `DissertacaoUnitarizada` com frases F1, F2… Acrescentado `MODELO_SPACY` ao `config.py`.
- **Arquivos:** `src/unitarizar.py`, `config.py`
- **Testes:** nos exemplos: E001 e E003 saem iguais ao gabarito (6 e 5 frases). E002 sai com 7 em vez de 6: o spaCy corta "Segundo Souza et al. | (2019), esse tempo…". Juntar as frases reproduz o resumo exatamente.
- **Observações / problemas:** o corte em "et al." é o primeiro caso da 5.2.

### 2026-10-07 18:38 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 4.3: 19 testes da `normalizar_texto`: quebras de linha do Windows e do Linux, tabulação, espaços repetidos e nas pontas, espaço não separável, hífen invisível, palavra cortada por hífen (3 casos), hífens que não devem ser mexidos (4 casos, inclusive números), "º"/"ª" preservados, acento decomposto, aspas e apóstrofos do Windows (3 casos) e texto já limpo que não muda.
- **Arquivos:** `tests/test_parte1_normalizar.py`
- **Testes:** `python -m pytest -q` → 32 passed.
- **Observações / problemas:** Etapa 4 concluída.

### 2026-10-07 18:37 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 4.2: `normalizar_texto` passou a juntar palavra cortada por hífen no fim da linha, antes de juntar os espaços. Primeira versão juntava também números ("2022-\n2023" → "20222023"); corrigido para só letras.
- **Arquivos:** `src/preparar_dados.py`
- **Testes:** "investiga-\nção" → "investigação"; "coope-\r\nrativa" → "cooperativa"; "NAF- Núcleo" e "cirurgião- dentista" inalterados; "2022-\n2023" → "2022- 2023". O original das 59 não tem nenhum hífen de fim de linha, então a regra não altera os dados reais.
- **Observações / problemas:** nenhum.

### 2026-10-07 18:37 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 4.1: criada `normalizar_texto`: Unicode NFC; conserto das aspas/apóstrofos do Windows que viraram caracteres invisíveis; remoção do hífen invisível; quebras de linha, tabulações, espaço não separável e espaços repetidos viram um espaço; tira espaços das pontas. Texto da divisão atualizado (NFKC → NFC).
- **Arquivos:** `src/preparar_dados.py`, `docs/divisao-tarefas.md`
- **Testes:** aplicada a todos os campos das 59: nenhum caractere de controle sobrou; títulos 5 e 28 com aspas/apóstrofo corretos; títulos 6 e 52 sem quebra; 15 "º" e 4 "ª" preservados. Testes automáticos ficam para a 4.3.
- **Observações / problemas:** achado novo: aspas corrompidas na cópia do PDF, que não estavam na lista de problemas conhecidos.

### 2026-10-07 18:36 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 3.3: 10 testes do `carregar_corpus`: exemplo carrega; `ano` opcional; resumo vazio, título vazio, campo faltando, id repetido, palavras-chave em texto, campo com nome errado e corpus que não é lista geram erro citando o id; vários problemas aparecem juntos.
- **Arquivos:** `tests/test_parte1_carregar_corpus.py`
- **Testes:** `python -m pytest -q` → 13 passed (3 de contratos + 10 novos).
- **Observações / problemas:** Etapa 3 concluída.

### 2026-10-07 18:35 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 3.2: `carregar_corpus` passou a conferir o corpus antes de criar as `Dissertacao`: lista no topo; campos obrigatórios; campo desconhecido; id, título e resumo não vazios; palavras-chave como lista de textos; `ano` inteiro ou ausente; id repetido. Criado o erro `ErroCorpus`.
- **Arquivos:** `src/preparar_dados.py`
- **Testes:** o `corpus_exemplo.json` continua carregando; um corpus com 3 itens ruins gerou as 6 mensagens esperadas ("D001 está sem resumo", "D003: falta o campo 'resumo'", "D001: id repetido (2 vezes)" etc.).
- **Observações / problemas:** nenhum.

### 2026-10-07 18:35 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 3.1: criado `src/preparar_dados.py` com `carregar_corpus(caminho)`, que lê o JSON em UTF-8 e cria uma `Dissertacao` por item. Ainda sem validação (é a 3.2).
- **Arquivos:** `src/preparar_dados.py`
- **Testes:** carregou o `corpus_exemplo.json`: 3 itens do tipo `Dissertacao`, palavras-chave em lista.
- **Observações / problemas:** nenhum.

### 2026-10-07 18:35 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 2.3: criado o gabarito de frases das 3 dissertações de exemplo (6, 6 e 5 frases). As frases foram definidas por nós, não pelo spaCy, para servir de resposta certa no teste da etapa 5. "Bardin (2016)", "et al. (2019)", "Dr. Paulo" e "Lei n.º 13.146" ficam dentro da mesma frase.
- **Arquivos:** `tests/exemplos/frases_exemplo.json`
- **Testes:** as frases de cada dissertação, juntadas com espaço, reproduzem exatamente o resumo do `corpus_exemplo.json`.
- **Observações / problemas:** Etapa 2 concluída.

### 2026-10-07 18:34 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 2.2: criado o exemplo no formato do original (palavras-chave em texto, sem `id`). Problemas colocados de propósito: quebra de linha do Windows no título da 1ª; palavra cortada por hífen no fim da linha ("coope-\nrativa"); espaços duplos e no começo/fim; espaço não separável no "n.º 13.146"; sobra "Palavras-chave: Cooperativismo, Territ" no fim do 1º resumo; vírgula e espaços sobrando nas palavras-chave. A ideia: preparar este arquivo tem que dar exatamente o `corpus_exemplo.json` (vira teste na etapa 6).
- **Arquivos:** `tests/exemplos/original_exemplo.json`
- **Testes:** o arquivo carrega como JSON e contém cada um dos problemas planejados.
- **Observações / problemas:** o resumo sem ponto final (3ª) continua sem ponto depois de preparado: a preparação não inventa texto; esse caso só gera aviso (7.1).

### 2026-10-07 18:34 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 2.1: criado o corpus de exemplo com 3 dissertações inventadas: E001 qualitativa (estudo de caso, entrevistas, Bardin), E002 quantitativa (questionário, estatística, "2,5 horas", "et al."), E003 sem método informado ("Lei n.º", "Dr."; resumo termina sem ponto final de propósito, para testar o aviso da 7.1). O título da E001 está em maiúsculas, como alguns títulos reais.
- **Arquivos:** `tests/exemplos/corpus_exemplo.json`
- **Testes:** as 3 entradas carregam no tipo `Dissertacao`; nenhum título coincide com as 59 reais.
- **Observações / problemas:** nenhum.

### 2026-10-07 18:33 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 1.6: criados o `pytest.ini` e a pasta `tests/` com um primeiro teste que confere os campos dos contratos da Parte 1 (em vez de deixar a pasta vazia, o que faria o pytest terminar sem rodar nada).
- **Arquivos:** `pytest.ini`, `tests/test_parte1_contratos.py`
- **Testes:** `python -m pytest -q` → 3 passed, tanto da raiz quanto de dentro de `tests/`.
- **Observações / problemas:** Etapa 1 concluída.

### 2026-10-07 18:33 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 1.5: criado o `config.py` na raiz, com a seção da Parte 1 (caminhos do original, do `corpus.json` e da calibração), cada um com comentário de justificativa.
- **Arquivos:** `config.py`
- **Testes:** `import config` funcionou da raiz e de dentro de `src/`; `CAMINHO_ORIGINAL` aponta para o arquivo existente.
- **Observações / problemas:** nenhum.

### 2026-10-07 18:32 — Franklyn/Lucas — Parte 1
- **Feito:** tarefa 1.4: criado o pacote `src` (`src/__init__.py`) e o `src/contratos.py` com os 3 tipos da Parte 1, exatamente como na seção 3.1 da divisão. Removido o `src/.gitkeep`, que não é mais necessário.
- **Arquivos:** `src/__init__.py`, `src/contratos.py`, `src/.gitkeep` (removido)
- **Testes:** importação dos 3 tipos e criação de um exemplo funcionaram; `ano` fica `None` quando não é informado.
- **Observações / problemas:** nenhum.

### 2026-10-07 18:31 — Franklyn/Lucas — Parte 1
- **Feito:** tarefas 1.2 e 1.3: criado o `venv/` (fora do git) e o `requirements.txt` com versões fixas; instalados spaCy 3.8.16, o modelo `pt_core_news_sm` 3.8.0 e pytest 9.1.1. Também, a pedido do Franklyn, o acompanhamento passou de `docs/progresso-parte-1.md` para este arquivo geral, com uma seção por parte; o conteúdo e as entradas anteriores do log foram trazidos sem alteração, e o item "README curto da Parte 1" saiu do checklist.
- **Arquivos:** `requirements.txt`, `docs/PROGRESSO.md` (novo), `docs/progresso-parte-1.md` (removido, conteúdo migrado), `AGENTS.md`, `docs/divisao-tarefas.md`
- **Testes:** `spacy.load('pt_core_news_sm')` carregou o modelo (versão 3.8.0); `python -m pytest --version` → 9.1.1; `pip install -r requirements.txt` terminou sem erro; `venv/` confirmado como ignorado pelo git.
- **Observações / problemas:** nenhum.

### 2026-10-07 18:29 — Franklyn/Lucas — Parte 1
- **Feito:** registradas as respostas sobre esqueleto, títulos, PDF e nome de branch; criada a branch `feature/parte-1-dados` (tarefa 1.1); convenção de branches atualizada na divisão, junto com a ordem decidida na reunião.
- **Arquivos:** `docs/progresso-parte-1.md`, `docs/divisao-tarefas.md`
- **Testes:** `git status` confirma a branch nova.
- **Observações / problemas:** tarefa 7.2 cancelada (sem PDF). Os arquivos ainda não foram commitados; commit só quando o Franklyn pedir.

### 2026-10-07 18:23 — Franklyn/Lucas — Parte 1
- **Feito:** criado o arquivo de acompanhamento, com o checklist da Parte 1 baseado em [divisao-tarefas.md](divisao-tarefas.md); criado o `AGENTS.md` com a regra de ler e atualizar o arquivo.
- **Arquivos:** `docs/progresso-parte-1.md`, `AGENTS.md`
- **Testes:** nenhum (só documentação). Verificado que o ambiente ainda não tem `spacy` nem `pytest` instalados.
- **Observações / problemas:** o esqueleto (contratos, config, requirements) ainda não existe; ver "Pendências".
