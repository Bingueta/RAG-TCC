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
| 3 — Geração com LLM e validação | Próxima | Lucas |
| 4 — Orquestração, configuração e Excel | Depois da Parte 3 | Lucas |
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
1. **Comparar LLMs de forças diferentes.** O mesmo processo roda com um modelo mais fraco, um mais forte e um mais potente, para ver se a qualidade das respostas do Excel muda. Sugestão, a confirmar na máquina (RTX 2060 6 GB, 16 GB de RAM): `qwen2.5:3b-instruct` (fraco), `qwen2.5:7b-instruct` (forte) e `qwen2.5:14b-instruct` (mais potente; não cabe inteiro nos 6 GB da placa, então o Ollama divide com a RAM e fica mais lento). Usar a mesma família (Qwen) isola o efeito do tamanho; um modelo de outra família (ex.: `llama3.1:8b`) pode entrar como extra. O modelo é escolhido por configuração, sem mexer no código.
2. **Metodologias incomuns.** A base de metodologias é uma **referência, não uma lista fechada**. Muitos resumos usam metodologias pouco comuns ou com nome de autor (ex.: "pesquisa-ação segundo Thiollent", "abordagem de tal autor"). O prompt deve deixar o LLM **interpretar e nomear a metodologia como o resumo descreve**, mesmo que ela não esteja na base, sempre apontando a frase que a justifica. Inventar continua proibido: se o resumo não diz o método, a resposta é "Não informado no resumo".

### Checklist

**Etapa 1 — Ambiente**
- [ ] 1.1 Criar a branch `feature/parte-3-geracao` a partir da `main` atualizada
- [ ] 1.2 Instalar o Ollama e baixar os modelos (fraco, forte, mais potente); confirmar quais rodam na máquina e quanto tempo cada um leva por dissertação
- [ ] 1.3 Instalar a biblioteca `ollama` (Python) e fixar a versão no `requirements.txt`
- [ ] 1.4 Acrescentar a `src/contratos.py` os tipos `Campo` e `RespostaIA` (seção 3.1 da divisão)
- [ ] 1.5 Acrescentar a seção da Parte 3 ao `config.py`: lista de modelos com rótulo (fraco/forte/potente), versão do prompt, `temperature=0`, `seed` fixa, `num_ctx`

**Etapa 2 — Prompt**
- [ ] 2.1 `src/prompts/v1.txt` partindo do "prompt interpretativo" do projeto de referência (TECNICAS 3.8): sempre **duas** temáticas; **todas** as metodologias; cada resposta com os ids das frases (F1, F2…) que a justificam; "Não informado no resumo" quando o método não aparece
- [ ] 2.2 Incluir no prompt a regra das metodologias incomuns (requisito 2 acima): a base é referência; pode nomear método fora dela, como o resumo descreve, com evidência
- [ ] 2.3 `montar_prompt(dissertacao, contexto, versao)` em `src/sugerir.py` (testável sem Ollama)

**Etapa 3 — Chamada ao modelo**
- [ ] 3.1 `gerar_resposta(dissertacao, contexto, modelo)`: Ollama com `format` = JSON Schema, `temperature=0`, `seed` fixa
- [ ] 3.2 Ler a resposta; se o JSON vier quebrado, tentar mais uma vez; se falhar, devolver `status="erro"` com a `saida_bruta`. Nunca travar o programa

**Etapa 4 — Validação**
- [ ] 4.1 `validar(resposta, dissertacao)` em `src/validar.py`: evidência citada tem que existir nas frases (senão `sem_evidencia`); tirar metodologias repetidas; tratar temática vazia
- [ ] 4.2 Testes sem Ollama: `montar_prompt`, leitura de saídas ruins (JSON quebrado, frase inexistente, resposta vazia) e `validar`

**Etapa 5 — Ajuste do prompt (só com a calibração)**
- [ ] 5.1 Rodar nas 20 dissertações de 2022 com os 3 modelos e ler as respostas
- [ ] 5.2 Ajustar o prompt **olhando só a calibração**; guardar cada versão (`v1`, `v2`…); fixar a versão final antes de rodar nas 59

**Etapa 6 — Fechamento**
- [ ] 6.1 Testes passando; pull request `[Parte 3] Geração com LLM e validação`

### Próximo passo
Lucas: tarefa 1.1.

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
- [ ] 6 Relatório em Excel (espera o `openpyxl` da Parte 4) e gráfico por indicador
- [ ] 7–9 Análise manual: só quando a professora enviar as respostas

### Próximo passo
Medir o v2 com a busca corrigida (Parte 2) contra o v2 antigo no `hibrido`; depois, o v3 (último ajuste). A régua fica congelada até lá: `src/comparar.py` e a referência com o mesmo sha256 da medição do v2, e a base só pode mudar nos `sinais` (o `comparar.py` usa só `id`, `termo`, `eixo` e `sinonimos`).

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
| 2026-10-07 | 2 | Na busca por sentido, cada verbete é representado pelo termo + sinônimos; a técnica `hibrido` soma a busca por palavra exata (BM25, juntos por RRF) | Na calibração, termos de método escritos no resumo que viram verbete: 16/26 com a definição, 20/26 só com termo + sinônimos, 27/27 com `hibrido` |
| 2026-10-07 | 5 | Referência da calibração escrita por IA, às cegas, fora do git, só para ajustar o prompt; não substitui o gabarito humano. Cada metodologia é marcada como dita no resumo (cobrada na revocação) ou interpretação aceitável (não tira precisão) | Sem gabarito humano ainda, a Parte 3 precisava de uma régua; escrita antes das execuções para não copiar o modelo |
| 2026-10-07 | 5 | Metodologia é reconhecida pela base + sinônimos e, se não bater exata, pelo conteúdo: conta todo método cujas palavras estão no item. O formato (item curto e exato × frase) é medido à parte | Os modelos juntam vários métodos num item só; a comparação exata dava zero a respostas certas |
