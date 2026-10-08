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
| 3 — Geração com LLM e validação | Em andamento (branch `feature/parte-3-geracao`) | Lucas |
| 4 — Orquestração, configuração e Excel | Depois da Parte 3 | Lucas |
| 5 — Avaliação das respostas da IA | Depois de tudo pronto (fora do objetivo atual) | a definir |

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
- [x] 1.1 Criar a branch `feature/parte-3-geracao` a partir da `main` atualizada (no fork `LucasFeres/RAG-TCC`; o PR vai para o repo do grupo)
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
- [~] 5.2 Ajustar o prompt **olhando só a calibração**; guardar cada versão (`v1`, `v2`…); fixar a versão final antes de rodar nas 59 — `v2` medido: o "estudo de caso" inventado caiu de 20 para 5 nas 9 rodadas, e a fonte dos dados (documental, secundários) passou a aparecer; o que sobrou vem da busca `hibrido` (ver decisão abaixo); o `v3` é o último

**Etapa 6 — Fechamento**
- [ ] 6.1 Testes passando; pull request `[Parte 3] Geração com LLM e validação`

### Próximo passo
Decisão do Lucas (com o Franklyn, que divide a Parte 2) sobre o defeito da busca `hibrido`: os sinais de várias palavras da base casam como uma palavra só (`_tokens` tira as preposições e corta em 6 letras), e "no município de" vira "munici". Assim, o verbete `estudo_de_caso` é oferecido em 10 das 20 da calibração (no `denso`, em 1). Depois da correção: rodar o `hibrido` de novo, escrever o `v3` e fixar.

---

## Parte 4 — Orquestração, configuração e Excel

**Objetivo:** um comando que pega as 59 dissertações, roda busca (Parte 2) + LLM (Parte 3) e grava o **Excel**. Detalhes na seção "Parte 4" de [divisao-tarefas.md](divisao-tarefas.md).

### Checklist
- [ ] 1 Branch `feature/parte-4-excel`
- [ ] 2 `src/pipeline.py`: corpus → `unitarizar` → `recuperar` → `gerar_resposta` → Excel; opções `--modelo`, `--tecnica`, `--corpus` (calibração ou 59) e `--todos` (todos os modelos × técnicas)
- [ ] 3 `src/exportar.py`: aba `respostas` com exatamente `id`, `titulo`, `tematica_1`, `tematica_2`, `metodologias` (separadas por "; "), `modelo`; aba `detalhes` (frases de evidência, status, técnica, versão do prompt); aba `execucao` (máquina, modelo, técnica, prompt, data)
- [ ] 4 Uma pasta por execução em `data/sugestoes/` (ex.: `qwen2.5-7b-instruct__hibrido__v1/`); retomar execução interrompida; erro numa dissertação não para as outras
- [ ] 5 Teste da regra de ouro: nenhuma parte do pipeline lê `data/analise_manual.json`
- [ ] 6 Seção "Instalação" do `README.md`
- [ ] 7 Gerar os Excel finais: os 3 modelos nas 59 (técnica `hibrido`; `sem_rag` como comparação, se der tempo)
- [ ] 8 Pull request `[Parte 4] Pipeline e Excel`

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
| 2026-10-07 | 3 | `Campo` e `RespostaIA` entram no `contratos.py` exatamente como na seção 3.1. Tempo e número de tentativas de cada dissertação ficam no `execucao.json` da rodada, fora do contrato | Atende a Parte 5 sem mudar o contrato |
| 2026-10-07 | 2 | Na busca por sentido, cada verbete é representado pelo termo + sinônimos; a técnica `hibrido` soma a busca por palavra exata (BM25, juntos por RRF) | Na calibração, termos de método escritos no resumo que viram verbete: 16/26 com a definição, 20/26 só com termo + sinônimos, 27/27 com `hibrido` |
