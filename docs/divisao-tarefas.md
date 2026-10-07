# Divisão de tarefas do RAG

**Situação:** proposta, com as decisões da seção 0 já tomadas e aguardando aprovação final do grupo. Nada do que está aqui foi implementado ainda.

Este documento divide a construção do RAG em **5 partes**, uma por pessoa, que podem ser feitas **ao mesmo tempo**. Para isso funcionar, ele define os **contratos** (o formato exato dos dados que uma parte entrega para a outra) e os **dados de exemplo** (mocks) que cada parte usa para trabalhar sem esperar as outras.

Ele se baseia em [PLANEJAMENTO_TCC.md](PLANEJAMENTO_TCC.md) e em [TECNICAS_RAG_REFERENCIA.md](TECNICAS_RAG_REFERENCIA.md). Os termos técnicos estão explicados no glossário da seção 2 do planejamento.

**Escopo desta etapa:** o sistema roda em **lote**, sem conversa. Ele recebe o JSON com as 59 dissertações (já existe: `data/brutos/dissertacoes.json`), extrai **temática 1, temática 2 e metodologias** de cada uma, e grava uma **planilha Excel**. Nesta etapa, o objetivo é **só gerar as respostas da IA**. A comparação com as respostas da análise manual vem depois que o RAG estiver pronto, quando a professora enviar essas respostas ao grupo. O mesmo processo roda com **modelos diferentes** e **técnicas de RAG diferentes**, trocados por configuração.

---

## 0. Decisões tomadas

Os conflitos entre o pedido desta etapa e o planejamento foram resolvidos assim. O planejamento já foi atualizado.

| # | Assunto | Decisão |
| --- | --- | --- |
| C1 | Formato da ferramenta | **Automático:** roda em lote e gera planilha, sem chat e sem tela. A análise das 59 **por pessoas usando a ferramenta** continua planejada, depois desta etapa: os analistas consultam a planilha da IA como apoio. Esta divisão cobre a construção da ferramenta e a avaliação da **IA sozinha × análise manual** |
| C2 | Evidência na planilha | A primeira aba (`respostas`) tem **exatamente as 6 colunas** pedidas. Evidências, status e versão do prompt ficam na segunda aba (`detalhes`) |
| C3 | Ajuste sem "roubar" | Prompt e base metodológica são ajustados só com **3 a 5 dissertações de fora das 59** (o grupo consegue). Depois são fixados, e só então todos os modelos e técnicas rodam nas 59 |
| C4 | Formato da base metodológica | **JSON**: `data/base_metodologia.json` |
| C5 | Respostas da análise manual | **Ficam para depois:** a professora vai enviar as respostas do grupo quando o RAG estiver pronto. Nesta etapa só importam as respostas da IA. A leitura do arquivo da professora fica como tarefa posterior da Parte 5 |
| C6 | Formato do JSON real | O original `data/brutos/dissertacoes.json` fica intacto. A Parte 1 gera o `corpus.json` com `id` (D001 a D059, na ordem do original) e palavras-chave em lista; `ano` é opcional. Como o Forms identificava a dissertação pelo **título colado**, a ligação com as respostas humanas (depois) será feita pelo título |
| C7 | Arquivos novos na estrutura | Aceitos (seção 6.1). A pasta `app/` fica sem uso nesta etapa |
| C8 | Divisão só de código | Aceita. A base metodológica entra na Parte 2; a escrita do TCC fica fora desta divisão |

---

## 1. Visão geral

```
                    ┌──────────── Parte 4: orquestra tudo, lê config.py, grava o Excel ────────────┐
                    │                                                                              │
data/brutos/     ─► Parte 1 ─► Parte 2 ─► Parte 3 ─────────────────────────────► planilha .xlsx ─► Parte 5 ─► relatório
                    (dados e   (base de   (LLM + prompt +                         (data/sugestoes/)  (compara com a
                     frases)   conhecim.  validação)                                                  análise manual)
                               + busca)
```

| Parte | Nome | Em uma frase | Dificuldade |
| --- | --- | --- | --- |
| 1 | Dados e unitarização | Gera o `corpus.json` a partir do JSON original, limpa o texto e quebra cada resumo em frases numeradas | Fácil a média |
| 2 | Base de conhecimento e busca | Escreve a base de metodologias e busca as frases e os verbetes certos para cada dissertação | Difícil |
| 3 | Geração com LLM e validação | Monta o prompt, chama o modelo no Ollama e confere se a resposta é válida | Difícil |
| 4 | Orquestração, configuração e Excel | Liga as partes, permite trocar modelo e técnica pela linha de comando e grava a planilha | Média |
| 5 | Avaliação das respostas da IA | Agora: indicadores sem gabarito, comparação entre modelos e técnicas e gabarito da calibração. Depois: comparação com a análise manual | Média a difícil |

---

## 2. O que o RAG recupera neste projeto

RAG significa buscar trechos de texto e entregá-los ao modelo antes de ele responder. Aqui o sistema busca em **três fontes**. Só a segunda é conhecimento que o modelo não tem no próprio resumo.

| Fonte | O que é buscado | Para qual campo | Observação |
| --- | --- | --- | --- |
| **Frases do próprio resumo** | As frases que falam do objetivo e do objeto (temáticas) e as que descrevem o que foi feito: coleta, participantes, análise (metodologias) | Temáticas e metodologias | Cada frase tem um código (F1, F2…) que o modelo cita como evidência. **Atenção:** o resumo é curto (cerca de 8 a 15 frases), então essa busca serve mais para **focar e citar** do que para encontrar algo escondido |
| **Base metodológica** (`data/base_metodologia.json`) | Os verbetes mais parecidos com as frases de método. Exemplo: a frase "foram realizadas entrevistas com 12 professores" recupera o verbete "Entrevista semiestruturada", com definição e sinais típicos | Metodologias | É a **base de conhecimento de verdade** do RAG: ajuda o modelo a dar o nome técnico certo ao que o resumo descreve (TECNICAS 3.8, "prompt interpretativo") |
| **Títulos de dissertações parecidas do corpus** (opcional) | Os títulos das 3 dissertações mais parecidas | Temáticas | Ajuda a manter nomes de temas consistentes entre dissertações. Nunca usa respostas humanas |

### Técnicas de RAG a comparar

Cada técnica é um valor de configuração (`tecnica`). Todas vêm do projeto de referência (TECNICAS, seções 3.4 a 3.6).

| Técnica | Como funciona | Obrigatória? |
| --- | --- | --- |
| `sem_rag` | Manda o resumo inteiro, sem busca e sem base metodológica. É a **linha de base**, que mostra se o RAG faz diferença | Sim |
| `denso` | Busca por sentido: embeddings `multilingual-e5` com prefixos `query:` e `passage:`, mais FAISS | Sim |
| `hibrido` | Busca por sentido + busca por palavra exata (BM25), juntas por RRF (k = 60) | Sim |
| `hibrido_rerank` | `hibrido` + reordenação com o reranker `bge-reranker-v2-m3` | Opcional, se sobrar tempo |

### Pontos em aberto sobre o RAG

- **A base metodológica ainda não existe.** Ela é escrita pela Parte 2, com revisão da orientadora. Sem ela, as técnicas `denso` e `hibrido` só buscam frases do resumo.
- **Talvez o ganho do RAG nas temáticas seja pequeno**, justamente porque o resumo é curto. A comparação com `sem_rag` vai mostrar isso, e esse já é um resultado para o TCC.

---

## 3. Contratos entre as partes

Contrato é o combinado: "eu entrego os dados neste formato, você recebe neste formato". Se todo mundo respeitar os contratos, cada parte pode ser feita sozinha e as peças se encaixam no final.

**Regra:** os contratos ficam num arquivo único, `src/contratos.py`, criado no esqueleto. **Ninguém altera esse arquivo sozinho.** Qualquer mudança passa por pull request aprovado pelas partes afetadas.

### 3.1 Tipos de dados (`src/contratos.py`)

Proposta. São `dataclasses` do Python, isto é, "fichas" com campos de nome e tipo fixos.

```python
from dataclasses import dataclass, field

# ---------- Parte 1 entrega ----------

@dataclass
class Dissertacao:
    id: str                       # "D001"
    titulo: str
    resumo: str
    palavras_chave: list[str]
    ano: int | None = None        # opcional (decisão C6)

@dataclass
class Frase:
    id: str                       # "F1", "F2"... a numeração recomeça em cada dissertação
    texto: str

@dataclass
class DissertacaoUnitarizada:
    dissertacao: Dissertacao
    frases: list[Frase]           # na ordem em que aparecem no resumo

# ---------- Parte 2 entrega ----------

@dataclass
class Verbete:
    id: str                       # "entrevista_semiestruturada"
    termo: str                    # "Entrevista semiestruturada"
    eixo: str                     # natureza, objetivos, abordagem, procedimento, coleta ou analise
    definicao: str
    sinais: list[str]             # expressões típicas no resumo: "roteiro de entrevista", "entrevistados"
    sinonimos: list[str]          # outras formas de escrever: "entrevistas semi-estruturadas"

@dataclass
class TrechoRecuperado:
    frase_id: str                 # "F3"
    texto: str
    score: float                  # quanto maior, mais parecido

@dataclass
class Contexto:
    dissertacao_id: str
    tecnica: str                  # sem_rag, denso, hibrido ou hibrido_rerank
    frases_tematicas: list[TrechoRecuperado]
    frases_metodologia: list[TrechoRecuperado]
    verbetes: list[Verbete]
    titulos_parecidos: list[str] = field(default_factory=list)

# ---------- Parte 3 entrega ----------

@dataclass
class Campo:
    texto: str                    # "Saúde do idoso"
    evidencia: list[str]          # ["F2"]
    status: str = "ok"            # ok, sem_evidencia, nao_informado ou erro

@dataclass
class RespostaIA:
    dissertacao_id: str
    tematica_1: Campo
    tematica_2: Campo
    metodologias: list[Campo]     # uma metodologia por Campo, cada uma com sua evidência
    modelo: str                   # "qwen2.5:7b-instruct"
    versao_prompt: str            # "v1"
    tecnica: str                  # igual a Contexto.tecnica
    saida_bruta: str = ""         # texto original do modelo, para investigar erros

# ---------- Parte 5 usa ----------

@dataclass
class RespostaHumana:
    dissertacao_id: str
    analista: str                 # "A1" a "A5", sempre anonimizado
    tematica_1: str
    tematica_2: str
    metodologias: str             # texto como foi digitado no Forms
```

Quando o resumo não informa o método, `metodologias` vira uma lista com um único item: `Campo(texto="Não informado no resumo", evidencia=[], status="nao_informado")`.

### 3.2 Entrada: do JSON original ao `data/corpus.json`

**Original** (`data/brutos/dissertacoes.json`, 59 itens, não editar):

```json
[
  {"titulo": "...", "resumo": "...", "palavras_chave": "Palavra um, Palavra dois, Palavra três"}
]
```

**Gerado pela Parte 1** (`data/corpus.json`), com `id` e palavras-chave em lista; `ano` é opcional porque o original não tem:

```json
[
  {"id": "D001", "titulo": "...", "resumo": "...", "palavras_chave": ["Palavra um", "Palavra dois", "Palavra três"]}
]
```

Se o formato do original mudar, só a Parte 1 precisa mudar. O resto do sistema recebe sempre `Dissertacao`.

### 3.3 Base metodológica: `data/base_metodologia.json`

```json
[
  {
    "id": "estudo_de_caso",
    "termo": "Estudo de caso",
    "eixo": "procedimento",
    "definicao": "Investigação aprofundada de um ou poucos casos (uma instituição, um grupo, um município).",
    "sinais": ["o caso de", "em uma escola de", "na cidade de"],
    "sinonimos": ["estudo de caso único", "estudo de casos múltiplos"]
  }
]
```

Os eixos e os termos iniciais estão na seção 6.3 do planejamento. A Parte 5 usa os `sinonimos` para reconhecer que "entrevistas semi-estruturadas" e "entrevista semiestruturada" são a mesma coisa. Por isso existe **uma única lista** de metodologias, mantida pela Parte 2.

### 3.4 Saída: a planilha Excel

Cada execução (combinação de modelo, técnica e versão do prompt) grava uma pasta própria:

```
data/sugestoes/qwen2.5-7b-instruct__hibrido__v1/
├── respostas.xlsx
└── respostas.json        # as RespostaIA completas, para a Parte 5 e para conferência
```

O `:` do nome do modelo vira `-`, porque o Windows não aceita `:` em nome de pasta.

**Aba `respostas`.** Exatamente as 6 colunas pedidas, nesta ordem:

| id | titulo | tematica_1 | tematica_2 | metodologias | modelo |
| --- | --- | --- | --- | --- | --- |
| D001 | ... | Saúde do idoso | Adesão ao tratamento | Pesquisa qualitativa; Estudo de caso; Entrevista semiestruturada; Análise de conteúdo | qwen2.5:7b-instruct |

As metodologias ficam numa coluna só, separadas por `"; "` (ponto e vírgula seguido de espaço).

**Aba `detalhes`** (decisão C2): `id`, `evidencia_tematica_1`, `evidencia_tematica_2`, `evidencia_metodologias`, `status`, `tecnica`, `versao_prompt`. As evidências aparecem como texto das frases, para quem lê a planilha não precisar procurar F2 no resumo.

**Aba `execucao`:** data e hora, máquina (CPU, RAM e GPU), modelo, técnica, versão do prompt, modelo de embedding, `temperature`, `seed`, quantas dissertações deram erro.

### 3.5 Respostas humanas: `data/analise_manual.json`

**Só depois que o RAG estiver pronto:** gerado pela Parte 5 a partir do arquivo que a professora vai enviar (formato ainda desconhecido). **Não vai para o GitHub** (o `.gitignore` já bloqueia).

```json
[
  {"dissertacao_id": "D001", "analista": "A3", "tematica_1": "...", "tematica_2": "...", "metodologias": "..."}
]
```

### 3.6 Relatório de avaliação

A Parte 5 grava em `data/avaliacao/<mesmo nome da pasta da execução>/relatorio.xlsx`. Essa pasta também deve ficar **fora do GitHub**, porque contém trechos das respostas humanas. Isso será acrescentado ao `.gitignore` no esqueleto.

### 3.7 Configuração: `config.py`

Um arquivo único, como manda a regra de reprodutibilidade. Ele é dividido em **seções, uma por parte**, e cada pessoa edita só a sua. Como cada pessoa mexe em linhas diferentes, o Git junta as mudanças sem conflito. Os valores abaixo são exemplos; cada parte justifica os seus num comentário.

```python
# ===== PARTE 1: dados =====
CAMINHO_ORIGINAL = "data/brutos/dissertacoes.json"
CAMINHO_CORPUS = "data/corpus.json"
CAMINHO_CALIBRACAO = "data/calibracao/corpus_calibracao.json"

# ===== PARTE 2: base e busca =====
CAMINHO_BASE = "data/base_metodologia.json"
MODELO_EMBEDDING = "intfloat/multilingual-e5-base"
TECNICAS = ["sem_rag", "denso", "hibrido"]
TOP_K_FRASES = 5
TOP_K_VERBETES = 5

# ===== PARTE 3: geração =====
VERSAO_PROMPT = "v1"
TEMPERATURA = 0
SEED = 42
NUM_CTX = 8192

# ===== PARTE 4: execução =====
MODELOS = ["qwen2.5:7b-instruct", "llama3.1:8b", "qwen2.5:3b-instruct"]
CORPUS_ATIVO = "calibracao"      # só muda para "corpus" depois de fixar prompt e base (decisão C3)
USAR_MOCKS = False

# ===== PARTE 5: avaliação =====
CAMINHO_GABARITO_CALIBRACAO = "data/calibracao/gabarito_calibracao.json"
CAMINHO_ANALISE_MANUAL = "data/analise_manual.json"   # fora do git; só existe depois
```

**Trocar o modelo sem mexer no código:** pela linha de comando, por exemplo `python -m src.pipeline --modelo llama3.1:8b --tecnica denso`. Sem argumentos, valem os padrões do `config.py`.

### 3.8 Funções que cada parte oferece

Estas são as "portas de entrada" de cada parte. As outras partes chamam **só estas funções**; o que há dentro de cada uma é livre.

| Parte | Função | Recebe | Devolve |
| --- | --- | --- | --- |
| 1 | `carregar_corpus(caminho)` | caminho do JSON | `list[Dissertacao]` (com erro claro se faltar campo) |
| 1 | `unitarizar(dissertacao)` | `Dissertacao` | `DissertacaoUnitarizada` |
| 1 | `preparar_corpus(caminho_original, caminho_saida)` | caminho do original | nada; grava `data/corpus.json` |
| 2 | `carregar_base(caminho)` | caminho do JSON | `list[Verbete]` |
| 2 | `construir_indice(corpus, verbetes)` | `list[DissertacaoUnitarizada]`, `list[Verbete]` | nada; salva em `data/indices/` |
| 2 | `recuperar(dissertacao, tecnica)` | `DissertacaoUnitarizada`, nome da técnica | `Contexto` |
| 3 | `gerar_resposta(dissertacao, contexto, modelo)` | `DissertacaoUnitarizada`, `Contexto`, nome do modelo | `RespostaIA` (nunca trava; em erro, devolve `status="erro"`) |
| 3 | `montar_prompt(dissertacao, contexto, versao)` | idem + versão do prompt | `str` (testável sem Ollama) |
| 3 | `validar(resposta, dissertacao)` | `RespostaIA`, `DissertacaoUnitarizada` | `RespostaIA` com os status corrigidos |
| 4 | `executar(modelo, tecnica, corpus)` | nomes; caminho do corpus | caminho da pasta da execução |
| 4 | `exportar_excel(respostas, corpus, pasta)` | `list[RespostaIA]`, `list[Dissertacao]`, pasta | caminho do `.xlsx` |
| 5 | `avaliar_sem_gabarito(pasta_execucao)` | pasta da execução | caminho do relatório |
| 5 | `importar_respostas(caminho)` (depois) | arquivo enviado pela professora | `list[RespostaHumana]` (já anonimizadas) |
| 5 | `avaliar_contra_gabarito(pasta_execucao, referencias, verbetes)` | pasta, `list[RespostaHumana]` (gabarito da calibração agora; análise manual depois), `list[Verbete]` | caminho do relatório |
| 5 | `comparar_execucoes(pasta_sugestoes)` | `data/sugestoes/` | tabela: uma linha por execução, com as métricas |

### 3.9 Dados de exemplo (mocks)

Ficam em `tests/exemplos/` e são criados no esqueleto. **São dissertações inventadas**, nunca uma das 59. Assim ninguém ajusta nada olhando o corpus real (decisão C3).

| Arquivo | Conteúdo | Quem usa |
| --- | --- | --- |
| `corpus_exemplo.json` | 3 dissertações inventadas: uma qualitativa, uma quantitativa e uma que não informa o método | Partes 1 e 4 |
| `frases_exemplo.json` | As mesmas 3 já divididas em frases (F1, F2…) | Partes 2, 3 e 4 |
| `base_metodologia_exemplo.json` | 6 verbetes, um por eixo | Partes 2 e 5 |
| `contexto_exemplo.json` | Um `Contexto` pronto para cada uma das 3 | Partes 3 e 4 |
| `saidas_llm/` | Respostas "cruas" de modelo: uma correta, uma com JSON quebrado, uma citando a frase F9 (que não existe), uma vazia | Parte 3 |
| `respostas_ia_exemplo.json` | `RespostaIA` das 3 | Partes 4 e 5 |
| `respostas_ia_exemplo.xlsx` | A planilha no formato da seção 3.4 | Parte 5 |
| `respostas_humanas_exemplo.json` | Respostas inventadas de 2 analistas (A1 e A2) para as 3, com acertos e erros de propósito; servem de gabarito inventado | Parte 5 |

`src/mocks.py`, também criado no esqueleto, traz versões falsas de `unitarizar`, `recuperar` e `gerar_resposta`, que só devolvem os dados de exemplo. Com `--mock`, o pipeline inteiro roda **desde o primeiro dia**, mesmo sem nenhuma parte pronta.

---

## 4. As 5 partes

Cada parte tem: objetivo, arquivos, entradas e saídas, tarefas em ordem, critério de pronto, como testar sozinha e dificuldade.

### Parte 1 — Dados e unitarização

**Objetivo:** entregar as dissertações limpas, com `id`, conferidas e divididas em frases numeradas. Todo o resto depende da qualidade disso. Como diz o projeto de referência: *lixo na entrada vira alucinação na saída*.

**Arquivos:** `src/preparar_dados.py`, `src/unitarizar.py`, `data/corpus.json` (gerado), `data/calibracao/`, `tests/test_parte1_*.py`. O original `data/brutos/dissertacoes.json` é só lido, nunca alterado.

**Entradas e saídas:** `data/brutos/dissertacoes.json` → `data/corpus.json` → `list[Dissertacao]` → `list[DissertacaoUnitarizada]`

**Tarefas, em ordem:**

1. `carregar_corpus`: ler o JSON e conferir os campos. Os `id` não podem repetir, e título e resumo não podem estar vazios. Em caso de problema, a mensagem de erro deve ser clara, por exemplo: *"D017 está sem resumo"*.
2. `normalizar_texto`: padronizar Unicode (NFKC), espaços, quebras de linha e hífen de fim de linha ("investiga-\nção" vira "investigação").
3. `unitarizar`: dividir o resumo em frases com spaCy `pt_core_news_sm` e numerar F1, F2…. **Não descartar frases curtas.** O filtro de lixo do projeto de referência foi feito para PDF completo; num resumo, toda frase pode ser evidência.
4. `preparar_corpus`: ler o original e gerar `data/corpus.json`:
   - criar o `id` de cada dissertação (D001 a D059, na ordem do original);
   - transformar as palavras-chave (texto separado por vírgulas) em lista;
   - remover sobras da cópia do PDF. Caso já conhecido: o resumo do 48º item ("Embornal de saberes e fazeres") termina com "Palavras-chave: Referências C".
5. Verificações automáticas: avisar quando um resumo tiver "Palavras-chave", "Abstract" ou "Resumo" no meio do texto, quando for muito curto ou terminar sem ponto final. Só as dissertações marcadas precisam ser conferidas contra o PDF.
6. Montar `data/calibracao/corpus_calibracao.json` com 3 a 5 dissertações **de fora das 59** (ex.: de 2022), no mesmo formato. Se elas estiverem só em PDF, extrair o texto com PyMuPDF.

**Pronto quando:**

- [ ] As 59 dissertações estão no `corpus.json`, com `id`, e as marcadas pelas verificações foram conferidas contra o PDF.
- [ ] `unitarizar` roda nas 59 sem erro.
- [ ] O corpus de calibração existe.
- [ ] Os testes passam.

**Como testar sozinha:** com `corpus_exemplo.json`. Testes sugeridos:

- "Segundo Bardin (2016), a análise…" não quebra em duas frases.
- "Dr." e números como "2,5" não quebram frase.
- Os ids saem sequenciais (F1, F2, F3).
- Um JSON com campo faltando gera erro com o `id` da dissertação.

**Dificuldade:** fácil. Como as 59 já estão em JSON, esta parte ficou mais leve que as outras; ver a pergunta sobre o rebalanceamento na seção 7.

### Parte 2 — Base de conhecimento e busca

**Objetivo:** escrever a base de metodologias e, para cada dissertação, entregar as frases e os verbetes certos para o modelo.

**Arquivos:** `data/base_metodologia.json`, `src/indexar.py`, `src/recuperar.py`, `data/indices/` (gerado, fora do git), `tests/test_parte2_*.py`

**Entradas e saídas:** `list[DissertacaoUnitarizada]` + `list[Verbete]` → índice → `Contexto`

**Tarefas, em ordem:**

1. Escrever `data/base_metodologia.json` com os eixos e termos da seção 6.3 do planejamento: definição, sinais e sinônimos de cada termo. Pedir revisão da orientadora. **Ajustar só olhando dissertações de calibração.**
2. `carregar_base`: ler e conferir a base (eixo válido, `id` sem repetição).
3. `recuperar(..., tecnica="sem_rag")`: devolver todas as frases e nenhum verbete. É a linha de base.
4. `construir_indice`: gerar os embeddings com `multilingual-e5` (prefixo `passage:` nos textos, vetores normalizados) e montar um índice FAISS `IndexFlatIP` para frases e outro para verbetes. Salvar em `data/indices/`.
5. `recuperar(..., tecnica="denso")`: usar perguntas fixas, com prefixo `query:`. Exemplos: "procedimentos metodológicos, coleta de dados, participantes, análise dos dados" para metodologias; "objetivo e objeto de estudo da pesquisa" e o próprio título para temáticas. Depois buscar os verbetes mais parecidos com as frases de método encontradas.
6. `recuperar(..., tecnica="hibrido")`: acrescentar BM25 (sugestão: biblioteca `rank-bm25`, mais simples que o SQLite FTS5 do projeto de referência) e juntar as listas com RRF (k = 60).
7. Avaliar a busca na calibração: marcar à mão quais frases de cada resumo descrevem o método e medir o **recall@5**, isto é, quantas das frases certas aparecem entre as 5 primeiras.
8. (Opcional) `hibrido_rerank` com `bge-reranker-v2-m3`.

**Pronto quando:**

- [ ] As 3 técnicas obrigatórias funcionam.
- [ ] O índice é reconstruído com um comando (`python -m src.indexar`).
- [ ] O recall@5 das frases de método na calibração foi medido e registrado, com uma meta a combinar (sugestão: 80% ou mais).
- [ ] A base metodológica foi revisada.

**Como testar sozinha:** com `frases_exemplo.json` e `base_metodologia_exemplo.json`. Testes sugeridos:

- A frase "foram realizadas entrevistas semiestruturadas" traz o verbete de entrevista semiestruturada entre os 3 primeiros.
- `sem_rag` devolve todas as frases.
- Nenhum `Contexto` cita frase de outra dissertação.

**Dificuldade:** difícil. Mistura conteúdo (escrever a base) com a parte mais técnica (embeddings, índice, fusão).

### Parte 3 — Geração com LLM e validação

**Objetivo:** transformar dissertação + contexto numa `RespostaIA` válida, com evidências que existem de verdade no resumo.

**Arquivos:** `src/sugerir.py`, `src/validar.py`, `src/prompts/v1.txt` (e as versões seguintes), `tests/test_parte3_*.py`

**Entradas e saídas:** `DissertacaoUnitarizada` + `Contexto` + nome do modelo → `RespostaIA`

**Tarefas, em ordem:**

1. Instalar o Ollama e baixar um modelo pequeno para desenvolver (ex.: `qwen2.5:3b-instruct`, que roda sem placa de vídeo). Os modelos maiores rodam na máquina com a RTX 2060.
2. `montar_prompt`: escrever o prompt `v1` partindo do "prompt interpretativo" do projeto de referência (TECNICAS 3.8). Ele deve:
   - nomear a temática ou a metodologia e apontar a frase que a justifica;
   - proibir inventar dados;
   - responder "Não informado no resumo" quando o método não aparece;
   - seguir as regras do formulário: sempre **duas** temáticas e todas as metodologias.
3. Chamar o Ollama com `format` = JSON Schema (força a resposta a vir no formato combinado), `temperature=0`, `seed` fixa e `num_ctx=8192`.
4. Interpretar a saída: ler o JSON. Se vier quebrado, tentar mais uma vez; se falhar de novo, devolver `status="erro"` com a `saida_bruta` guardada. **Nunca travar o programa.**
5. `validar`: toda evidência citada tem que existir nas frases; se não existir, `status="sem_evidencia"`. Também remover metodologias repetidas e tratar temática vazia.
6. Testar modelos na calibração: quais cabem nos 6 GB da RTX 2060, quanto tempo leva cada dissertação e quantas respostas dão erro. Isso responde à decisão em aberto "quais modelos usar".
7. Ajustar o prompt **só com a calibração**, guardando cada versão (`v1`, `v2`…) num arquivo separado.

**Pronto quando:**

- [ ] Gera `RespostaIA` válida para todas as dissertações da calibração com pelo menos 2 modelos.
- [ ] Os testes com saídas ruins passam (JSON quebrado, frase inexistente, resposta vazia), sem nenhum travamento.
- [ ] A versão final do prompt está registrada.

**Como testar sozinha:**

- `montar_prompt` e `validar` são testados **sem Ollama**, com `contexto_exemplo.json`, `frases_exemplo.json` e as saídas de `saidas_llm/`.
- Só o teste de ponta a ponta precisa do Ollama ligado.

**Dificuldade:** difícil. Modelos pequenos erram o formato com frequência, e o prompt exige muitas idas e vindas.

### Parte 4 — Orquestração, configuração e Excel

**Objetivo:** ligar todas as partes num comando só, permitir trocar modelo e técnica sem mexer no código e gravar a planilha.

**Arquivos:** `src/pipeline.py`, `src/exportar.py`, `config.py` (a seção da Parte 4, mais a organização geral do arquivo), `src/mocks.py` (manutenção), `tests/test_parte4_*.py`, `tests/test_nao_le_analise_manual.py`, `requirements.txt`, seção "Instalação" do `README.md`

**Entradas e saídas:** `config.py` + linha de comando → chama as Partes 1, 2 e 3 → `data/sugestoes/<execução>/respostas.xlsx` e `respostas.json`

**Tarefas, em ordem:**

1. `pipeline.py` com modo mock, para rodar com dados de exemplo desde o primeiro dia: `python -m src.pipeline --mock`.
2. `exportar.py`: gerar a planilha com as abas `respostas` (6 colunas, na ordem exata), `detalhes` e `execucao` (seção 3.4).
3. Argumentos de linha de comando: `--modelo`, `--tecnica`, `--corpus` e `--todos`. O `--todos` roda todas as combinações de `MODELOS` × `TECNICAS`.
4. Uma pasta por execução, com nome seguro para o Windows. Não sobrescrever uma execução existente sem `--sobrescrever`.
5. Retomar execução interrompida: guardar cada resposta assim que ela fica pronta, para não refazer as 59 se faltar luz ou o programa fechar.
6. Mostrar progresso ("D017 de 59…"). Um erro numa dissertação não pode parar as outras.
7. Registrar a máquina (CPU, RAM, GPU) e as versões das bibliotecas na aba `execucao`.
8. `test_nao_le_analise_manual.py`, a **regra de ouro**:
   - (a) procurar o texto `analise_manual` nos arquivos das Partes 1 a 4;
   - (b) rodar o pipeline em modo mock e falhar se algum arquivo com esse nome for aberto.
9. Proteção contra "roubar" (C3): `CORPUS_ATIVO` começa em `calibracao`. Rodar nas 59 exige mudar isso de propósito.
10. Manter o `requirements.txt` e a seção de instalação do `README.md`.

**Pronto quando:**

- [ ] `--mock` gera a planilha correta.
- [ ] Com as partes reais, gera a planilha da calibração.
- [ ] `--todos` gera uma pasta por combinação.
- [ ] O teste da regra de ouro passa.
- [ ] Uma pessoa nova consegue instalar seguindo o README.

**Como testar sozinha:** tudo em modo mock, sem Ollama e sem índice. Por exemplo: conferir que a planilha tem 3 linhas, as 6 colunas na ordem, metodologias separadas por `"; "` e o nome do modelo preenchido.

**Dificuldade:** média. Não tem IA, mas é a parte que mais conversa com as outras.

### Parte 5 — Avaliação das respostas da IA

**Objetivo:** medir a qualidade das respostas da IA e comparar modelos e técnicas. **Agora**, sem as respostas humanas: com indicadores que não precisam de gabarito e com um gabarito pequeno feito pelo grupo para as dissertações de calibração. **Depois**, quando a professora enviar as respostas da análise manual: a comparação com elas, usando as mesmas funções já prontas e testadas.

**Arquivos:** `src/comparar.py`, `src/importar_respostas.py` (só depois), `data/calibracao/gabarito_calibracao.json`, `data/avaliacao/` (fora do git), `tests/test_parte5_*.py`

**Entradas e saídas:** pastas de `data/sugestoes/` (planilha, `respostas.json` e aba `execucao`) + base metodológica + gabarito → relatório e tabela comparativa

**Tarefas agora, em ordem:**

1. Ler as execuções: a planilha (abas `respostas`, `detalhes` e `execucao`) e o `respostas.json`.
2. **Indicadores sem gabarito**, para cada execução:
   - quantas respostas saíram com status "ok", "sem evidência", "não informado no resumo" e "erro";
   - tempo médio por dissertação;
   - quantos eixos de metodologia (abordagem, procedimento, coleta, análise) cada resposta cobre.
3. **Concordância entre execuções:** para a mesma dissertação, o quanto modelos e técnicas diferentes concordam entre si. Isso mostra se a resposta é estável ou muda muito de um modelo para outro.
4. **Funções de métrica**, testadas com dados de exemplo:
   - **Metodologias:** separar os termos (por "; ", "," e " e "), normalizar com os `sinonimos` da base metodológica (para que "entrevistas semi-estruturadas" e "entrevista semiestruturada" contem como o mesmo termo) e calcular **precisão**, **revocação** e **F1** por dissertação e por eixo. Exemplo: a referência diz "qualitativa, estudo de caso, entrevista" e a IA diz "qualitativa, entrevista, questionário". Precisão = 2/3 (do que a IA disse, quanto estava certo). Revocação = 2/3 (do que a referência diz, quanto a IA achou).
   - **Temáticas:** **similaridade de sentido** (embeddings `multilingual-e5`) entre o par de temáticas da IA e o par de referência, como **par sem ordem**: compara as duas combinações possíveis e fica com a melhor.
5. **Gabarito da calibração:** o grupo escreve a temática 1, a temática 2 e as metodologias das 3 a 5 dissertações de calibração (de fora das 59). A Parte 5 mede cada versão do prompt contra esse gabarito. Isso ajuda a Parte 3 a escolher o prompt **sem olhar as 59**.
6. Relatório por execução e `comparar_execucoes`: uma tabela com modelos × técnicas lado a lado, mais um gráfico de barras por indicador.

**Tarefas depois (quando a professora enviar as respostas da análise manual):**

7. `importar_respostas`: ler o arquivo recebido (formato a conhecer), anonimizar os analistas (A1 a A5) e ligar cada resposta ao `id` pelo **título colado** no Forms, ignorando maiúsculas, espaços e quebras de linha. Listar para conferência as respostas cujo título não for encontrado.
8. Rodar as métricas da tarefa 4 contra as respostas reais.
9. **Teto humano:** as mesmas métricas entre os 2 analistas de cada dissertação. Se a IA concorda com cada analista tanto quanto eles concordam entre si, ela está no nível humano.

**Pronto (agora) quando:**

- [ ] As métricas batem com os valores calculados à mão nos dados de exemplo.
- [ ] O relatório sem gabarito sai para todas as execuções reais.
- [ ] A comparação de versões do prompt contra o gabarito da calibração funciona.
- [ ] A tabela compara todas as execuções.

**Como testar sozinha:** com `respostas_ia_exemplo.json`, `respostas_ia_exemplo.xlsx`, `respostas_humanas_exemplo.json` (servindo de gabarito inventado) e `base_metodologia_exemplo.json`. Os valores esperados são calculados à mão antes e colocados nos testes.

**Dificuldade:** média a difícil. O código não é complexo, mas decidir **o que conta como acerto** exige cuidado. A classificação às cegas e o kappa/alfa (seção 8.2 do planejamento) dependem de codificação manual e ficam para uma etapa posterior.

---

## 5. Se alguém não puder programar

Algumas partes têm tarefas **sem código** que valem tanto quanto as outras. Uma pessoa que não programa pode assumir essas tarefas, em dupla com quem programa:

- escrever o conteúdo da base metodológica (Parte 2, tarefa 1);
- conferir contra o PDF as dissertações marcadas pelas verificações (Parte 1, tarefa 5);
- marcar à mão as frases de método da calibração, que servem de gabarito da busca (Parte 2, tarefa 7);
- calcular à mão os valores esperados dos testes da Parte 5;
- revisar pull requests, lendo o código e testando.

Se faltar quem programe uma parte, a melhor combinação para **uma pessoa ficar com duas partes** é esta:

| Combinação | Por que funciona | Paralelismo |
| --- | --- | --- |
| **Parte 1 + Parte 4** (recomendada) | A Parte 1 ficou leve com o JSON pronto, e a Parte 4 começa e funciona com mocks. As duas são "estrutura": arquivos, JSON, linha de comando | Mantido: as Partes 2, 3 e 5 continuam usando os mocks |
| **Parte 1 + Parte 5** | As duas lidam com dados em tabela (JSON, planilhas, pandas), e a Parte 5 também começa com mocks | Mantido |
| Evitar: Parte 2 + Parte 3 | São as duas mais difíceis e o coração do RAG. Juntas, viram o gargalo do projeto | Quebraria |

Na dupla, uma pessoa programa e a outra apoia nas tarefas sem código listadas acima, além de revisar e testar.

---

## 6. Integração no GitHub

### 6.1 Estrutura de pastas proposta (com o dono de cada item)

```
RAG-TCC/
├── config.py                      # compartilhado: cada parte edita só a sua seção (3.7)
├── requirements.txt               # Parte 4 (criado completo no esqueleto)
├── README.md                      # Parte 4 cuida da seção "Instalação"
├── data/
│   ├── brutos/dissertacoes.json   # original das 59 (não editar)
│   ├── corpus.json                # Parte 1 (gerado a partir do original)
│   ├── calibracao/                # Parte 1 (3 a 5 dissertações de fora das 59); o gabarito delas é da Parte 5
│   ├── base_metodologia.json      # Parte 2
│   ├── indices/                   # Parte 2 (gerado, fora do git)
│   ├── sugestoes/                 # Parte 4 (uma pasta por execução)
│   ├── avaliacao/                 # Parte 5 (fora do git)
│   └── analise_manual.json        # Parte 5, só depois (fora do git)
├── src/
│   ├── contratos.py               # esqueleto; mudanças só com aprovação das partes afetadas
│   ├── mocks.py                   # esqueleto; Parte 4 mantém
│   ├── preparar_dados.py          # Parte 1
│   ├── unitarizar.py              # Parte 1
│   ├── indexar.py                 # Parte 2
│   ├── recuperar.py               # Parte 2
│   ├── sugerir.py                 # Parte 3
│   ├── validar.py                 # Parte 3
│   ├── prompts/                   # Parte 3 (v1.txt, v2.txt…)
│   ├── pipeline.py                # Parte 4
│   ├── exportar.py                # Parte 4
│   ├── importar_respostas.py      # Parte 5, só depois
│   └── comparar.py                # Parte 5
├── tests/
│   ├── exemplos/                  # mocks (esqueleto; cada parte pode acrescentar os seus)
│   ├── test_parte1_*.py … test_parte5_*.py
│   └── test_nao_le_analise_manual.py   # Parte 4
├── notebooks/                     # cada um usa o prefixo da parte: parte2_testes_busca.ipynb
├── docs/
└── app/                           # sem uso nesta etapa
```

**Regra:** cada pessoa só altera os arquivos da sua parte. Se precisar de algo de outra parte, abre uma *issue* (um pedido registrado no GitHub) para o dono daquela parte.

### 6.2 Branches

- `main`: a versão que funciona. **Protegida:** ninguém envia direto para ela, só por pull request aprovado.
- Uma branch por parte: `parte-1`, `parte-2`, `parte-3`, `parte-4` e `parte-5`.
- A branch continua existindo depois de cada merge. Antes de começar uma tarefa nova, cada um traz as novidades da `main` para a sua branch.

### 6.3 Commits e pull requests

- **Mensagem de commit:** `parte-N: verbo no presente + o que mudou`. Exemplos:
  - `parte-1: adiciona divisão do resumo em frases`
  - `parte-3: trata JSON quebrado na saída do modelo`
- **Título do pull request:** `[Parte N] O que foi feito`. Exemplo: `[Parte 2] Busca densa com e5 e FAISS`.
- **Pull requests pequenos:** uma tarefa terminada vira um PR. Evite juntar tudo num PR gigante no final.
- **Checklist que todo PR deve ter na descrição:**
  - [ ] Os testes passam (`python -m pytest`).
  - [ ] Só alterei arquivos da minha parte.
  - [ ] Nada lê `analise_manual.json` (exceto na Parte 5).
  - [ ] Nada sensível no commit: respostas humanas, CSV do Forms ou nomes de analistas.
  - [ ] Como testar este PR: …
- **Revisão em rodízio:** a Parte 1 é revisada pela 2, a 2 pela 3, a 3 pela 4, a 4 pela 5 e a 5 pela 1. Mudança em `src/contratos.py` precisa da aprovação das partes afetadas.

### 6.4 Ordem de merge na `main`

1. **Esqueleto primeiro:** contratos, mocks, `config.py` com as seções, `requirements.txt`, `tests/exemplos/` e uma pasta e README curto por parte. Todos criam a sua branch **depois** disso.
2. **Depois, as partes, em qualquer ordem:** graças aos mocks, nenhuma parte trava a outra. Para as primeiras versões "de verdade", a ordem natural é **Parte 1 → 2 → 3 → 4 → 5**, porque cada uma substitui um mock na corrente.
3. **Por fim, a integração ponta a ponta** (6.5).

### 6.5 Passo final: integração ponta a ponta

| # | Passo | Comando (proposta) | Responsável |
| --- | --- | --- | --- |
| 1 | Gerar o `corpus.json` a partir do original e montar a calibração | `python -m src.preparar_dados` | Parte 1 |
| 2 | Construir o índice | `python -m src.indexar` | Parte 2 |
| 3 | Rodar na **calibração** com 1 modelo e conferir a planilha à mão | `python -m src.pipeline --modelo qwen2.5:7b-instruct --tecnica hibrido` | Parte 4 + grupo |
| 4 | **Fixar** prompt e base metodológica, e marcar a versão no git | `git tag v1-fixado` | Partes 2 e 3 |
| 5 | Mudar `CORPUS_ATIVO` para o corpus das 59 e rodar todas as combinações | `python -m src.pipeline --todos` | Parte 4 |
| 6 | Avaliar as execuções (indicadores sem gabarito e comparação entre modelos e técnicas) | `python -m src.comparar` | Parte 5 |
| 7 | **Depois:** importar as respostas enviadas pela professora e comparar com a IA | `python -m src.comparar --com-analise-manual` | Parte 5 |
| 8 | Conferência final | — | Grupo |

**Checklist da conferência final:**

- [ ] Cada planilha tem 59 linhas e as 6 colunas na ordem combinada.
- [ ] Nenhuma célula vazia sem um `status` explicando o motivo na aba `detalhes`.
- [ ] O teste da regra de ouro passou.
- [ ] O relatório da Parte 5 traz todas as execuções (o teto humano entra depois, com as respostas da professora).
- [ ] A aba `execucao` registra a máquina e a configuração de cada rodada.

### 6.6 Passo a passo de git para quem está começando

```bash
# uma vez só: baixar o repositório
git clone https://github.com/Bingueta/RAG-TCC.git
cd RAG-TCC
git checkout parte-1            # troque pelo número da sua parte

# antes de cada tarefa: trazer as novidades da main
git pull origin main

# depois de mudar arquivos
git status                      # ver o que mudou
git add src/unitarizar.py       # adicionar só os arquivos da sua parte
git commit -m "parte-1: adiciona divisão do resumo em frases"
git push origin parte-1

# no site do GitHub: "Compare & pull request" → base: main ← parte-1 → pedir revisão
```

---

## 7. Decisões em aberto desta divisão

- [ ] Formato do arquivo de respostas que a professora vai enviar (definir quando chegar)
- [ ] Quem escreve o gabarito das dissertações de calibração (sugestão: 2 membros, cada um sozinho, como na análise manual)
- [ ] FAISS ou ChromaDB. Recomendação: **FAISS**, já testado no projeto de referência e suficiente para alguns milhares de frases
- [ ] Biblioteca do BM25. Recomendação: `rank-bm25`, mais simples que o SQLite FTS5
- [ ] Lista final de modelos (depende do teste da Parte 3 na RTX 2060)
- [ ] Meta de recall@5 da busca (sugestão: 80%)
- [ ] Limiar de similaridade para considerar que uma temática "acertou" (Parte 5)
- [ ] Se as planilhas da IA (`data/sugestoes/`) vão para o GitHub. Recomendação: sim, porque são o registro da execução e não contêm respostas humanas
- [ ] Quais 3 a 5 dissertações de fora das 59 entram na calibração
- [ ] Quem assume cada parte
