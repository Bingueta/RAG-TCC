# Técnicas de RAG usadas no projeto de referência (`rag-chatbot`)

**Para que serve este arquivo:** registrar as técnicas, as bibliotecas e as decisões de arquitetura do `rag-chatbot`, que já foram testadas e escolhidas com medições. O TCC não copia esse projeto. A ideia é reaproveitar as escolhas que funcionaram e não gastar tempo testando de novo o que já foi decidido.

Levantamento feito em 29/09/2026 a partir do código (`config.py`, `app/*.py`, `data/golden.json`) e dos 13 artigos de referência. Os números de desempenho citados vêm dos comentários do próprio código, onde as medições foram registradas. Eles não foram medidos de novo aqui.

---

## 1. Visão geral da arquitetura

```
dump MySQL (.sql) ──► SQLite (1 registro por obra) ──┬──► FTS5/BM25 (lexical)
                                                     └──► embeddings e5 ──► FAISS (denso)
PDFs ──► PyMuPDF + limpeza ──► sentence window ──────┬──► FTS5/BM25
                                                     └──► embeddings e5 ──► FAISS

pergunta ──► roteador (regex, sem LLM)
               ├─ metadados ────► SQL determinístico (sem LLM)
               ├─ obras ────────► híbrido nível 1 ─► RRF ─► reranker ─► lista (sem LLM)
               ├─ trecho ───────► híbrido nível 2 ─► RRF ─► reranker ─► LLM extrativo + citação
               └─ interpretativo ► híbrido nível 2 ─► RRF ─► reranker ─► LLM interpretativo + citação
                                                           │
                                          limiar de abstenção calibrado
```

Princípios que aparecem em todo o código:

- **Recall largo, precisão estreita:** buscar muitos candidatos de forma barata e ordenar poucos de forma cara.
- **O LLM só entra quando precisa.** Contagens, listagens e fichas saem direto do SQL, e buscas temáticas saem direto da recuperação.
- **Abster é uma resposta correta.** Quando a evidência não sustenta a resposta, o sistema diz "Não encontrado no texto." em vez de inventar.
- **Tudo é medido.** Há um conjunto de avaliação com perguntas que não têm resposta, justamente para medir alucinação.
- **Hardware modesto.** Tudo roda localmente, e os modelos foram escolhidos pensando em máquinas sem GPU dedicada.

---

## 2. Resumo por etapa

| Etapa | Técnica | Biblioteca | Parâmetros | Motivo registrado no código |
| --- | --- | --- | --- | --- |
| Base de dados | Dump SQL convertido para SQLite, um registro por obra | `sqlite3` (padrão do Python) + parser próprio | — | O chatbot consome "uma obra = um registro completo" |
| Extração de PDF | Texto por página + limpeza | `pymupdf` | páginas com menos de 120 caracteres são descartadas | O pypdf quebrava palavras ("iníci o"), o que prejudica o embedding e o BM25 |
| Chunking | Sentence window | `spacy` (`pt_core_news_sm`) | janela = 2 frases de cada lado; filtro de lixo | Uma frase solta raramente é recuperável |
| Embeddings | Bi-encoder multilíngue | `sentence-transformers` | `intfloat/multilingual-e5-small`, prefixos `query:`/`passage:`, vetores normalizados | O corpus é todo em português; sem os prefixos a qualidade cai |
| Índice denso | Busca exata por produto interno | `faiss-cpu` | `IndexFlatIP` | Com vetores normalizados, o produto interno é igual ao cosseno |
| Índice lexical | BM25 nativo | SQLite FTS5 | `unicode61 remove_diacritics 2` | Captura nomes, siglas e números que o denso "borra" |
| Fusão | Reciprocal Rank Fusion | implementação própria | `k = 60` | Junta os rankings só pela posição, porque BM25 e cosseno têm escalas diferentes |
| Reranking | Cross-encoder | `sentence-transformers` `CrossEncoder` | `BAAI/bge-reranker-v2-m3`, fp16 na GPU, `max_length=512` | MRR 0,40 → 0,96 em relação ao `bge-reranker-base` |
| Geração | LLM local | `ollama` | `qwen2.5:3b-instruct-q4_K_M`, `temperature=0`, `num_ctx=8192` | Melhor custo-benefício em máquina sem GPU dedicada |
| Avaliação | Golden set + curva risco-cobertura | implementação própria | 42 perguntas, metade sem resposta | Sem medição não dá para saber se uma mudança ajudou |

---

## 3. Técnicas em detalhe

### 3.1 Dados e base de conhecimento

- **Parser do dump MySQL** (`db.py`, `_parse_rows`): lê os `INSERT INTO ... VALUES` diretamente do `.sql`, tratando aspas e escapes, sem precisar de um servidor MySQL.
- **Achatamento relacional:** as tabelas (pessoas, funções, palavras-chave, locais, ODS) viram colunas de texto numa única tabela `obras`. Consultar fica simples e o texto para indexar sai pronto.
- **Representação textual da obra** (`texto_da_obra`): título + palavras-chave + autor + orientador + resumo. Título, palavras-chave e resumo carregam o sinal temático; autor e orientador entram para perguntas do tipo "o que fulano pesquisou".
- **Metadados curados ficam no SQL, e o texto solto vai para a recuperação.** É a divisão defendida nos artigos sobre OKF, e o próprio `db.py` diz isso.
- **Ingestão incremental** (`ingest.py`): só reconstrói a base com a flag `--reconstruir-base`, e PDFs já processados são pulados. Assim, adicionar um PDF não obriga a reprocessar todos.

### 3.2 Extração e limpeza de PDF (`extract.py`)

- **PyMuPDF em vez de pypdf:** o pypdf inseria espaços no meio das palavras.
- Normalização Unicode **NFKC** e remoção do hífen condicional.
- Remoção da **hifenização de fim de linha** ("investiga-\ncao" → "investigacao").
- Remoção de **números de página soltos** e de **linhas de sumário** ("1.2 Metodologia ....... 23").
- **Remontagem de parágrafos:** se a linha não termina em pontuação e a próxima começa em minúscula, era quebra de diagramação.
- **Remoção de cabeçalhos e rodapés repetidos:** linhas que aparecem no topo ou no fim de mais de 50% das páginas.
- Princípio anotado no código: *"Garbage in means hallucinations out"*, ou seja, a limpeza vale mais que qualquer ajuste depois.

### 3.3 Chunking: sentence window (`chunking.py`)

- O texto é dividido em frases com o spaCy `pt_core_news_sm`, com NER, lematizador e tagger desligados para ficar mais rápido.
- Cada chunk guarda duas versões:
    - `sentence`: a frase isolada, usada para **exibir e citar**;
    - `window`: a frase mais 2 vizinhas de cada lado. É o texto **indexado** e o que vai para o LLM.
- **Filtro de lixo:** descarta frases com menos de 40 caracteres, com menos de 60% de letras ou com menos de 5 palavras.
- Cada chunk guarda o número da página, para a citação.

### 3.4 Embeddings (`embed.py`)

- Modelo `intfloat/multilingual-e5-small`, escolhido por ser multilíngue.
- Prefixos obrigatórios do e5: `"query: "` na pergunta e `"passage: "` nos documentos.
- `normalize_embeddings=True`, para o produto interno do FAISS ser igual ao cosseno.
- O usuário escolhe GPU ou CPU na inicialização.

### 3.5 Índices (`vectordb.py`, `db.py`)

- **FAISS `IndexFlatIP`:** busca exata, sem aproximação. É suficiente para alguns milhares de vetores. O código registra que o `IndexFlatL2` usado antes media a métrica errada para esses modelos.
- Os ids externos ficam num `.npy` paralelo ao índice.
- **Dois níveis de índice:**
    - **Nível 1 (obra):** um vetor por dissertação, a partir dos metadados. Serve para "quais dissertações falam sobre X".
    - **Nível 2 (trecho):** um vetor por janela de frases do texto completo. Serve para "o que a dissertação X diz sobre Y".
- **FTS5/BM25 nos dois níveis**, com tokenizador `unicode61 remove_diacritics 2`, para que "adesao" encontre "adesão".
- **Sanitização da consulta FTS** (`fts_query`): extrai tokens de 3 ou mais caracteres e junta com `OR`, porque a pontuação da pergunta quebrava o parser do FTS5.

### 3.6 Recuperação híbrida (`retrieve.py`)

```
pergunta ─┬─ denso (FAISS/e5, top 50) ─┐
          │                            ├─ RRF (k=60) ─► pool (25 obras / 40 trechos) ─► cross-encoder ─► top 5 (ou 10)
          └─ BM25 (FTS5, top 50) ──────┘
```

- **Híbrido denso + lexical:** o denso pega paráfrases; o BM25 pega nomes próprios, siglas e números.
- **RRF** (Reciprocal Rank Fusion): pontuação = soma de 1/(60 + posição). Usa só a posição, nunca o score.
- **Rerank com cross-encoder** apenas sobre o pool fundido. Ler pergunta e documento juntos é caro demais para o corpus inteiro.
- **Troca de reranker medida:** o `bge-reranker-base` saturava em português (todos os scores ficavam perto de 0,00004) e piorava a ordem. O `bge-reranker-v2-m3` (base XLM-R) levou o MRR de 0,40 para 0,96.
- **Truncar o texto enviado ao reranker em 450 caracteres** (`OBRA_RERANK_CHARS`): o começo do resumo diz o objeto de estudo, e o resto dilui o sinal. Resultado registrado: MRR 0,87 → 0,96 e 8 vezes mais rápido.
- **Pré-filtro por obra** (`acervos=`): no nível 2, a busca pode ser restrita a uma ou poucas dissertações.
- **Top-k diferente por tipo de pergunta:** 5 passagens para perguntas factuais e 10 para perguntas interpretativas (metodologia, abordagem, tema), porque nessas a evidência fica espalhada em várias frases.
- **Recuperação hierárquica obra → trecho:** a busca temática primeiro acha as obras e depois tenta aprofundar nos trechos dessas obras antes de decidir abster. O score do resumo e o do trecho vivem em escalas diferentes.

### 3.7 Roteamento de perguntas (`chat.py`)

- **Roteador determinístico por regex**, sem LLM. Detecta intenção (contagem, listagem, campo do banco, pergunta interpretativa) e "slots" (ano, número de acervo, ODS, nomes próprios).
- **Não usa text-to-SQL:** um modelo de 3B erra o SQL com frequência. No lugar, há consultas SQL prontas preenchidas pelos slots.
- Quatro rotas, da mais barata para a mais cara:

| Rota | Pergunta típica | Resolve com | Usa LLM? |
| --- | --- | --- | --- |
| `metadados` | "Quantas dissertações de 2020?" | SQL determinístico | Não |
| `obras` | "Quais dissertações falam sobre X?" | Híbrido nível 1 + lista formatada | Não |
| `trecho` | "O que a dissertação X diz sobre Y?" | Híbrido nível 2 + prompt extrativo | Sim |
| `interpretativo` | "Qual a metodologia da dissertação X?" | Híbrido nível 2 (top 10) + prompt interpretativo | Sim |

- **Busca temática sem LLM** (`formatar_lista_obras`): perguntas de descoberta têm resposta plural que já vem pronta da recuperação. Passar isso pelo LLM fazia o modelo de 3B abster mesmo com 5 obras relevantes recuperadas.
- **Resolução implícita da obra:** se há exatamente um PDF ingerido, "a dissertação" se refere a ele.

### 3.8 Geração

- **Ollama** com `qwen2.5:3b-instruct-q4_K_M`, `temperature=0` e `num_ctx=8192`. O padrão de 2048 estourava com 5 passagens, e 3 das perguntas falhavam.
- **Comparação de modelos registrada no `config.py`:**

| Modelo | Cita | Abstém corretamente | RAM (só CPU) | Velocidade |
| --- | --- | --- | --- | --- |
| `qwen2.5:3b` (escolhido) | 72% | 94% | +2,3 GB | 13,9 tokens/s |
| `qwen3:4b` | 89% | 94% | +3,7 GB | 10,8 tokens/s |

  O `qwen3:4b` cita melhor, mas usa 62% mais RAM e é 22% mais lento. A escolha priorizou hardware modesto.
- **Dois prompts de sistema:**
    - `PROMPT_SISTEMA` (**extrativo, estrito**): responde só com as passagens, sem conhecimento externo, sem suposições.
    - `PROMPT_INTERPRETATIVO` (**permissivo com inferência**): o modelo pode e deve nomear a abordagem ("estudo de caso", "entrevista semiestruturada") mesmo que o texto não use esse termo, desde que aponte a evidência concreta. Continua proibido inventar dados (números, instrumentos, locais). O motivo registrado é que o texto raramente escreve "a metodologia é…"; ele descreve o que foi feito.
- **Passagens numeradas** no contexto, no formato `[n] título (ano), acervo, p. X`.
- **Contexto truncado** em 700 caracteres por passagem (900 no modo interpretativo). Resumos longos com 5 passagens somavam cerca de 3 mil tokens e contribuíam para o modelo pequeno degenerar.

### 3.9 Citação e salvaguardas contra alucinação

- **Citação única no final** (`Fontes: [1][2]`) em vez de citação por frase. A citação por frase foi testada e o `qwen2.5:3b` degenerava (respondia só "[1]") em cerca de 40% das perguntas.
- **Validação das citações** (`validar_citacoes`): ids fora do intervalo de passagens enviadas são descartados, porque citar uma passagem inexistente prova que o modelo inventou. Se o modelo não escreveu "Fontes:" mas citou no meio do texto, essas citações são aproveitadas.
- **Token de abstenção** `SEM_EVIDENCIA`, verificado sem diferenciar maiúsculas de minúsculas (o modelo já escreveu "Sem_EvidENCIA").
- **Proteção contra degeneração:** resposta com menos de 5 caracteres de prosa vira abstenção.
- **Fontes de reserva:** se o modelo respondeu e esqueceu de citar, todas as passagens enviadas são mostradas como fonte.
- **Limiar de abstenção pelo score do reranker** (`RERANK_MIN_SCORE = 0.003`), calibrado pela curva risco-cobertura:

| Limiar | Cobertura | Alucinação |
| --- | --- | --- |
| 0,001 | 93,8% | 16,7% |
| **0,003 (escolhido)** | **93,8%** | **0,0%** |
| 0,010 | 62,5% | 0,0% |

  O código anota que esse número é uma propriedade do modelo e deve ser recalibrado se o embedding ou o reranker mudarem.

### 3.10 Avaliação (`eval.py`, `data/golden.json`)

- **Golden set com 42 perguntas:** 28 de busca temática, 8 de metadados e 6 de trecho. **21 não têm resposta no acervo**, e é essa metade que mede alucinação.
- **Perguntas escritas com palavras diferentes das do texto** (ex.: "Por que pessoas mais velhas largam o remédio da pressão?"), para testar paráfrase e não só coincidência de palavras.
- Blocos de avaliação:
    1. **Roteamento:** a pergunta caiu na rota certa?
    2. **Recuperação:** MRR, top-1 e recall@5 da obra correta.
    3. **Metadados:** a resposta SQL contém o valor esperado?
    4. **Abstenção:** matriz 2×2 (respondível × respondida). A única célula perigosa é "não respondível e respondida", que é alucinação por definição.
- **Varredura de limiar com orçamento de alucinação:** escolhe o limiar de maior cobertura com alucinação ≤ 5% (ou 10%, 20%).
- **Avaliação separada por rota:** o score do retriever separa bem assunto fora do acervo, mas não separa **premissa falsa** sobre uma obra que existe (a recuperação acha passagens relevantes de verdade).
- Execução: `python -m app.eval` (sem LLM) ou `python -m app.eval --llm`.

### 3.11 Engenharia

- **UTF-8 forçado** no console do Windows (o cp1252 quebrava prints em português).
- **Todos os parâmetros num único `config.py`**, com a justificativa e a medição de cada escolha em comentário.
- Carregamento preguiçoso (lazy) dos índices e do reranker, com cache em memória.
- Mensagem clara quando o Ollama está fora do ar; a recuperação continua funcionando.

---

## 4. Artigos de referência × o que foi usado

| Artigo | O que propõe | Usado no `rag-chatbot`? |
| --- | --- | --- |
| *Advanced Retrieval Techniques in RAG* (Parte 1) | RAG básico com LlamaIndex; apresenta sentence window e parent document; avaliação com TruLens (relevância do contexto, groundedness, relevância da resposta) | **Em parte.** Usa o sentence window. Não usa LlamaIndex nem TruLens; a avaliação é própria (`eval.py`) |
| *Part 02 — Parent Document Retrieval* | Indexar pedaços pequenos (filhos) e mandar ao LLM o bloco maior (pai) | **Não como no artigo.** A ideia de "buscar pequeno, entregar maior" aparece no sentence window e na busca obra → trecho |
| *Part 03 — Sentence Window Retrieval* | Indexar a frase com uma janela de vizinhas; testa tamanhos de janela contra groundedness e custo | **Sim.** É o chunking do projeto (`window_size=2`), com uma diferença: o projeto indexa a janela e usa a frase isolada para citar |
| *Building a RAG Pipeline for 10M Documents With Near-Zero Hallucination* | Híbrido denso + BM25, RRF, recall largo e reranker, citação por id de passagem, remoção de citação inventada, token de abstenção, roteador, golden set com metade sem resposta, matriz 2×2, curva risco-cobertura com orçamento; também chunks contextualizados, verificação de cada afirmação (claim) com juiz de fidelidade, decomposição de pergunta, checagem de premissa falsa, agente com refinamento, LanceDB em escala | **É a principal fonte.** Usados: híbrido, RRF (k=60), recall largo e reranker, citação por id com validação, token de abstenção, roteador, golden set meio a meio, matriz 2×2, curva risco-cobertura. **Não usados:** chunks contextualizados, verificação por claim/NLI, decomposição, checagem de premissa falsa, agente, LanceDB. Todos exigem mais chamadas a um LLM grande (o artigo usa um modelo de 32B numa H100), o que não cabe num modelo de 3B local |
| *Vectorless RAG* | Recuperação sem embeddings (BM25, full-text, metadados); busca exata e determinística reduz alucinação | **Em parte.** O BM25 via FTS5 e a rota de metadados por SQL seguem essa linha, mas o projeto é híbrido e mantém os vetores |
| *Beyond RAG: How Google's OKF is Replacing the Vector Database* | Conhecimento estável e curado em arquivos Markdown + YAML, consultado de forma determinística | **A ideia sim, o formato não.** Metadados curados são consultados por SQL (citado no `db.py`); não há pacote OKF em Markdown |
| *Did Google Just Kill RAG? What OKF Actually Replaces* | OKF para fatos estáveis e RAG para texto não estruturado; um não substitui o outro | **Sim, como princípio:** SQL para campos curados, RAG para o texto |
| *OKF and RAG: The Ultimate AI Agent Architecture* | Roteador que tenta o caminho determinístico primeiro e cai no RAG depois | **Sim.** O roteador manda para o SQL quando dá e cai na busca temática quando o SQL não sabe responder |
| *RAG Killer Really? Why Google's OKF is "RAG Killer"* | Sistema de "dois motores" (curado + vetorial) em C#/.NET | **A ideia sim** (mesma divisão SQL + RAG); a implementação não se aplica |
| *Graphify, OKF or Both? Beyond RAG for Codebases* | Grafos de código (AST) e OKF para agentes de programação | **Não.** É voltado a código-fonte, não a documentos acadêmicos |
| *Standardizing Agent Memory: Self-Updating Codebase Knowledge Graph with OKF* | Wiki OKF que se atualiza sozinha, para memória de agentes | **Não.** Fora do escopo |
| *MegaRAG: Stop Chunking Blindly* | GraphRAG multimodal (texto + figuras), grafo de entidades por página | **Não.** Exige extração de entidades com LLM grande e é voltado a documentos com figuras |
| *Survey Research about RAG* | Panorama: reranking, compressão, filtragem, fusão, reescrita/expansão de consulta, roteamento, recuperação adaptativa, GraphRAG, fine-tuning de encoders | **Em parte.** Usados: reranking, fusão (híbrido + RRF), roteamento, filtragem (pré-filtro por obra e limiar), uma compressão simples (truncar passagens) e recuperação adaptativa simplificada (rotas que pulam o LLM). Não usados: reescrita/expansão de consulta (HyDE), GraphRAG, fine-tuning |

---

## 5. O que isso significa para o TCC

O TCC trabalha com título, resumo e palavras-chave de 59 dissertações e ajuda a identificar a temática 1, a temática 2 e as metodologias de cada uma. A ferramenta é automática: roda em lote e gera uma planilha, sem chat. Nem tudo do projeto de referência se aplica.

| Técnica | Aplicar no TCC? | Observação |
| --- | --- | --- |
| e5 multilíngue com prefixos + vetores normalizados | Sim | Mesmo idioma, mesma escolha |
| FAISS `IndexFlatIP` | Sim | Com poucos milhares de frases, a busca exata basta |
| BM25 (FTS5) + RRF | Sim | Útil para termos exatos de metodologia ("grupo focal", "survey") |
| Reranker `bge-reranker-v2-m3` | Opcional | Com um resumo por vez o pool é pequeno; usar se a recuperação de frases ou de verbetes falhar |
| Sentence window | Adaptar | O resumo é curto: indexar frases (unidades de registro) com janela de 1, e citar a frase isolada |
| Limpeza de PDF (PyMuPDF etc.) | Em parte | Os resumos estão num PDF (uma dissertação por página). Basta extrair o texto uma vez para montar o `corpus.json`, com a normalização Unicode e a remoção de hifenização; o resto da limpeza (sumário, cabeçalhos repetidos) não é necessário |
| `PROMPT_INTERPRETATIVO` (nomear e apontar a evidência) | **Sim, é o ponto de partida** | É exatamente a tarefa de temáticas e metodologias |
| Citação por id + validação de ids | Sim | Citar ids de frases do resumo e descartar ids inexistentes |
| Citação única em vez de por frase | Sim, com modelo de 3B | Com modelo maior, dá para exigir evidência por campo |
| Token de abstenção + "não informado no resumo" | Sim | Muitos resumos não dizem o método |
| Proteção contra degeneração, `temperature=0` | Sim | Mesmos modelos locais |
| Roteador de 4 rotas, SQL de metadados | Não | A ferramenta é automática e faz sempre a mesma tarefa; não há perguntas para rotear |
| Golden set, matriz 2×2, curva risco-cobertura | Adaptar | A avaliação principal do TCC é a comparação com a análise manual, mas um mini-golden ajuda a calibrar a ferramenta antes de o grupo usá-la |
| `config.py` único com justificativas | Sim | Ajuda a fixar e documentar a configuração usada pelo grupo |
| Escolha de modelo por custo (qwen2.5:3b × qwen3:4b) | Revisar | Para interpretar metodologias, vale testar também um modelo de 7B–8B: a máquina prevista (RTX 2060 com 6 GB) deve comportar um 7B–8B compactado, a confirmar em teste. Como a ferramenta é automática, a velocidade pesa menos, mas importa: cada combinação de modelo × técnica roda as 59 dissertações |
