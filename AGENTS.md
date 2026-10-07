# Regras para quem trabalha neste repositório (pessoas e assistentes de IA)

## Antes de qualquer coisa

Leia [docs/CONTEXTO_DO_PROJETO.md](docs/CONTEXTO_DO_PROJETO.md) e a seção da sua parte em [docs/divisao-tarefas.md](docs/divisao-tarefas.md).

## Acompanhamento

- Para qualquer trabalho em qualquer parte, leia [docs/PROGRESSO.md](docs/PROGRESSO.md) **antes** de começar. Depois de cada tarefa, marque o checklist e atualize o próximo passo. Na tabela de decisões, registre **só decisões estratégicas e importantes**; não crie log de cada tarefa nem novos arquivos Markdown.

## Regras do projeto

- A ferramenta nunca lê `data/analise_manual.json`.
- O prompt e a base de metodologias só são ajustados com as 20 dissertações de 2022, de fora das 59 (`data/calibracao/`).
- `data/brutos/dissertacoes.json` e `data/brutos/calibracao.json` são os originais: só leitura.
- Cada parte mexe só nos próprios arquivos. Mudança nos contratos compartilhados (`src/contratos.py`) é registrada como decisão em `docs/PROGRESSO.md`.
- O repositório é público: nada de nomes de analistas, respostas da análise manual, senhas ou dados de servidor.
- Escreva em português.
