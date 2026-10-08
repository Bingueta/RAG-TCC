# Progresso do projeto

> Fonte da verdade sobre o andamento de **todas as partes**. Leia antes de mexer no código.

**Como usar:**
1. Antes de trabalhar numa parte, leia a seção dela aqui e em [divisao-tarefas.md](divisao-tarefas.md).
2. Ao terminar uma tarefa, marque o item no checklist e atualize o "próximo passo" da parte.
3. Na tabela de decisões, registre **só decisões estratégicas e importantes** (que mudam o método, os dados ou os contratos). Detalhes de implementação ficam no código e nos commits.

Legenda: [ ] pendente · [~] em andamento · [x] concluído · [!] bloqueado

**Objetivo atual:** gerar o Excel com temática 1, temática 2 e metodologias das 59 dissertações, com a maior precisão possível, comparando LLMs mais fracos e mais fortes. Medir se as respostas estão certas fica para depois de tudo pronto.

## Visão geral

| Parte | Status | Quem |
|-------|--------|------|
| 1 — Dados e unitarização | Concluída (PR #1 na `main`) | Franklyn/Lucas |
| 2 — Base de conhecimento e busca | Concluída (PR da branch `feature/parte-2-busca`) | Franklyn/Lucas |
| 3 — Geração com LLM e validação | Concluída: prompt `v3`, `qwen3.5` 2b/4b/9b (branch `feature/parte-3-geracao`, no fork) | Lucas |
| 4 — Orquestração, configuração e Excel | Concluída: `python -m src.pipeline`; as 59 rodadas com 3 modelos × 3 técnicas (branch `feature/parte-4-excel`, no fork) | Lucas |
| 5 — Avaliação das respostas da IA | Em andamento: métricas para escolher modelo e prompt na calibração | Lucas |

---

## Parte 1 — Dados e unitarização (concluída)

- **Comandos:** `python -m src.preparar_dados` gera `data/corpus.json` (59 dissertações, D001 a D059, 287 palavras-chave, 0 avisos); `python -m src.preparar_dados --calibracao` gera `data/calibracao/corpus_calibracao.json` (20 dissertações de 2022, C001 a C020).
- **Funções para as outras partes:** `carregar_corpus(caminho)` em `src/preparar_dados.py` e `unitarizar(dissertacao)` em `src/unitarizar.py` (629 frases nas 59; 212 na calibração).

## Parte 2 — Base de conhecimento e busca (concluída)

- **Base de metodologias:** `data/base_metodologia.json`, 28 verbetes nos 6 eixos (v1 feita a partir de manuais; o grupo pode trocar por uma versão própria e rodar `python -m src.indexar` de novo).
- **Comando:** `python -m src.indexar` guarda em `data/indices/` (fora do git) os vetores das 841 frases (59 + 20) e dos verbetes. Rodar de novo se o corpus ou a base mudarem.
- **Função para a Parte 3:** `recuperar(dissertacao, tecnica)` em `src/recuperar.py` devolve um `Contexto` (frases para temáticas, frases de método e verbetes). Técnicas: `sem_rag` (resumo inteiro, sem base), `denso` (busca por sentido) e `hibrido` (sentido + palavra exata; a mais completa). Sempre dentro do resumo da própria dissertação.
- **Testes:** `python -m pytest` → 80 testes (Partes 1 e 2). Os testes da Parte 2 baixam/carregam o modelo de embedding (alguns segundos).

---

## Parte 3 — Geração com LLM e validação

**Objetivo:** transformar dissertação + `Contexto` numa `RespostaIA` (temática 1, temática 2, metodologias, cada uma com a frase do resumo que a justifica), usando um LLM local pelo Ollama. Detalhes na seção "Parte 3" de [divisao-tarefas.md](divisao-tarefas.md).

**Dois requisitos combinados com o grupo:**
1. **Comparar LLMs de forças diferentes.** O mesmo processo roda com um modelo mais fraco, um mais forte e um mais potente, para ver se a qualidade das respostas do Excel muda. Os modelos rodam no PC do Lucas (Ryzen 7 5700X, 16 GB de RAM, **RTX 3060 Ti com 8 GB**), não mais na máquina da RTX 2060. Candidatos medidos na calibração: `qwen3.5` 2b/4b/9b (a geração atual da família; o 9b é o maior que cabe nos 8 GB), `qwen3:8b` e `qwen2.5:7b-instruct` (a sugestão original), todos em `q4_K_M`. Usar a mesma família isola o efeito do tamanho. O modelo é escolhido por configuração (`config.MODELOS_LLM`), sem mexer no código.
2. **Metodologias incomuns.** A base de metodologias é uma **referência, não uma lista fechada**. Muitos resumos usam metodologias pouco comuns ou com nome de autor (ex.: "pesquisa-ação segundo Thiollent", "abordagem de tal autor"). O prompt deve deixar o LLM **interpretar e nomear a metodologia como o resumo descreve**, mesmo que ela não esteja na base, sempre apontando a frase que a justifica. Inventar continua proibido: se o resumo não diz o método, a resposta é "Não informado no resumo".

### Checklist

**Etapa 1 — Ambiente**
- [x] 1.1 Criar a branch `feature/parte-3-geracao` a partir da `main` atualizada (no fork `LucasFeres/RAG-TCC`; como levar ao repo do grupo é decisão do Franklyn)
- [x] 1.2 Instalar o Ollama e baixar os modelos (fraco, forte, mais potente); confirmar quais rodam na máquina e quanto tempo cada um leva por dissertação — Ollama 0.40.0, modelos em `D:\ollama\modelos`; `qwen3.5` 2b/4b/9b levam ~1,6 / 3,5 / 5 s por dissertação
- [x] 1.3 Instalar a biblioteca `ollama` (Python) e fixar a versão no `requirements.txt` (`ollama==0.6.3`)
- [x] 1.4 Acrescentar a `src/contratos.py` os tipos `Campo` e `RespostaIA` (seção 3.1 da divisão, sem mudança)
- [x] 1.5 Acrescentar a seção da Parte 3 ao `config.py`: lista de modelos com rótulo (fraco/forte/potente), versão do prompt, `temperature=0`, `seed` fixa, `num_ctx` (os modelos ficam a confirmar pela medição)

**Etapa 2 — Prompt**
- [x] 2.1 `src/prompts/v1.txt` partindo do "prompt interpretativo" do projeto de referência (TECNICAS 3.8): sempre **duas** temáticas; **todas** as metodologias; cada resposta com os ids das frases (F1, F2…) que a justificam; "Não informado no resumo" quando o método não aparece
- [x] 2.2 Incluir no prompt a regra das metodologias incomuns (requisito 2 acima): a base é referência; pode nomear método fora dela, como o resumo descreve, com evidência
- [x] 2.3 `montar_prompt(dissertacao, contexto, versao)` em `src/sugerir.py` (testável sem Ollama)

**Etapa 3 — Chamada ao modelo**
- [x] 3.1 `gerar_resposta(dissertacao, contexto, modelo)`: Ollama com `format` = JSON Schema, `temperature=0`, `seed` fixa
- [x] 3.2 Ler a resposta; se o JSON vier quebrado, tentar mais uma vez; se falhar, devolver `status="erro"` com a `saida_bruta`. Nunca travar o programa

**Etapa 4 — Validação**
- [x] 4.1 `validar(resposta, dissertacao)` em `src/validar.py`: evidência citada tem que existir nas frases (senão `sem_evidencia`); tirar metodologias repetidas; tratar temática vazia
- [x] 4.2 Testes sem Ollama: `montar_prompt`, leitura de saídas ruins (JSON quebrado, frase inexistente, resposta vazia) e `validar` (`tests/test_parte3_*.py`, 43 testes)

**Etapa 5 — Ajuste do prompt (só com a calibração)**
- [x] 5.1 Rodar nas 20 dissertações de 2022 com os 3 modelos e ler as respostas — `notebooks/parte3_calibracao.py`; saídas em `data/sugestoes/calibracao/`
- [x] 5.2 Ajustar o prompt **olhando só a calibração**; guardar cada versão (`v1`, `v2`…); fixar a versão final antes de rodar nas 59 — **fixado o `v3`** (`config.VERSAO_PROMPT`), pelo critério escrito antes da rodada. Números e passo a passo em [RESULTADOS.md](RESULTADOS.md)

**Etapa 6 — Fechamento**
- [x] 6.1 Testes passando. O Franklyn não pediu PR: o trabalho está no fork `LucasFeres/RAG-TCC`, branch `feature/parte-3-geracao`, que traz também a correção da busca (Parte 2) e a avaliação (Parte 5)

### Próximo passo
Parte 3 concluída. Pendências que não são de código:
- O grupo decide se escreve o gabarito humano das 20 de calibração. Enquanto não decidir, a referência de IA fica fora do repositório, porque quem a lesse antes escreveria o gabarito influenciado.
- O grupo confirma se, no Forms, a temática levava o lugar ("… em Tarumirim"). O `v3` tira o lugar; a medição não mostrou diferença.
- O Franklyn decide se leva para o repo do grupo a correção da busca (`feature/parte-2-correcao-busca`).

---

## Parte 4 — Orquestração, configuração e Excel

**Objetivo:** um comando que pega as 59 dissertações, roda busca (Parte 2) + LLM (Parte 3) e grava o **Excel**. Detalhes na seção "Parte 4" de [divisao-tarefas.md](divisao-tarefas.md).

### Checklist
- [x] 1 Branch `feature/parte-4-excel` (no fork, a partir da `feature/parte-3-geracao`)
- [x] 2 `src/pipeline.py`: corpus → `unitarizar` → `recuperar` → `gerar_resposta` → Excel; opções `--modelo`, `--tecnica`, `--corpus` (calibração ou 59), `--todos`, `--mock` e `--sobrescrever`
- [x] 3 `src/exportar.py`: aba `respostas` com exatamente `id`, `titulo`, `tematica_1`, `tematica_2`, `metodologias` (separadas por "; "), `modelo`; aba `detalhes` (evidência como texto das frases, status, técnica, versão do prompt); aba `execucao` (máquina, bibliotecas, modelo e digest, técnica, prompt, hashes, data, tempo)
- [x] 4 Uma pasta por execução em `data/sugestoes/`; retoma execução interrompida; erro numa dissertação não para as outras; execução completa não é regravada (só a planilha)
- [x] 5 Teste da regra de ouro (`tests/test_nao_le_analise_manual.py`): nenhum arquivo das Partes 1 a 4 cita a análise manual, e o pipeline em modo mock não abre nenhum arquivo com esse nome
- [x] 6 Seções "Instalação" e "Uso" do `README.md`
- [x] 7 Gerar os Excel finais: os 3 modelos × as 3 técnicas nas 59, com o prompt `v3` (`data/sugestoes/<modelo>__<tecnica>__v3/`)
- [x] 8 ~~Pull request~~ O Franklyn não pediu PR: tudo está no fork, na branch `feature/parte-4-excel`, que contém as Partes 2 (correção), 3, 4 e 5

### Próximo passo
Parte 4 concluída. Qual das 9 planilhas os analistas vão consultar na análise com a ferramenta é decisão do grupo (seção 12 do planejamento): escolher pela que mais concordar com a análise manual empurraria a nova análise na direção da antiga.

---

## Parte 5 — Avaliação das respostas da IA

**Objetivo agora:** medir as execuções da calibração para a Parte 3 escolher modelo e prompt **sem olhar as 59**. Detalhes na seção "Parte 5" de [divisao-tarefas.md](divisao-tarefas.md).

- **Comando:** `python -m src.comparar` avalia todas as pastas de `data/sugestoes/calibracao/` e grava `relatorio.json` de cada uma e `comparacao.json` em `data/avaliacao/` (fora do git). `--sem-embedding` pula as temáticas.
- **Referência da calibração:** `data/avaliacao/referencia_ia_calibracao.json`, escrita por IA às cegas (antes de qualquer execução). Fora do git. **Não é o gabarito do TCC**; o gabarito humano continua sendo `data/calibracao/gabarito_calibracao.json`.

### Checklist
- [x] 1 Ler as execuções (`respostas.json` + `execucao.json`)
- [x] 2 Indicadores sem gabarito: status, tempo, tentativas, eixos cobertos, formato dos itens
- [x] 3 Concordância entre execuções (Jaccard nas metodologias, similaridade nas temáticas)
- [x] 4 Métricas testadas com dados inventados: P/R/F1 por dissertação e por eixo (macro e micro); temáticas por similaridade e5 como par sem ordem, com linha de base
- [~] 5 Gabarito da calibração: referência da IA pronta; o gabarito humano do grupo ainda não existe
- [x] 5b Medir as rodadas de ajuste da Parte 3 (v1, v2, busca corrigida, v3) com a régua congelada; métricas em `data/metricas/calibracao/rodada1` a `rodada4`, cada uma com `origem.json` (sha256 de tudo que entrou). O critério do v3, escrito antes da rodada, manteve o v3 (`rodada4/criterio_v3.json`)
- [x] 6 Relatório em Excel e gráfico por indicador: `python -m src.relatorio_excel PASTA` grava o `.xlsx` ao lado de cada `comparacao.json` e `relatorio.json`. Fica num arquivo à parte para o `src/comparar.py` (a régua) não mudar de sha256
- [ ] 7–9 Análise manual: só quando a professora enviar as respostas

- [x] 5c As 59 com o prompt fixado (v3): indicadores sem gabarito e concordância das 9 execuções em `data/metricas/corpus/`. Sem referência e sem nenhum ajuste; o corpus não foi aberto. `calibracao_v3_mesma_regua.json` mede a calibração do mesmo jeito (só a base no vocabulário), para a comparação ser justa

### Próximo passo
Quando existir o gabarito humano da calibração: medir v1, v2 e v3 contra ele, com a mesma régua. Ganho que só aparece na referência de IA foi ajuste ao estilo dela. Quando a professora enviar a análise manual: tarefas 7 a 9 (importar, medir as 59, teto humano).

---

## Decisões tomadas (só as estratégicas)

| Data | Parte | Decisão | Motivo |
|------|-------|---------|--------|
| 2026-10-07 | Todas | **Objetivo atual: gerar o Excel** (temática 1, temática 2 e metodologias) com a maior precisão possível. Medir se as respostas estão certas (gabarito, comparação com a análise manual, Parte 5) fica para depois de tudo pronto, talvez num código separado | Decisão do Franklyn |
| 2026-10-07 | Todas | Partes 1 e 2 feitas em dupla por Franklyn e Lucas; Partes 3 e 4 seguem com o Lucas | Divisão do grupo |
| 2026-10-07 | 3 | Comparar 3 LLMs de forças diferentes (fraco, forte, mais potente) para ver se a qualidade do Excel muda | Decisão do Franklyn |
| 2026-10-07 | 3 | A base de metodologias é referência, não lista fechada: o LLM pode nomear metodologias incomuns ou com nome de autor, como o resumo descreve, sempre com a frase que justifica | Muitos resumos usam métodos que nenhuma lista cobre; aí entra a interpretação do LLM |
| 2026-10-07 | Todas | Branches no padrão `feature/parte-N-tema`; dependências com versão fixa no `requirements.txt` | Organização e reprodutibilidade |
| 2026-10-07 | Todas | Um único arquivo de progresso (este); registrar só decisões estratégicas | Evitar excesso de Markdown |
| 2026-10-07 | 1 | A Parte 1 criou o mínimo do esqueleto (`src/contratos.py`, `config.py`, `requirements.txt`, `pytest.ini`); cada parte acrescenta a sua seção | O esqueleto era da Parte 4 |
| 2026-10-07 | 1 | O JSON é a fonte (não há PDF): títulos ficam como no original; só espaços, quebras e aspas corrompidas são corrigidos | Fidelidade ao texto das dissertações |
| 2026-10-07 | 1 | Unicode em NFC, não NFKC | O NFKC trocaria "n.º" por "n.o" em 15 lugares |
| 2026-10-07 | 1 | Uma frase só termina em ". ! ? …"; as frases são recortadas do texto pela posição | O spaCy cortava em "et al.", dentro de aspas, em listas e após ":" |
| 2026-10-07 | 1 | Ponto final acrescentado nos resumos D057 e D059, direto no original | O texto estava completo; só faltava o ponto |
| 2026-10-07 | Todas | Calibração com as 20 dissertações de 2022 (C001 a C020), de fora das 59. Exportações do phpMyAdmin ficam fora do git | Ajustar sem olhar as 59; repositório público sem dados de hospedagem |
| 2026-10-07 | 2 | Busca em NumPy, sem FAISS nem ChromaDB; embeddings `intfloat/multilingual-e5-base` na CPU | Compara só ~10 frases e 28 verbetes por vez; testado: NumPy e FAISS dão o mesmo resultado nas 79 dissertações |
| 2026-10-07 | 2 | Base metodológica v1 escrita a partir de manuais, sem olhar as 59 nem as 20; o grupo pode trocá-la | Ter uma base para começar sem enviesar |
| 2026-10-07 | 3 | Os modelos rodam no PC do Lucas (Ryzen 7 5700X, 16 GB de RAM, RTX 3060 Ti 8 GB), não na máquina da RTX 2060 | Mais VRAM; combinado entre Lucas e Franklyn. A aba `execucao` registra a máquina de cada rodada |
| 2026-10-07 | 3 | Modo de "pensar" dos Qwen3/3.5 desligado (`think=False`) | O pensamento fica fora do JSON, deixa cada resposta várias vezes mais lenta e os outros modelos não têm; assim todos respondem do mesmo jeito |
| 2026-10-07 | 3 | Evidência só vale se a frase existe **e foi mostrada ao modelo**; o esquema JSON força o formato do código (`F` + número), mas não quais existem | Com RAG o modelo vê só algumas frases: citar uma que ele não viu é inventar. Não restringir aos códigos válidos mantém mensurável quanto ele inventa (`sem_evidencia`) |
| 2026-10-07 | 3 | Temática vazia ou "não informado" vira status `erro`; "Não informado no resumo" só existe para metodologias e só vale sozinho | Todo resumo tem tema, e o formulário exige duas temáticas |
| 2026-10-07 | 3 | Modelos: `qwen3.5:2b` (fraco), `qwen3.5:4b` (forte), `qwen3.5:9b` (potente), todos `q4_K_M` | Na calibração, o 9b passou o `qwen2.5:7b` (F1 das metodologias +0,16) e empatou com o `qwen3:8b`, com temáticas e formato melhores; o 2b é claramente o fraco; 4b e 9b empatam em qualidade, então a ordem é pelo tamanho |
| 2026-10-07 | 3 | O prompt v3 é o último ajuste; depois, fixar. Nenhuma regra nova depois de ver o resultado do v3: o que sobrar vira limitação registrada. A régua do v3 fica congelada (referência de IA e `src/comparar.py` com o mesmo sha256 do v2) | São 20 dissertações e uma referência só: cada nova rodada de ajuste aproxima o prompt do estilo da referência, não do problema. Quando existir o gabarito humano da calibração, v1, v2 e v3 são medidos contra ele também; ganho que só aparece na referência de IA foi ajuste ao estilo dela |
| 2026-10-07 | 2 | Na técnica `hibrido`, sinal de várias palavras só casa como expressão inteira, e `estudo_de_caso` perde os sinais de lugar e instituição ("no município de", "em uma instituição"…) | O casamento tirava as preposições e cortava em 6 letras: "no município de" virava "munici", e o verbete de estudo de caso ia para o modelo em 10 das 20 da calibração (depois da correção, 1). O qwen3.5:9b copiava o verbete. Achado só com a calibração; o que a avaliação usa da base (id, termo, eixo, sinônimos) não mudou |
| 2026-10-07 | 3 | Critério do `v3`, fixado antes da rodada: fica o `v3` se a média do F1 pareado (v3 − v2) nas 9 combinações (3 modelos × 3 técnicas) for ≥ 0, comparando com o `v2` de `sem_rag` e `denso` das rodadas antigas e de `hibrido` da rodada `__busca-corrigida`. Qualquer uma destas derruba o `v3`: alguma combinação com IC95 pareado inteiro abaixo de zero; acerto@1 das temáticas, na média, mais de 0,05 abaixo do `v2`; itens exatos (nome limpo) abaixo do `v2` | Escrito antes de ver o resultado, para a escolha não ser feita olhando o número. Com 20 dissertações, a média oscila uns ±0,03 só de ruído, daí as travas. Comparar com o `hibrido` antigo daria ao `v3` o crédito da correção da busca |
| 2026-10-07 | 3 | Prompt fixado no `v3` | Critério escrito antes: F1 pareado médio v3 − v2 = +0,005 (≥ 0) e nenhuma trava. A margem é mínima: empate dentro do ruído, com o `v3` melhorando o 9b (+0,078 no `hibrido`, IC acima de zero) e não ajudando o 4b (−0,04 no `sem_rag` e no `denso`, dentro do ruído). Sem regra nova depois do resultado: o que sobrou está nas limitações do RESULTADOS.md |
| 2026-10-07 | 3 | `Campo` e `RespostaIA` entram no `contratos.py` exatamente como na seção 3.1. Tempo e número de tentativas de cada dissertação ficam no `execucao.json` da rodada, fora do contrato | Atende a Parte 5 sem mudar o contrato |
| 2026-10-07 | 2 | Na busca por sentido, cada verbete é representado pelo termo + sinônimos; a técnica `hibrido` soma a busca por palavra exata (BM25, juntos por RRF) | Na calibração, termos de método escritos no resumo que viram verbete: 16/26 com a definição, 20/26 só com termo + sinônimos, 27/27 com `hibrido` |
| 2026-10-07 | 5 | Referência da calibração escrita por IA, às cegas, fora do git, só para ajustar o prompt; não substitui o gabarito humano. Cada metodologia é marcada como dita no resumo (cobrada na revocação) ou interpretação aceitável (não tira precisão) | Sem gabarito humano ainda, a Parte 3 precisava de uma régua; escrita antes das execuções para não copiar o modelo |
| 2026-10-07 | 5 | Metodologia é reconhecida pela base + sinônimos e, se não bater exata, pelo conteúdo: conta todo método cujas palavras estão no item. O formato (item curto e exato × frase) é medido à parte | Os modelos juntam vários métodos num item só; a comparação exata dava zero a respostas certas |
