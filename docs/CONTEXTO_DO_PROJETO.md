# Contexto do projeto

Resumo de uma página para quem chega agora no repositório: membros do grupo, a orientadora ou alguém ajudando no código. Os detalhes estão em [PLANEJAMENTO_TCC.md](PLANEJAMENTO_TCC.md) e [divisao-tarefas.md](divisao-tarefas.md).

## O que é

TCC de Sistemas de Informação da Univale: **"Análise de Conteúdo Acadêmico Assistida por IA: Uma Abordagem com LLMs e RAG"**.

O grupo já fez, sem IA, uma análise de conteúdo de **59 dissertações** (2023–2025): para cada uma, identificou as **duas temáticas principais** e as **metodologias**. Agora vamos construir uma ferramenta de IA que faz a mesma tarefa e medir se ela ajuda.

## Como a ferramenta funciona

- **Automática, em lote:** lê as 59 dissertações (título, resumo e palavras-chave) e grava uma **planilha Excel** com `id`, `titulo`, `tematica_1`, `tematica_2`, `metodologias` e `modelo`. Não é chat e não tem tela.
- **Mostra de onde tirou cada resposta:** uma segunda aba da planilha traz a frase do resumo que justifica cada temática e metodologia.
- **IA local:** o modelo roda no próprio computador, pelo **Ollama**, sem internet e sem pagar API.
- **RAG:** antes de responder, o programa busca as frases certas do resumo e os verbetes de uma **base de metodologias** escrita pelo grupo, e entrega isso ao modelo. Isso reduz a invenção e ajuda a dar o nome técnico certo ao método.
- **Comparável:** o modelo e a técnica de RAG são trocados por configuração, para comparar modelos mais fortes e mais fracos e técnicas diferentes (sem RAG, busca densa, busca híbrida).

## Como vamos avaliar

1. **IA sozinha × análise manual:** as respostas da IA são comparadas com as do grupo. Essas respostas serão enviadas pela professora **depois que o RAG estiver pronto**; até lá, o foco é só gerar as respostas da IA e avaliá-las com indicadores que não precisam de gabarito. Nas metodologias, por precisão, revocação e F1; nas temáticas, por similaridade de sentido. A régua é o **teto humano**: o quanto os 2 analistas de cada dissertação concordam entre si.
2. **Análise manual × análise com a ferramenta:** o grupo refaz a análise das 59, cada membro com dissertações que **não analisou antes**, consultando a planilha da IA como apoio. Depois compara com a análise manual (concordância, qualidade, tempo, se as pessoas copiam a IA).

## Situação atual

| Item | Situação |
| --- | --- |
| Análise manual | Concluída (118 análises no Google Forms). As respostas serão enviadas pela professora depois que o RAG estiver pronto |
| Dissertações em JSON | Prontas: `data/brutos/dissertacoes.json` (original) e `data/corpus.json` (preparado) |
| Planejamento | [PLANEJAMENTO_TCC.md](PLANEJAMENTO_TCC.md) |
| Divisão do código em 5 partes | Em execução: [divisao-tarefas.md](divisao-tarefas.md). Andamento em [PROGRESSO.md](PROGRESSO.md) |
| Código | Partes 1 (dados e frases) e 2 (base de metodologias e busca) prontas e testadas; próximas: Parte 3 (LLM) e Parte 4 (Excel) |
| Calibração | 20 dissertações de 2022, de fora das 59: `data/brutos/calibracao.json` |

## Regras que não podem ser quebradas

1. **A ferramenta nunca lê as respostas da análise manual** (`data/analise_manual.json`). Elas só servem para a avaliação. Um teste automático garante isso.
2. **Sem "roubar":** prompt e base de metodologias são ajustados só com as 20 dissertações de 2022 **de fora das 59** (`data/calibracao/`).
3. **Fixar antes de medir:** prompt e base ficam fixos antes de rodar nas 59, e todos os modelos rodam com a mesma versão.
4. **O `corpus.json` não muda** depois que a análise com a ferramenta começar.
5. **Reprodutível:** todos os parâmetros num único `config.py`, com justificativa; `temperature=0` e `seed` fixa.
6. **Repositório público:** nenhuma resposta da análise manual, nome de analista (sempre A1 a A5), senha ou dado de servidor vai para o GitHub.

## Onde está cada coisa

| Caminho | O que é |
| --- | --- |
| `data/brutos/dissertacoes.json` | As 59 dissertações, como foram passadas do PDF. **Não editar** |
| `data/corpus.json` | Versão preparada pelo programa, com `id` (D001 a D059) |
| `data/base_metodologia.json` | Base de metodologias que o RAG consulta |
| `data/calibracao/` | As 20 dissertações de 2022 (de fora das 59), para ajustar o prompt |
| `data/sugestoes/` | Planilhas geradas pela IA, uma pasta por execução |
| `src/` | Código, um arquivo por etapa |
| `tests/` | Testes automáticos e dados de exemplo |
| `docs/` | Planejamento, divisão de tarefas, técnicas de referência e este resumo |

## Ambiente

Python 3.11, Windows. Máquina prevista para rodar os modelos: i5 de 10ª geração, 16 GB de RAM, RTX 2060 (6 GB). A instalação será descrita no [README](../README.md) quando o código começar.

## Para saber mais

- Termos técnicos: glossário na seção 2 do [planejamento](PLANEJAMENTO_TCC.md).
- Técnicas de RAG já testadas num projeto anterior: [TECNICAS_RAG_REFERENCIA.md](TECNICAS_RAG_REFERENCIA.md).
- Decisões ainda em aberto: seção 12 do planejamento e seção 7 da divisão de tarefas.
