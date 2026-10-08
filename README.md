# Análise de Conteúdo Acadêmico Assistida por IA: Uma Abordagem com LLMs e RAG

Trabalho de Conclusão de Curso — Sistemas de Informação, Universidade Vale do Rio Doce (Univale).

**Grupo:** Franklyn Rodrigues dos Santos, Igor Coelho Brasil, Lucas Andrade Feres, Felipe Dias Ribeiro, Helber Fernandes Rodrigues
**Orientadora:** Prof.ª Dr.ª Cristiane Mendes Netto

## O que é

Uma ferramenta que usa IA para **ajudar na análise de conteúdo** de resumos de dissertações: identificar as **duas temáticas principais** e as **metodologias** de cada uma, sempre mostrando a frase do resumo que justifica a resposta. A IA roda no próprio computador (via Ollama) e usa RAG, isto é, busca os trechos certos do resumo antes de responder, para não inventar.

O grupo já fez uma análise manual (sem IA) de 59 dissertações. A ferramenta vai ser avaliada de duas formas: comparando as respostas da IA sozinha com a análise manual, e comparando a análise manual com uma nova análise do grupo feita com o apoio da ferramenta.

## Situação atual

**A ferramenta funciona.** Ela é **automática**: roda as 59 dissertações em lote e gera uma planilha Excel por combinação de modelo e técnica de RAG. Partes 1 a 4 prontas e testadas; a Parte 5 (avaliação) mede a calibração e, nas 59, os indicadores que não precisam de gabarito. A comparação com a análise manual espera as respostas que a professora vai enviar.

- Andamento e decisões: [docs/PROGRESSO.md](docs/PROGRESSO.md).
- Qual LLM foi usado, como, o passo a passo e os números: [docs/RESULTADOS.md](docs/RESULTADOS.md).

## Por onde começar

1. Leia [docs/CONTEXTO_DO_PROJETO.md](docs/CONTEXTO_DO_PROJETO.md): o projeto inteiro em uma página.
2. Veja como o código foi dividido em 5 partes em [docs/divisao-tarefas.md](docs/divisao-tarefas.md).
3. Os detalhes estão em [docs/PLANEJAMENTO_TCC.md](docs/PLANEJAMENTO_TCC.md). A seção 2 é um glossário com os termos técnicos.
4. Se quiser entender as técnicas que vão ser usadas, leia [docs/TECNICAS_RAG_REFERENCIA.md](docs/TECNICAS_RAG_REFERENCIA.md).

## Estrutura das pastas

| Pasta | O que vai ter |
| --- | --- |
| `data/` | Os dados: as 59 dissertações (original em `brutos/dissertacoes.json`, versão preparada em `corpus.json`), base de metodologia e respostas da IA (`sugestoes/`) |
| `src/` | O código da ferramenta, uma parte por arquivo |
| `tests/` | Testes automáticos e dados de exemplo (dissertações inventadas, nunca uma das 59) |
| `docs/` | Planejamento, divisão de tarefas, progresso e resultados |
| `notebooks/` | Scripts de apoio: a calibração da Parte 3 e os diagnósticos da Parte 5 |

## Regras importantes

- **As respostas da análise manual não vão para o GitHub.** O repositório é público. O arquivo `data/analise_manual.json` e os CSVs do Google Forms ficam só no computador de cada um (o `.gitignore` já bloqueia).
- **A ferramenta nunca lê as respostas da análise manual.** Se lesse, estaria copiando o grupo, e a comparação não mediria nada.
- Os analistas aparecem sempre anonimizados (A1 a A5).
- Nada de senha, chave de API ou dado pessoal no repositório.

## Instalação

Testado no Windows 11 com Python 3.11. Os comandos são do PowerShell, na pasta do repositório.

**1. Python e bibliotecas.** Instala também o modelo de português do spaCy e o torch para CPU, cerca de 1 GB no total.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

**2. Ollama e os modelos.** O Ollama roda os LLMs no próprio computador, sem internet e sem pagar API. Os três modelos ocupam ~12 GB. Para guardá-los fora do disco C:, troque a pasta em *Settings → Model location* no aplicativo do Ollama: a variável `OLLAMA_MODELS` não basta, porque o aplicativo usa a pasta das configurações dele.

```powershell
winget install --id Ollama.Ollama
ollama pull qwen3.5:2b-q4_K_M
ollama pull qwen3.5:4b-q4_K_M
ollama pull qwen3.5:9b-q4_K_M
```

**3. Índice de vetores.** Na primeira vez, baixa o modelo de embedding (~1 GB). Rode de novo sempre que o corpus ou a base de metodologias mudarem.

```powershell
.\.venv\Scripts\python -m src.indexar
```

**4. Conferir.** Os testes não precisam do Ollama.

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m src.pipeline --mock      # o caminho inteiro com 3 dissertações inventadas
```

## Uso

```powershell
.\.venv\Scripts\python -m src.pipeline                       # modelo e técnica padrão do config.py, nas 59
.\.venv\Scripts\python -m src.pipeline --todos               # 3 modelos × 3 técnicas
.\.venv\Scripts\python -m src.pipeline --modelo qwen3.5:4b-q4_K_M --tecnica sem_rag
.\.venv\Scripts\python -m src.pipeline --corpus calibracao   # as 20 de calibração
```

Cada execução grava uma pasta em `data/sugestoes/<modelo>__<técnica>__<prompt>/`, com:

- `respostas.xlsx`: a planilha, com as abas `respostas`, `detalhes` e `execucao`;
- `respostas.json`: as respostas completas;
- `execucao.json`: a máquina, o modelo exato, os parâmetros e o tempo de cada dissertação.

Se o programa parar no meio, rodar o mesmo comando de novo retoma de onde parou. Na RTX 3060 Ti, as 59 levam de ~1,5 min (2b) a ~5 min (9b) por técnica.
