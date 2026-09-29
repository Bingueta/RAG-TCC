# Análise de Conteúdo Acadêmico Assistida por IA: Uma Abordagem com LLMs e RAG

**Arquivo de contexto e planejamento do desenvolvimento**
Graduação em Sistemas de Informação — Universidade Vale do Rio Doce (Univale)
Grupo: Franklyn Rodrigues dos Santos, Igor Coelho Brasil, Lucas Andrade Feres, Felipe Dias Ribeiro, Helber Fernandes Rodrigues
Orientadora convidada: Prof.ª Dr.ª Cristiane Mendes Netto
Atualizado em: 29/09/2026

---

## 1. Resumo em uma frase

Construir uma ferramenta RAG, com a IA rodando no próprio computador, que **ajuda a fazer a análise de conteúdo** de resumos de dissertações: identificar as **duas temáticas principais** e as **metodologias**. No final, o grupo compara o resultado obtido com a ajuda da ferramenta com a **análise manual** que já fez, para saber se com a IA ficou melhor.

## 2. Palavras que aparecem neste documento

| Termo | O que significa aqui |
| --- | --- |
| Análise de conteúdo | Ler um texto e identificar do que ele trata (temáticas) e como a pesquisa foi feita (metodologias). Base: Bardin (2016) |
| Análise manual | A análise que o grupo **já fez**, sem IA, das 59 dissertações |
| Análise com a ferramenta | A análise que o grupo **vai fazer**, usando a ferramenta como apoio |
| LLM | Modelo de linguagem, o "cérebro" da IA (ex.: Qwen, Llama) |
| Ollama | Programa que roda o LLM no próprio computador, sem internet e sem pagar API |
| RAG | Técnica em que, antes de responder, o programa **busca os trechos certos do texto** e entrega ao LLM. Assim a IA responde com base no resumo, em vez de inventar |
| Corpus | O conjunto das 59 dissertações (título, resumo e palavras-chave) |
| JSON | Formato de arquivo de texto organizado em "fichas", com nome e valor para cada informação. Fácil de o programa ler (exemplo na seção 6.1) |
| Evidência | A frase do resumo que justifica uma temática ou as metodologias |
| Embeddings e índice | Transformar cada frase em números para o programa achar rapidamente as frases parecidas com uma pergunta. O índice é como o índice remissivo de um livro |
| Prompt | As instruções escritas que o programa manda para o LLM |

## 3. Contexto

A análise de conteúdo de documentos acadêmicos (Bardin, 2016) exige tempo e esforço, e pessoas diferentes chegam a interpretações diferentes. LLMs podem apoiar essa tarefa, mas, usados sozinhos, inventam coisas (alucinam) e são inconsistentes. O RAG faz a IA responder com base no texto do resumo, o que reduz a invenção e mostra de onde veio cada resposta.

**O papel da ferramenta:** ela é só um **apoio à análise de conteúdo**. Ela não substitui a pessoa: quem decide a resposta final é o analista. O **formato** da ferramenta (chat, sugestões ou geração automática) **ainda não foi decidido** (seção 7.1).

**Pergunta de pesquisa:** de que maneira a integração de LLMs com RAG pode auxiliar e qualificar a análise de conteúdo em dissertações acadêmicas quando comparada ao processo de análise puramente manual?

> A conferir: se este é o texto oficial da pergunta no projeto entregue à faculdade.

## 4. Como o trabalho acontece

| Etapa | Situação | O que é |
| --- | --- | --- |
| Análise manual | **Concluída** | 59 dissertações, cada uma analisada por 2 membros, sem IA e sem ver a resposta do outro. 118 análises, registradas no Google Forms. Serviu para identificar temáticas e metodologias |
| Construção da ferramenta | A fazer | Construir a ferramenta RAG |
| Análise com a ferramenta | A fazer | Os 5 membros usam a ferramenta para analisar resumos |
| Comparação | A fazer | Resultado com a ferramenta × resultado da análise manual (seção 8) |

### 4.1 A tarefa de análise

A análise manual usou um formulário com:

1. Identificação do analista
2. Dissertação avaliada
3. **Temática 1** — resposta aberta
4. **Temática 2** — resposta aberta
5. **Metodologias** — um único campo de resposta aberta, em que o analista escreve uma frase citando as metodologias da pesquisa (ex.: "pesquisa qualitativa, estudo de caso, entrevistas semiestruturadas, análise de conteúdo")

Regras: sempre **duas** temáticas (as duas principais, mesmo que o resumo trate de uma só ou de muitas). O analista só vê as respostas dos outros depois de enviar, para evitar viés.

Para a comparação ser justa, a análise com a ferramenta deve produzir respostas **nesse mesmo formato**: temática 1, temática 2 e metodologias em texto livre.

### 4.2 Quem analisa o quê com a ferramenta

Cada membro usa a ferramenta com **resumos diferentes dos que analisou na análise manual**. Se a mesma pessoa refizer a mesma dissertação, ela lembra da própria resposta, e a comparação mede memória, não o efeito da IA.

- Com 5 membros e 2 analistas por dissertação na análise manual, sobram sempre 3 membros que ainda não viram cada dissertação; sorteiam-se 2 deles.
- A carga fica parecida com a da análise manual: cerca de 22–24 análises por membro.
- Manter as mesmas regras da análise manual (mesmos campos, sem ver a resposta dos outros).
- São **as mesmas 59 dissertações** da análise manual; só muda quem analisa cada uma.

### 4.3 O que registrar na análise com a ferramenta (proposta)

- Horário de início e de fim (ou tempo gasto em minutos)
- Para cada campo: "Usei o que a IA indicou / Editei / Ignorei"
- Utilidade da ferramenta nesta dissertação (1 a 5)
- Observação livre (opcional): onde a IA ajudou ou atrapalhou

O jeito de registrar (Google Forms ou dentro da própria ferramenta) depende do formato escolhido. Se o tempo gasto na análise manual não foi registrado, a comparação de tempo fica apenas descritiva e entra como limitação.

## 5. Escopo

**Dentro do escopo**

- Entrada: apenas **título, resumo e palavras-chave** das 59 dissertações (2023–2025).
- Ajudar a identificar temática 1, temática 2 e metodologias, sempre mostrando a frase do resumo que justifica cada uma.
- LLM executado **localmente** via Ollama.
- Uma forma simples de os membros usarem a ferramenta (formato a decidir, seção 7.1).

**Fora do escopo**

- Texto completo das dissertações.
- Treino ou fine-tuning de modelos.

## 6. Dados

Nenhum destes arquivos existe ainda. Eles são os primeiros a serem criados.

### 6.1 Corpus — `data/corpus.json`

**Origem:** hoje os resumos estão num PDF, com uma dissertação por página (título, resumo e palavras-chave). Um script extrai o texto do PDF e gera o `corpus.json`; depois uma pessoa confere cada dissertação contra o PDF.

Cada dissertação vira uma "ficha" assim:

```json
{
  "id": "D001",
  "ano": 2024,
  "titulo": "...",
  "resumo": "...",
  "palavras_chave": ["...", "..."]
}
```

Não incluir autor nem orientador. Não editar depois que a análise com a ferramenta começar.

### 6.2 Respostas da análise manual — `data/analise_manual.json`

Exportar o Forms (Planilhas Google → Arquivo → Download → CSV) e padronizar:

```json
{
  "id": "D001",
  "analista": "A3",
  "tematica_1": "...",
  "tematica_2": "...",
  "metodologias": "..."
}
```

Anonimizar os analistas (A1–A5). Este arquivo **não vai para o GitHub** (o repositório é público).

**Regra de ouro: a ferramenta nunca lê as respostas da análise manual.** Elas servem só para a comparação no final. Se a ferramenta usasse essas respostas, ela estaria copiando o grupo, e a comparação não mediria nada.

### 6.3 Base de conhecimento metodológico — `data/base_metodologia.md`

É o que o RAG consulta para nomear as metodologias de forma fundamentada. Um glossário curto, escrito pelo grupo, com a definição e os sinais típicos de cada termo:

- **Natureza:** básica, aplicada
- **Objetivos:** exploratória, descritiva, explicativa
- **Abordagem:** qualitativa, quantitativa, mista
- **Procedimentos:** bibliográfica, documental, estudo de caso, survey/levantamento, pesquisa-ação, etnográfica, experimental
- **Coleta:** entrevista (estruturada, semiestruturada, aberta), questionário, grupo focal, observação, análise documental, dados secundários
- **Análise:** análise de conteúdo, análise do discurso, análise temática, estatística descritiva/inferencial

Exemplo de verbete: *"Estudo de caso — investigação aprofundada de um ou poucos casos (uma instituição, um grupo, um município). Sinais no resumo: 'o caso de…', 'em uma escola de…', 'na cidade de…'."*

## 7. A ferramenta

### 7.1 Formato (a decidir)

| Formato | Como funciona na prática | Bom quando |
| --- | --- | --- |
| **Chat** | A pessoa pergunta "quais as metodologias da D012?" e a IA responde | A pessoa quer tirar dúvidas específicas sobre um resumo |
| **Sugestões** | A pessoa abre uma dissertação e já aparecem temática 1, temática 2 e metodologias sugeridas, com a frase do resumo que justifica cada uma destacada | A pessoa vai fazer a análise e quer um ponto de partida |
| **Automático** | O programa passa pelas dissertações de uma vez e gera uma planilha com tudo | O grupo quer o resultado pronto para revisar |

Os formatos podem ser combinados (ex.: gerar tudo automaticamente e mostrar numa tela de sugestões). A base técnica (etapas 1 a 6 abaixo) é **a mesma** nos três formatos; só muda a última etapa. Por isso o grupo pode começar a construir a base antes de decidir o formato.

### 7.2 Arquitetura

```
corpus.json ─► 1. Pré-processamento ─► 2. Unitarização (frases) ─┐
                                                                  ├─► 3. Embeddings + índice
base_metodologia.md ──────────────────────────────────────────────┘
                                   │
               4. Recuperação (busca as frases certas)
                                   │
               5. LLM local (Ollama) → resposta em JSON
                                   │
               6. Validação da evidência
                                   │
               7. Forma de uso (chat, sugestões ou automático)
```

### 7.3 Etapas

1. **Pré-processamento:** padronizar acentos (Unicode), espaços e quebras de linha.
2. **Unitarização:** dividir cada resumo em frases, que correspondem às unidades de registro de Bardin. Cada frase recebe um código (F1, F2…), para ser citada como evidência.
3. **Embeddings e índice:** transformar em números as frases do corpus e os verbetes da base metodológica. Sugestão: `intfloat/multilingual-e5-base` (ou `-small`, se ficar lento; exige os prefixos `query:` e `passage:`), vetores normalizados e similaridade de cosseno, em FAISS ou ChromaDB.
4. **Recuperação:**
    - *Metodologias:* achar as frases do resumo que descrevem o que foi feito (coleta, participantes, análise) e os verbetes da base metodológica mais parecidos com elas.
    - *Temáticas:* achar as frases centrais do resumo (objeto e objetivo) e, opcionalmente, títulos de dissertações parecidas do próprio corpus, para manter nomes de temas consistentes. Só títulos e resumos, nunca respostas da análise manual.
5. **Geração:** o LLM recebe título, palavras-chave, frases e verbetes recuperados e devolve a resposta num formato fixo (JSON). Temperatura 0 e `seed` fixa, para a mesma pergunta dar sempre a mesma resposta.
6. **Validação:** cada evidência citada tem que existir no resumo. Se não existir, a resposta é marcada como "sem evidência" em vez de ser mostrada como certa. Se o resumo não disser o método, a resposta é "não informado no resumo".
7. **Forma de uso:** ver 7.1.

### 7.4 Exemplo de resposta da IA

```json
{
  "id": "D001",
  "tematica_1": {"sugestao": "Saúde do idoso", "evidencia": ["F2"]},
  "tematica_2": {"sugestao": "Adesão ao tratamento medicamentoso", "evidencia": ["F1", "F3"]},
  "metodologias": {
    "sugestao": "Pesquisa qualitativa, estudo de caso, com entrevistas semiestruturadas e análise de conteúdo",
    "evidencia": ["F4", "F5"],
    "termos": {"abordagem": "qualitativa", "procedimento": "estudo de caso",
               "coleta": "entrevista semiestruturada", "analise": "análise de conteúdo"}
  },
  "frases": {"F1": "...", "F2": "...", "F3": "...", "F4": "...", "F5": "..."},
  "modelo": "qwen2.5:7b-instruct",
  "versao_prompt": "v3"
}
```

### 7.5 Tecnologias

- Python 3.11
- Ollama (LLM local), com 2–3 modelos testados (ex.: `qwen2.5:7b-instruct`, `llama3.1:8b`, `gemma2:9b`)
- Máquina prevista para rodar o modelo: i5 de 10ª geração, 16 GB de RAM, RTX 2060 (6 GB). Modelos de 7B–8B compactados devem caber na placa; o `gemma2:9b` fica no limite. Confirmar em teste e registrar a máquina usada
- sentence-transformers (embeddings)
- FAISS ou ChromaDB
- spaCy `pt_core_news_sm` (divisão em frases)
- PyMuPDF (extrair o texto do PDF dos resumos)
- Streamlit (tela, se o formato escolhido tiver uma)
- pandas, scikit-learn, `krippendorff` (comparação)
- Git/GitHub (repositório público, para a orientadora ter acesso)

### 7.6 Estrutura do repositório

```
RAG-TCC/
├── data/
│   ├── corpus.json
│   ├── base_metodologia.md
│   ├── analise_manual.json   # só para a comparação, nunca lido pela ferramenta; fora do GitHub
│   ├── analise_com_ia.json   # respostas da análise com a ferramenta
│   └── sugestoes/            # respostas da IA, uma pasta por versão (modelo + prompt)
├── src/
│   ├── preparar_dados.py     # PDF → corpus.json; CSV do Forms → analise_manual.json
│   ├── unitarizar.py
│   ├── indexar.py
│   ├── recuperar.py
│   ├── sugerir.py            # prompt + Ollama + JSON
│   ├── validar.py
│   └── comparar.py           # comparação da seção 8
├── app/
│   └── interface.py          # forma de uso (formato a decidir)
├── docs/
│   ├── PLANEJAMENTO_TCC.md
│   └── TECNICAS_RAG_REFERENCIA.md
├── notebooks/
├── config.py
└── requirements.txt
```

### 7.7 Ajustar a ferramenta sem "roubar"

- Ajustar os prompts e a base metodológica com **3 a 5 dissertações de fora das 59** (ex.: de 2022). Se o grupo ajustasse a ferramenta olhando as 59, ela ficaria boa justamente nelas, e a comparação ficaria injusta.
- Antes de o grupo começar a análise com a ferramenta, **fixar** modelo, prompt e base metodológica. Todos usam a mesma versão do começo ao fim.
- Fazer um teste rápido de uso com 2 ou 3 dissertações de fora das 59, para ajustar a usabilidade.

## 8. Como comparar (proposta, a validar com o grupo e a orientadora)

As respostas são texto livre, então não dá para comparar só com "igual/diferente". A proposta combina três formas:

1. **Classificação às cegas (principal).** Juntar todas as respostas (manuais e com a ferramenta), embaralhadas e **sem indicar de onde vieram**. O grupo (ou a orientadora) agrupa as temáticas em categorias e separa cada resposta de metodologias nos eixos da seção 6.3 (abordagem, procedimento, coleta, análise). Com isso as respostas ficam comparáveis.
2. **Similaridade de sentido.** Medir, com embeddings, o quanto duas respostas dizem a mesma coisa (ex.: "saúde da pessoa idosa" ≈ "saúde do idoso"). Serve de apoio e de conferência da forma 1.
3. **Nota de qualidade às cegas.** Um avaliador lê o resumo e dá nota de 1 a 5 para cada resposta, sem saber de onde ela veio: a temática representa o resumo? As metodologias estão corretas e completas?

Temática 1 e temática 2 são comparadas **como par** (a ordem não importa).

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

Uma pessoa puxa cada frente, mas todos participam um pouco de cada uma. Na análise com a ferramenta, **todos** analisam.

| Frente | O que inclui | Responsável |
| --- | --- | --- |
| Dados | PDF → `corpus.json`, Forms → `analise_manual.json`, sorteio de quem analisa o quê | a definir |
| Base metodológica | Glossário (seção 6.3), revisão com a orientadora | a definir |
| Busca (RAG) | Unitarização, embeddings, índice, recuperação | a definir |
| IA e forma de uso | Prompts, formato da resposta, testes de modelos, validação, tela | a definir |
| Comparação e escrita | Classificação às cegas, métricas, gráficos, análise das divergências, texto | a definir |

Rotina sugerida: reunião curta semanal, quadro de tarefas (GitHub Projects) e pull requests revisados por outro membro.

## 10. Ordem das etapas

A análise com a ferramenta começa quando a ferramenta estiver pronta e fixada.

1. `corpus.json` extraído do PDF e conferido; `analise_manual.json`; repositório; base metodológica v1; **decidir o formato da ferramenta**
2. Unitarização, embeddings, índice e busca; primeira versão das respostas da IA
3. Validação da evidência; ajuste com dissertações de fora das 59; escolha do modelo; forma de uso
4. Teste rápido de uso; **fixar** a versão da ferramenta
5. **Análise com a ferramenta**: cada membro analisa suas ~23 dissertações
6. Classificação às cegas, notas de qualidade, métricas
7. Escrita de resultados e discussão; revisão pela orientadora
8. Revisão final e apresentação

## 11. Riscos

| Risco | Como reduzir |
| --- | --- |
| Pessoa lembra da própria resposta manual | Cada membro analisa com a ferramenta resumos que não analisou antes (4.2) |
| Analistas copiam a IA sem pensar | Mostrar sempre a evidência; medir "usei/editei/ignorei" e a similaridade com o que a IA indicou |
| Respostas abertas difíceis de comparar | Classificação às cegas + similaridade + nota de qualidade (seção 8) |
| Resumo não informa o método | Resposta "não informado no resumo" |
| Modelo local fraco ou lento | Testar 2–3 modelos na máquina prevista |
| Ferramenta ajustada com as respostas manuais | A ferramenta nunca lê `analise_manual.json`; ajustar só com dissertações de fora das 59 |
| Erro ao passar o PDF para o `corpus.json` | Conferência manual de cada dissertação contra o PDF |
| Formato decidido tarde | Construir primeiro a base comum (etapas 1 a 6), que serve para qualquer formato |
| Dado sensível no GitHub (repositório público) | `.gitignore` bloqueia `analise_manual.json` e CSVs; analistas sempre anonimizados |
| Tempo da análise manual não registrado | Comparação de tempo descritiva; citar como limitação |
| Ferramenta atrasar e empurrar a análise, a comparação e a escrita | Priorizar a base comum e a análise com a ferramenta; comparações extras só se sobrar tempo |

## 12. Decisões em aberto

- [ ] **Formato da ferramenta:** chat, sugestões, automático ou uma combinação (7.1)
- [ ] Confirmar se a pergunta de pesquisa da seção 3 é o texto oficial do projeto
- [ ] Onde registrar as respostas da análise com a ferramenta (Google Forms ou na própria ferramenta)
- [ ] Se o tempo da análise manual foi registrado (mesmo que aproximado)
- [ ] Quem faz a classificação às cegas e a nota de qualidade (grupo, orientadora ou ambos)
- [ ] Quais modelos do Ollama cabem na máquina prevista (teste)
- [ ] FAISS ou ChromaDB
- [ ] Quais dissertações de fora das 59 usar para o ajuste
- [ ] Responsáveis por cada frente
