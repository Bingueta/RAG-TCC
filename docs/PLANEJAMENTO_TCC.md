# Análise de Conteúdo Acadêmico Assistida por IA: Uma Abordagem com LLMs e RAG

**Arquivo de contexto e planejamento do desenvolvimento**
Graduação em Sistemas de Informação — Universidade Vale do Rio Doce (Univale)
Grupo: Franklyn Rodrigues dos Santos, Igor Coelho Brasil, Lucas Andrade Feres, Felipe Dias Ribeiro, Helber Fernandes Rodrigues
Orientadora convidada: Prof.ª Dr.ª Cristiane Mendes Netto
Atualizado em: 06/10/2026

Resumo curto do projeto: [CONTEXTO_DO_PROJETO.md](CONTEXTO_DO_PROJETO.md). Divisão do código em 5 partes: [divisao-tarefas.md](divisao-tarefas.md).

---

## 1. Resumo em uma frase

Construir uma ferramenta RAG, com a IA rodando no próprio computador, que **ajuda a fazer a análise de conteúdo** de resumos de dissertações: identificar as **duas temáticas principais** e as **metodologias**. A ferramenta roda em lote e gera uma planilha. Ela é avaliada de duas formas: comparando as respostas da **IA sozinha** com a **análise manual** que o grupo já fez, e comparando a análise manual com uma nova análise do grupo **feita com o apoio da ferramenta**.

## 2. Palavras que aparecem neste documento

| Termo | O que significa aqui |
| --- | --- |
| Análise de conteúdo | Ler um texto e identificar do que ele trata (temáticas) e como a pesquisa foi feita (metodologias). Base: Bardin (2016) |
| Análise manual | A análise que o grupo **já fez**, sem IA, das 59 dissertações |
| Análise com a ferramenta | A análise que o grupo **vai fazer** das mesmas 59, consultando as respostas da IA como apoio |
| LLM | Modelo de linguagem, o "cérebro" da IA (ex.: Qwen, Llama) |
| Ollama | Programa que roda o LLM no próprio computador, sem internet e sem pagar API |
| RAG | Técnica em que, antes de responder, o programa **busca os trechos certos do texto** e entrega ao LLM. Assim a IA responde com base no resumo, em vez de inventar |
| Corpus | O conjunto das 59 dissertações (título, resumo e palavras-chave) |
| JSON | Formato de arquivo de texto organizado em "fichas", com nome e valor para cada informação. Fácil de o programa ler (exemplo na seção 6.1) |
| Evidência | A frase do resumo que justifica uma temática ou uma metodologia |
| Embeddings e índice | Transformar cada frase em números para o programa achar rapidamente as frases parecidas com uma pergunta. O índice é como o índice remissivo de um livro |
| Prompt | As instruções escritas que o programa manda para o LLM |
| Calibração | Ajustar o prompt e a base de metodologias usando dissertações **de fora das 59** (as 20 de 2022), para não "roubar" |

## 3. Contexto

A análise de conteúdo de documentos acadêmicos (Bardin, 2016) exige tempo e esforço, e pessoas diferentes chegam a interpretações diferentes. LLMs podem apoiar essa tarefa, mas, usados sozinhos, inventam coisas (alucinam) e são inconsistentes. O RAG faz a IA responder com base no texto do resumo, o que reduz a invenção e mostra de onde veio cada resposta.

**O papel da ferramenta:** ela é um **apoio à análise de conteúdo**. Ela não substitui a pessoa: quem decide a resposta final é o analista.

**Formato (decidido):** a ferramenta é **automática**. Ela roda as dissertações em lote e grava uma planilha Excel. Não há chat nem tela nesta etapa (seção 7.1).

**Pergunta de pesquisa:** de que maneira a integração de LLMs com RAG pode auxiliar e qualificar a análise de conteúdo em dissertações acadêmicas quando comparada ao processo de análise puramente manual?

> A conferir: se este é o texto oficial da pergunta no projeto entregue à faculdade.

## 4. Como o trabalho acontece

| Etapa | Situação | O que é |
| --- | --- | --- |
| Análise manual | **Concluída** | 59 dissertações, cada uma analisada por 2 membros, sem IA e sem ver a resposta do outro. 118 análises, registradas no Google Forms |
| Construção da ferramenta | A fazer | O programa em lote que gera a planilha da IA ([divisao-tarefas.md](divisao-tarefas.md)) |
| Avaliação da IA sozinha | A fazer | Rodar a ferramenta com vários modelos e técnicas de RAG e avaliar as respostas. A comparação com a análise manual vem depois que a ferramenta estiver pronta, quando a professora enviar as respostas do grupo (8.1) |
| Análise com a ferramenta | A fazer | Os 5 membros analisam de novo as 59, consultando a planilha da IA como apoio (4.2) |
| Comparação | A fazer | Análise manual × análise com a ferramenta (8.2) |

### 4.1 A tarefa de análise

A análise manual usou um formulário com:

1. Identificação do analista
2. Dissertação avaliada (o analista **colava o título** da dissertação)
3. **Temática 1** — resposta aberta
4. **Temática 2** — resposta aberta
5. **Metodologias** — um único campo de resposta aberta, em que o analista escreve uma frase citando as metodologias da pesquisa (ex.: "pesquisa qualitativa, estudo de caso, entrevistas semiestruturadas, análise de conteúdo")

Regras: sempre **duas** temáticas (as duas principais, mesmo que o resumo trate de uma só ou de muitas). O analista só vê as respostas dos outros depois de enviar, para evitar viés.

A ferramenta produz respostas **nesse mesmo formato**: temática 1, temática 2 e metodologias.

### 4.2 Análise com a ferramenta: quem analisa o quê

Cada membro analisa, com a ferramenta, **dissertações que não analisou na análise manual**. Se a mesma pessoa refizer a mesma dissertação, ela lembra da própria resposta, e a comparação mede memória, não o efeito da IA.

- Com 5 membros e 2 analistas por dissertação na análise manual, sobram sempre 3 membros que ainda não viram cada dissertação; sorteiam-se 2 deles.
- A carga fica parecida com a da análise manual: cerca de 22–24 análises por membro.
- São **as mesmas 59 dissertações**; só muda quem analisa cada uma.
- Como a ferramenta é automática, o "apoio" é a **planilha da IA**: o analista lê o resumo, consulta as respostas da IA e as frases de evidência (aba `detalhes`) e decide a própria resposta.
- Manter as mesmas regras da análise manual (mesmos campos, sem ver a resposta dos outros).

### 4.3 O que registrar na análise com a ferramenta (proposta)

As respostas são registradas num **Google Forms**, como na análise manual, com estes campos extras:

- Horário de início e de fim (ou tempo gasto em minutos)
- Para cada campo: "Usei o que a IA indicou / Editei / Ignorei"
- Utilidade da ferramenta nesta dissertação (1 a 5)
- Observação livre (opcional): onde a IA ajudou ou atrapalhou

Se o tempo gasto na análise manual não foi registrado, a comparação de tempo fica apenas descritiva e entra como limitação.

## 5. Escopo

**Dentro do escopo**

- Entrada: apenas **título, resumo e palavras-chave** das 59 dissertações (2023–2025).
- Identificar temática 1, temática 2 e metodologias, com a frase do resumo que justifica cada uma.
- LLM executado **localmente** via Ollama, com modelo e técnica de RAG trocáveis por configuração.
- Saída em planilha Excel.

**Fora do escopo**

- Texto completo das dissertações.
- Chat e tela de uso (podem vir depois, se o grupo quiser).
- Treino ou fine-tuning de modelos.

## 6. Dados

### 6.1 Corpus — `data/corpus.json`

**Origem:** os resumos estavam num PDF, uma dissertação por página. O grupo passou as 59 para JSON, em `data/brutos/dissertacoes.json`. Esse arquivo é o **original** e não é editado. Ele tem só três campos, e as palavras-chave vêm num texto único separado por vírgulas:

```json
{
  "titulo": "...",
  "resumo": "...",
  "palavras_chave": "Palavra um, Palavra dois, Palavra três"
}
```

Um script lê o original e gera o `data/corpus.json`. Nele, cada dissertação ganha um `id` (D001 a D059, na ordem do original) e as palavras-chave viram uma lista:

```json
{
  "id": "D001",
  "titulo": "...",
  "resumo": "...",
  "palavras_chave": ["Palavra um", "Palavra dois", "Palavra três"]
}
```

O original não tem o ano. O campo `ano` fica opcional.

Observações sobre o original:

- 59 dissertações, sem título repetido e sem campo vazio.
- Os resumos têm entre 1.138 e 3.585 caracteres (cerca de 5 a 18 frases) e de 3 a 7 palavras-chave.
- Alguns títulos estão todos em maiúsculas ou com quebra de linha no meio (itens 6, 48 e 52). Como o Forms identificava a dissertação pelo **título colado**, a ligação entre as respostas e o `id` precisa ignorar maiúsculas, espaços e quebras de linha.
- Dois resumos terminavam sem ponto final (itens 57 e 59); o texto estava completo e o ponto foi acrescentado no original.
- Aspas e apóstrofos curvos viraram caracteres invisíveis na cópia do PDF (11 casos, ex.: "Olhos D’água"); a preparação os conserta.
- Uma busca simples por termos de método (qualitativa, quantitativa, entrevista, questionário, estudo de caso, bibliográfica, documental) encontrou algum desses termos em 48 dos 59 resumos. Os outros 11 merecem atenção, porque podem cair em "não informado no resumo" ou descrever o método com outras palavras.

Não incluir autor nem orientador. Não editar o `corpus.json` depois que a análise com a ferramenta começar.

### 6.2 Respostas da análise manual — `data/analise_manual.json`

**Só depois que a ferramenta estiver pronta.** A professora vai enviar ao grupo as respostas da análise manual. Até lá, o trabalho usa só as respostas da IA. Quando o arquivo chegar, ele é padronizado assim:

```json
{
  "dissertacao_id": "D001",
  "analista": "A3",
  "tematica_1": "...",
  "tematica_2": "...",
  "metodologias": "..."
}
```

O `dissertacao_id` é encontrado comparando o título colado no Forms com os títulos do `corpus.json`. Respostas cujo título não for encontrado são listadas para conferência manual.

Anonimizar os analistas (A1–A5). Este arquivo **não vai para o GitHub** (o repositório é público).

**Regra de ouro: a ferramenta nunca lê as respostas da análise manual.** Elas servem só para a avaliação e a comparação. Se a ferramenta usasse essas respostas, ela estaria copiando o grupo, e a comparação não mediria nada.

### 6.3 Base de conhecimento metodológico — `data/base_metodologia.json`

É o que o RAG consulta para nomear as metodologias de forma fundamentada. Um glossário curto, escrito pelo grupo, com a definição, os sinais típicos e os sinônimos de cada termo, em JSON (formato na seção 3.3 de [divisao-tarefas.md](divisao-tarefas.md)). Eixos e termos iniciais:

- **Natureza:** básica, aplicada
- **Objetivos:** exploratória, descritiva, explicativa
- **Abordagem:** qualitativa, quantitativa, mista
- **Procedimentos:** bibliográfica, documental, estudo de caso, survey/levantamento, pesquisa-ação, etnográfica, experimental
- **Coleta:** entrevista (estruturada, semiestruturada, aberta), questionário, grupo focal, observação, análise documental, dados secundários
- **Análise:** análise de conteúdo, análise do discurso, análise temática, estatística descritiva/inferencial

Exemplo de verbete: *"Estudo de caso — investigação aprofundada de um ou poucos casos (uma instituição, um grupo, um município). Sinais no resumo: 'o caso de…', 'em uma escola de…', 'na cidade de…'."*

A mesma base serve para a avaliação: os sinônimos permitem reconhecer que "entrevistas semi-estruturadas" e "entrevista semiestruturada" são o mesmo termo.

## 7. A ferramenta

### 7.1 Formato: automático

O programa passa pelas dissertações de uma vez e grava uma planilha Excel por execução (combinação de modelo, técnica de RAG e versão do prompt):

- aba `respostas`: `id`, `titulo`, `tematica_1`, `tematica_2`, `metodologias` (todas numa coluna, separadas por "; ") e `modelo`;
- aba `detalhes`: as frases de evidência de cada resposta, o status ("ok", "sem evidência", "não informado no resumo", "erro"), a técnica e a versão do prompt;
- aba `execucao`: máquina, configuração e data da rodada.

O formato exato está na seção 3.4 de [divisao-tarefas.md](divisao-tarefas.md).

### 7.2 Arquitetura

```
data/brutos/dissertacoes.json ─► 1. Preparação (id, limpeza) ─► 2. Unitarização (frases) ─┐
                                                                                          ├─► 3. Embeddings + índice
data/base_metodologia.json ───────────────────────────────────────────────────────────────┘
                                   │
               4. Recuperação (busca as frases e os verbetes certos)
                                   │
               5. LLM local (Ollama) → resposta em JSON
                                   │
               6. Validação da evidência
                                   │
               7. Planilha Excel (data/sugestoes/)
```

### 7.3 Etapas

1. **Preparação:** gerar o `id`, transformar as palavras-chave em lista e padronizar acentos (Unicode), espaços e quebras de linha.
2. **Unitarização:** dividir cada resumo em frases, que correspondem às unidades de registro de Bardin. Cada frase recebe um código (F1, F2…), para ser citada como evidência.
3. **Embeddings e índice:** transformar em números as frases do corpus e os verbetes da base metodológica. Sugestão: `intfloat/multilingual-e5-base` (ou `-small`, se ficar lento; exige os prefixos `query:` e `passage:`), vetores normalizados e similaridade de cosseno, calculada com NumPy (o FAISS dá o mesmo resultado; ver PROGRESSO.md).
4. **Recuperação:**
    - *Metodologias:* achar as frases do resumo que descrevem o que foi feito (coleta, participantes, análise) e os verbetes da base metodológica mais parecidos com elas.
    - *Temáticas:* achar as frases centrais do resumo (objeto e objetivo) e, opcionalmente, títulos de dissertações parecidas do próprio corpus, para manter nomes de temas consistentes. Só títulos e resumos, nunca respostas da análise manual.
    - Técnicas comparadas: sem RAG (linha de base), busca densa, busca híbrida e, se sobrar tempo, híbrida com reranker (seção 2 de [divisao-tarefas.md](divisao-tarefas.md)).
5. **Geração:** o LLM recebe título, palavras-chave, frases e verbetes recuperados e devolve a resposta num formato fixo (JSON). Temperatura 0 e `seed` fixa, para a mesma pergunta dar sempre a mesma resposta.
6. **Validação:** cada evidência citada tem que existir no resumo. Se não existir, a resposta é marcada como "sem evidência" em vez de ser mostrada como certa. Se o resumo não disser o método, a resposta é "não informado no resumo".
7. **Planilha:** ver 7.1.

### 7.4 Exemplo de resposta da IA

Cada metodologia vem separada, com a própria evidência. O formato exato (as "fichas" `RespostaIA` e `Campo`) está na seção 3.1 de [divisao-tarefas.md](divisao-tarefas.md).

```json
{
  "dissertacao_id": "D001",
  "tematica_1": {"texto": "Saúde do idoso", "evidencia": ["F2"], "status": "ok"},
  "tematica_2": {"texto": "Adesão ao tratamento medicamentoso", "evidencia": ["F1", "F3"], "status": "ok"},
  "metodologias": [
    {"texto": "Pesquisa qualitativa", "evidencia": ["F4"], "status": "ok"},
    {"texto": "Estudo de caso", "evidencia": ["F4"], "status": "ok"},
    {"texto": "Entrevista semiestruturada", "evidencia": ["F5"], "status": "ok"},
    {"texto": "Análise de conteúdo", "evidencia": ["F5"], "status": "ok"}
  ],
  "modelo": "qwen2.5:7b-instruct",
  "versao_prompt": "v1",
  "tecnica": "hibrido"
}
```

### 7.5 Tecnologias

- Python 3.11
- Ollama (LLM local), com 2–3 modelos testados (ex.: `qwen2.5:7b-instruct`, `llama3.1:8b`, `qwen2.5:3b-instruct`)
- Máquina prevista para rodar o modelo: i5 de 10ª geração, 16 GB de RAM, RTX 2060 (6 GB). Modelos de 7B–8B compactados devem caber na placa; o `gemma2:9b` fica no limite. Confirmar em teste e registrar a máquina usada
- sentence-transformers (embeddings)
- NumPy (busca por sentido; sem FAISS nem ChromaDB) e `rank-bm25` (busca por palavra exata)
- spaCy `pt_core_news_sm` (divisão em frases)
- pandas e openpyxl (planilha Excel)
- scikit-learn e `krippendorff` (avaliação e comparação)
- pytest (testes automáticos)
- PyMuPDF (só se for preciso extrair do PDF as dissertações de calibração)
- Git/GitHub (repositório público, para a orientadora ter acesso)

### 7.6 Estrutura do repositório

A estrutura completa, com o dono de cada arquivo, está na seção 6.1 de [divisao-tarefas.md](divisao-tarefas.md). Resumo:

```
RAG-TCC/
├── data/
│   ├── brutos/dissertacoes.json  # original das 59; não editar
│   ├── corpus.json               # gerado a partir do original
│   ├── calibracao/               # 20 dissertações de 2022, de fora das 59
│   ├── base_metodologia.json
│   ├── indices/                  # gerado, fora do git
│   ├── sugestoes/                # planilhas da IA, uma pasta por execução
│   ├── avaliacao/                # relatórios, fora do git
│   └── analise_manual.json       # fora do git; nunca lido pela ferramenta
├── src/                          # código, um arquivo por etapa (ver divisao-tarefas.md)
├── tests/                        # testes automáticos e dados de exemplo
├── docs/
├── notebooks/
├── config.py                     # todos os parâmetros, com justificativa
└── requirements.txt
```

A pasta `app/` fica sem uso enquanto não houver tela.

### 7.7 Ajustar a ferramenta sem "roubar"

- Ajustar os prompts e a base metodológica só com as **20 dissertações de 2022**, de fora das 59, guardadas em `data/calibracao/`. Se o grupo ajustasse a ferramenta olhando as 59, ela ficaria boa justamente nelas, e a comparação ficaria injusta.
- Medir os modelos e as técnicas nas 59 é permitido. **Ajustar o prompt olhando a nota nas 59 não é.**
- Antes de rodar nas 59, **fixar** prompt e base metodológica (com uma marca de versão no git). Todos os modelos e técnicas rodam com a mesma versão.
- A versão usada pelos analistas na análise com a ferramenta também fica fixa do começo ao fim.

## 8. Como avaliar e comparar (proposta, a validar pelo grupo)

As respostas são texto livre, então não dá para comparar só com "igual/diferente". Temática 1 e temática 2 são comparadas **como par** (a ordem não importa).

### 8.1 IA sozinha × análise manual

Feita automaticamente pelo programa, para cada execução (modelo × técnica). **Enquanto as respostas da análise manual não chegam**, o programa já mede indicadores que não precisam delas (respostas válidas, evidências, "não informado", tempo, concordância entre modelos e técnicas) e compara as versões do prompt com um gabarito escrito pelo grupo para as dissertações de calibração. Quando a professora enviar as respostas, entram as medidas abaixo:

| O que medir | Como |
| --- | --- |
| Acerto nas **metodologias** | Separar cada resposta em termos, padronizar com os sinônimos da base metodológica e calcular **precisão** (do que a IA disse, quanto estava certo), **revocação** (do que a pessoa disse, quanto a IA achou) e **F1** (as duas juntas), por dissertação e por eixo |
| Acerto nas **temáticas** | **Similaridade de sentido** (embeddings) entre o par de temáticas da IA e o par da pessoa; contar como acerto acima de um limiar |
| **Teto humano** | As mesmas medidas entre os 2 analistas de cada dissertação. Se a IA concorda com cada analista tanto quanto eles concordam entre si, ela está no nível humano |
| Impacto do **modelo** e da **técnica de RAG** | Tabela com todas as execuções lado a lado, incluindo a linha de base sem RAG |

### 8.2 Análise manual × análise com a ferramenta

1. **Classificação às cegas (principal).** Juntar todas as respostas (manuais e com a ferramenta), embaralhadas e **sem indicar de onde vieram**. O grupo agrupa as temáticas em categorias e separa cada resposta de metodologias nos eixos da seção 6.3. Com isso as respostas ficam comparáveis.
2. **Similaridade de sentido.** Medir, com embeddings, o quanto duas respostas dizem a mesma coisa (ex.: "saúde da pessoa idosa" ≈ "saúde do idoso"). Serve de apoio e de conferência da forma 1.
3. **Nota de qualidade às cegas.** Um avaliador lê o resumo e dá nota de 1 a 5 para cada resposta, sem saber de onde ela veio: a temática representa o resumo? As metodologias estão corretas e completas?

| Pergunta | Como medir |
| --- | --- |
| Com a IA, os analistas **concordam mais** entre si? | Concordância entre os 2 analistas de cada dissertação, na análise manual e na análise com a ferramenta (alfa de Krippendorff sobre as categorias; similaridade média) |
| Com a IA, as respostas ficam **melhores**? | Notas da avaliação às cegas: manual × com a ferramenta |
| As metodologias ficam mais **completas**? | Quantos eixos (abordagem, procedimento, coleta, análise) cada resposta cobre |
| A IA **economiza tempo**? | Tempo registrado na análise com a ferramenta (e na manual, se existir) |
| As pessoas só **copiam** a IA? | Similaridade entre a resposta final e o que a IA indicou; campo "usei / editei / ignorei" |
| Onde a IA **erra** e mesmo assim é aceita? | Casos em que a resposta da IA recebeu nota baixa e o analista usou sem editar |

**Análise qualitativa:** para as dissertações em que o resultado manual e o com a ferramenta divergem mais, descrever por quê (resumo ambíguo, IA influenciou, erro humano, erro da IA).

**Estatística:** com 59 dissertações, usar estatística descritiva e testes pareados não paramétricos (Wilcoxon) por dissertação. Deixar claro que o estudo é exploratório.

## 9. Divisão do trabalho

O código é dividido em **5 partes**, uma por pessoa, que podem ser feitas ao mesmo tempo. Os detalhes (contratos, dados de exemplo, tarefas, critérios de pronto, fluxo de git) estão em [divisao-tarefas.md](divisao-tarefas.md).

| Parte | O que inclui | Responsável |
| --- | --- | --- |
| 1 — Dados e unitarização | `corpus.json` a partir do original, limpeza, frases numeradas, calibração | a definir |
| 2 — Base de conhecimento e busca | Base metodológica, embeddings, índice, técnicas de RAG | a definir |
| 3 — Geração com LLM e validação | Prompt, Ollama, formato da resposta, validação, testes de modelos | a definir |
| 4 — Orquestração, configuração e Excel | Pipeline, troca de modelo e técnica, planilha, teste da regra de ouro | a definir |
| 5 — Avaliação | Métricas da seção 8.1 e tabela comparativa | a definir |

A análise com a ferramenta, a classificação às cegas e a escrita do TCC são feitas por **todos** e ficam fora dessa divisão de código.

Rotina sugerida: reunião curta semanal, quadro de tarefas (GitHub Projects) e pull requests revisados por outro membro.

## 10. Ordem das etapas

1. Preparar o `corpus.json` a partir do original; montar a calibração; base metodológica v1
2. Construir as 5 partes em paralelo, usando dados de exemplo
3. Juntar as partes e rodar na calibração; ajustar prompt e base só com ela
4. **Fixar** prompt e base metodológica
5. Rodar todas as combinações de modelo × técnica nas 59 e avaliar com os indicadores sem gabarito
6. Receber da professora as respostas da análise manual e comparar com a IA sozinha (8.1)
7. **Análise com a ferramenta**: cada membro analisa suas ~23 dissertações, consultando a planilha da IA
8. Classificação às cegas, notas de qualidade, comparação (8.2)
9. Escrita de resultados e discussão
10. Revisão final e apresentação

## 11. Riscos

| Risco | Como reduzir |
| --- | --- |
| Pessoa lembra da própria resposta manual | Cada membro analisa com a ferramenta resumos que não analisou antes (4.2) |
| Analistas copiam a IA sem pensar | Mostrar sempre a evidência; medir "usei/editei/ignorei" e a similaridade com o que a IA indicou |
| Respostas abertas difíceis de comparar | Precisão/revocação nas metodologias, similaridade nas temáticas, classificação às cegas e nota de qualidade (seção 8) |
| Resumo não informa o método | Resposta "não informado no resumo" |
| Modelo local fraco ou lento | Testar 2–3 modelos na máquina prevista |
| Ferramenta ajustada com as respostas manuais ou com as 59 | A ferramenta nunca lê `analise_manual.json`; ajustar só com a calibração (7.7) |
| Título colado no Forms diferente do título no JSON | Comparar títulos ignorando maiúsculas, espaços e quebras; listar para conferência os que não forem encontrados |
| Erro ao passar o PDF para o JSON (texto cortado, sobras) | Verificações automáticas na preparação; conferir contra o PDF as dissertações marcadas |
| Dado sensível no GitHub (repositório público) | `.gitignore` bloqueia `analise_manual.json`, CSVs e relatórios; analistas sempre anonimizados; nenhum dado de servidor ou hospedagem nos arquivos |
| Tempo da análise manual não registrado | Comparação de tempo descritiva; citar como limitação |
| Ferramenta atrasar e empurrar a análise, a comparação e a escrita | Priorizar a ferramenta e a avaliação da IA sozinha; técnicas extras (reranker) só se sobrar tempo |

## 12. Decisões em aberto

- [ ] Confirmar se a pergunta de pesquisa da seção 3 é o texto oficial do projeto
- [ ] Qual execução (modelo × técnica) os analistas vão consultar na análise com a ferramenta. Atenção: escolher "a que mais concordou com a análise manual" pode empurrar a análise com a ferramenta na direção da manual; discutir no grupo
- [ ] Formato do arquivo com as respostas da análise manual que a professora vai enviar
- [ ] Se o tempo da análise manual foi registrado (mesmo que aproximado)
- [ ] Quem do grupo faz a classificação às cegas e a nota de qualidade
- [ ] Quais modelos do Ollama cabem na máquina prevista (teste)
- [ ] As demais decisões técnicas da seção 7 de [divisao-tarefas.md](divisao-tarefas.md)
- [ ] Responsáveis por cada parte
