# Análise de Conteúdo Acadêmico Assistida por IA: Uma Abordagem com LLMs e RAG

Trabalho de Conclusão de Curso — Sistemas de Informação, Universidade Vale do Rio Doce (Univale).

**Grupo:** Franklyn Rodrigues dos Santos, Igor Coelho Brasil, Lucas Andrade Feres, Felipe Dias Ribeiro, Helber Fernandes Rodrigues
**Orientadora:** Prof.ª Dr.ª Cristiane Mendes Netto

## O que é

Uma ferramenta que usa IA para **ajudar na análise de conteúdo** de resumos de dissertações: identificar as **duas temáticas principais** e as **metodologias** de cada uma, sempre mostrando a frase do resumo que justifica a resposta. A IA roda no próprio computador (via Ollama) e usa RAG, isto é, busca os trechos certos do resumo antes de responder, para não inventar.

O grupo já fez uma análise manual (sem IA) de 59 dissertações. Depois de construir a ferramenta, o grupo vai analisar as mesmas 59 com a ajuda dela e comparar os resultados, para saber se com a IA ficou melhor.

## Situação atual

**Em planejamento.** Ainda não há código. O formato da ferramenta (chat, sugestões ou geração automática) ainda vai ser decidido pelo grupo.

## Por onde começar

1. Leia [docs/PLANEJAMENTO_TCC.md](docs/PLANEJAMENTO_TCC.md). A seção 2 é um glossário com os termos técnicos.
2. Veja as **decisões em aberto** na seção 12 do planejamento. Elas serão discutidas em reunião.
3. Se quiser entender as técnicas que vão ser usadas, leia [docs/TECNICAS_RAG_REFERENCIA.md](docs/TECNICAS_RAG_REFERENCIA.md).

## Estrutura das pastas

| Pasta | O que vai ter |
| --- | --- |
| `data/` | Os dados: resumos das dissertações (`corpus.json`), base de metodologia e respostas da IA (`sugestoes/`) |
| `src/` | O código da ferramenta, uma parte por arquivo |
| `app/` | A forma de usar a ferramenta (tela ou chat, conforme o formato escolhido) |
| `docs/` | Os documentos de planejamento |
| `notebooks/` | Testes e análises exploratórias |

## Regras importantes

- **As respostas da análise manual não vão para o GitHub.** O repositório é público. O arquivo `data/analise_manual.json` e os CSVs do Google Forms ficam só no computador de cada um (o `.gitignore` já bloqueia).
- **A ferramenta nunca lê as respostas da análise manual.** Se lesse, estaria copiando o grupo, e a comparação não mediria nada.
- Os analistas aparecem sempre anonimizados (A1 a A5).
- Nada de senha, chave de API ou dado pessoal no repositório.

## Instalação

Será descrita aqui quando o código começar (Python 3.11, Windows).
