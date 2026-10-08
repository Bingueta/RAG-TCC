# Resultados — calibração (Parte 3) e execução nas 59 (Parte 4)

Registro do que foi rodado, com qual LLM, como e com que resultado, para qualquer pessoa do grupo (ou a orientadora) conferir e repetir. Pedido do Franklyn em 07/10/2026.

**Escopo:** o ajuste foi feito só com as **20 dissertações de calibração** (2022, C001 a C020, de fora das 59). Só depois de prompt e base fixados (tag `v1-fixado` no git) a ferramenta rodou nas 59 (seção 5.6), e nada foi ajustado olhando o resultado delas (regra C3). O andamento e as decisões estão em [PROGRESSO.md](PROGRESSO.md); este arquivo guarda os **números** e o **passo a passo**.

## 1. Resumo

| Item | Escolha | Por quê (seção) |
| --- | --- | --- |
| LLMs | `qwen3.5:2b` (fraco), `qwen3.5:4b` (forte), `qwen3.5:9b` (potente), todos `q4_K_M` | 5.1 |
| Técnicas de RAG | `sem_rag`, `denso`, `hibrido`, todas mantidas para comparar | 5.2 |
| Prompt | `v3`, fixado pelo critério escrito antes da rodada; margem mínima (empate com o `v2` dentro do ruído) | 5.3 a 5.5 |
| Busca `hibrido` | corrigida: sinal de várias palavras só casa como expressão inteira | 5.4 |
| Execução nas 59 | 3 modelos × 3 técnicas, prompt `v3`: 9 planilhas em `data/sugestoes/` | 5.6 |

## 2. Ambiente

| | |
| --- | --- |
| Máquina | PC do Lucas: AMD Ryzen 7 5700X, 16 GB de RAM, NVIDIA RTX 3060 Ti (8 GB), driver 610.62 |
| Sistema | Windows 11 (build 26200), Python 3.11.9 |
| LLM local | Ollama 0.40.0 (`ollama` 0.6.3 no Python); modelos em `D:\ollama\modelos` |
| Bibliotecas | `sentence-transformers` 6.1.0, `torch` 2.14.1 (CPU), `spacy` 3.8.16, `rank-bm25` 0.2.2, `numpy` 2.4.6 |
| Embedding | `intfloat/multilingual-e5-base`, na CPU (a placa fica para o LLM) |

**Modelos testados.** O `digest` identifica exatamente o arquivo baixado: o nome no Ollama pode passar a apontar para outra versão, o digest não.

| Modelo | Digest (12 primeiros) | Tamanho carregado | Na VRAM |
| --- | --- | --- | --- |
| `qwen3.5:2b-q4_K_M` | `1e2d21a4f03a` | 1,7 GB | 100% |
| `qwen3.5:4b-q4_K_M` | `d8b0f5e9760c` | 3,3 GB | 100% |
| `qwen3.5:9b-q4_K_M` | `56671c2ab938` | 6,4 GB | 88% (o resto na RAM) |
| `qwen3:8b-q4_K_M` | `500a1f067a9f` | 6,2 GB | 100% |
| `qwen2.5:7b-instruct-q4_K_M` | `845dbda0ea48` | 5,1 GB | 100% |

O 9b não coube inteiro porque o Windows e os programas abertos ocupavam ~2,5 GB da placa. Isso pesa no tempo, não na resposta.

## 3. Método

### 3.1 Caminho de cada dissertação

1. **Frases** (Parte 1): o resumo é dividido em frases numeradas F1, F2… (`src/unitarizar.py`).
2. **Busca** (Parte 2): `recuperar(dissertacao, tecnica)` escolhe as frases que falam do tema, as que falam do método e os verbetes da base de metodologias (`src/recuperar.py`).
3. **Prompt** (Parte 3): título, palavras-chave, frases escolhidas e verbetes entram no texto de `src/prompts/<versão>.txt` (`montar_prompt`, em `src/sugerir.py`).
4. **LLM** (Parte 3): Ollama com `format` = JSON Schema, que obriga a resposta a vir no formato combinado: duas temáticas e uma lista de metodologias, cada uma com os códigos das frases que a justificam (`gerar_resposta`).
5. **Validação** (Parte 3): o status de cada campo é calculado pelo programa, nunca aceito do modelo (`src/validar.py`).

### 3.2 Técnicas de RAG

| Técnica | O que o modelo recebe |
| --- | --- |
| `sem_rag` | O resumo inteiro e nenhum verbete. Linha de base |
| `denso` | As 5 frases mais parecidas (por sentido) com "tema" e com "método", e os 5 verbetes mais parecidos com as frases de método |
| `hibrido` | O mesmo, juntando a busca por sentido com a busca por palavra exata (BM25, juntas por RRF, k = 60) |

### 3.3 Parâmetros (todos no `config.py`)

| Parâmetro | Valor | Motivo |
| --- | --- | --- |
| `temperature` | 0 | A mesma dissertação dá sempre a mesma resposta |
| `seed` | 42 | Idem |
| `num_ctx` | 8192 | O padrão do Ollama (2048) estourava no projeto de referência |
| `think` | desligado | Os Qwen3/3.5 "pensam" antes de responder; isso deixa a resposta várias vezes mais lenta e fica fora do JSON |
| Tentativas | 2 | Se o JSON vier quebrado, a segunda tentativa devolve o erro ao modelo (com temperatura 0, repetir o pedido daria a mesma resposta) |

### 3.4 Validação da evidência

- Todo código citado tem que existir no resumo **e ter sido mostrado ao modelo**. Com RAG ele vê só algumas frases; citar uma que não viu é inventar. Código inválido é descartado; se não sobra nenhum, o campo fica `sem_evidencia`.
- O esquema JSON obriga o **formato** do código (`F` + número), mas não diz quais existem, para continuar sendo possível medir quanto o modelo inventa.
- Metodologia repetida sai; "Não informado no resumo" só vale sozinho; temática vazia é `erro`.

### 3.5 Como as respostas foram avaliadas

- **Referência:** escrita por uma IA (a sessão de avaliação), **às cegas**, antes de qualquer resposta dos modelos existir, olhando só título, resumo e palavras-chave das 20. **Não é o gabarito do grupo.** Cada metodologia da referência é marcada como *dita no resumo* (cobrada) ou *interpretação aceitável* (não tira ponto se aparecer).
- **Metodologias:** precisão (P, os aceitáveis contam como acerto), precisão estrita (os aceitáveis contam como erro), revocação (R, só os ditos no resumo) e F1, por dissertação, com intervalo de confiança de 95% por bootstrap (5000 reamostras). O reconhecimento de termos usa a base de metodologias e os sinônimos.
- **Temáticas:** a similaridade crua do e5 fica entre 0,91 e 0,95 para todos e não discrimina. Por isso duas medidas: **margem** (similaridade com a própria referência menos a média com as outras 19) e **acerto@1** (o par fica mais perto da própria referência do que de qualquer outra).
- **Formato:** *itens exatos* é a fração de metodologias escritas como nome limpo (o que vai para a célula do Excel), e não como frase.
- **Régua congelada:** a referência e o `src/comparar.py` ficaram com o mesmo sha256 do `v2` em diante; a mudança da base mexeu só nos `sinais`, que a avaliação não lê.

### 3.6 Cuidados para não "roubar"

- Ninguém olhou as 59 para ajustar nada: prompt e busca foram ajustados só com as 20 de calibração.
- Os exemplos escritos no prompt foram inventados e conferidos contra o texto das 20, para a medida não sair otimista.
- O `v3` é o último ajuste, e o critério para ele substituir o `v2` foi escrito no PROGRESSO.md **antes** da rodada.

## 4. Passo a passo para repetir

```powershell
# 1. Ambiente (uma vez)
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
winget install --id Ollama.Ollama          # e, no app do Ollama, a pasta dos modelos
ollama pull qwen3.5:2b-q4_K_M
ollama pull qwen3.5:4b-q4_K_M
ollama pull qwen3.5:9b-q4_K_M

# 2. Índice de vetores (de novo sempre que o corpus ou a base mudarem)
.\.venv\Scripts\python -m src.indexar

# 3. Testes (sem Ollama)
.\.venv\Scripts\python -m pytest

# 4. Rodar a calibração (exemplo: o prompt final, três técnicas, três modelos)
.\.venv\Scripts\python notebooks/parte3_calibracao.py --versao v3 --tecnicas sem_rag denso hibrido `
    --modelos qwen3.5:2b-q4_K_M qwen3.5:4b-q4_K_M qwen3.5:9b-q4_K_M

# 5. Medir a calibração (Parte 5)
.\.venv\Scripts\python -m src.comparar

# 6. Rodar nas 59 e gerar as planilhas (Parte 4): 3 modelos × 3 técnicas, prompt v3
.\.venv\Scripts\python -m src.pipeline --todos
```

Com a mesma máquina, o mesmo digest de modelo e os mesmos arquivos, as respostas saem iguais (temperatura 0 e seed fixa). Em outra placa, ou com outra fração do modelo na VRAM, pequenas diferenças numéricas podem mudar alguma resposta.

## 5. Resultados

### 5.1 Rodada 1 — prompt `v1`, técnica `hibrido`, 5 modelos

| Modelo | P | P estrita | R | F1 [IC95] | Itens exatos | Temáticas: margem / acerto@1 | Tempo por dissertação |
| --- | --- | --- | --- | --- | --- | --- | --- |
| qwen3.5:4b | 0,83 | 0,74 | 0,83 | 0,80 [0,73; 0,87] | 37% | 0,053 / 0,95 | 3,5 s |
| qwen3.5:9b | 0,79 | 0,64 | 0,67 | 0,69 [0,55; 0,82] | 92% | 0,073 / 1,00 | 4,8 s |
| qwen3:8b | 0,68 | 0,60 | 0,69 | 0,65 [0,52; 0,77] | 72% | 0,055 / 0,85 | 4,1 s |
| qwen2.5:7b | 0,65 | 0,60 | 0,49 | 0,53 [0,39; 0,66] | 91% | 0,054 / 0,90 | 2,4 s |
| qwen3.5:2b | 0,53 | 0,47 | 0,36 | 0,40 [0,26; 0,55] | 71% | 0,032 / 0,65 | 1,6 s |

Nenhum erro de formato, nenhuma segunda tentativa, nos cinco.

- **Família:** a Qwen3.5 vence na faixa de 7 a 9 bilhões de parâmetros. 9b − qwen2.5:7b = +0,16 de F1 [+0,01; +0,33]. Contra o qwen3:8b, empate no F1 (+0,04 [−0,07; +0,14]), mas o 9b tem temáticas e formato melhores.
- **Escada:** o 2b é claramente o fraco (4b − 2b = +0,40 [+0,24; +0,57]). O 4b e o 9b **não se separam em qualidade**, e no `v1` tinham defeitos opostos: o 4b acertava o conteúdo escrito como frase longa (37% de itens exatos); o 9b escrevia nome limpo, mas inventava. A ordem forte/potente fica pelo tamanho.

### 5.2 Técnicas de RAG

Com o prompt `v1`, nos três Qwen3.5: `hibrido` e `sem_rag` não se distinguem no 9b (−0,03 de F1) nem no 4b (+0,04). No 2b, o RAG atrapalha: F1 0,60 (`sem_rag`), 0,54 (`denso`), 0,40 (`hibrido`). Uma explicação provável: o resumo tem de 5 a 18 frases, então mandar o resumo inteiro já cabe e não esconde nada do modelo.

### 5.3 Rodada 2 — prompt `v2`

O `v2` saiu dos padrões de erro do `v1`, como regras gerais: um método por item com nome curto; procedimento só com nome ou descrição sem ambiguidade ("lugar não é estudo de caso"); tipo da entrevista só o que o resumo diz; fonte dos dados (documental, dados secundários, bibliográfica) com a lista tirada das definições da própria base.

**v2 − v1, F1 pareado [IC95]:**

| | `hibrido` | `sem_rag` | `denso` |
| --- | --- | --- | --- |
| 2b | +0,27 [+0,12; +0,43] | +0,06 [−0,07; +0,19] | +0,05 [−0,09; +0,21] |
| 4b | +0,04 [−0,04; +0,12] | +0,07 [−0,03; +0,17] | +0,10 [−0,00; +0,21] |
| 9b | +0,01 [−0,06; +0,08] | +0,11 [+0,03; +0,21] | +0,07 [+0,00; +0,15] |

F1 do `v2`: 4b 0,84 / 0,83 / 0,82 e 9b 0,70 / 0,83 / 0,79 (`hibrido` / `sem_rag` / `denso`). São 9 comparações com 20 dissertações: um intervalo que mal encosta no zero pode ser sorte.

- **"Estudo de caso" inventado:** de 20 para 5, somando as 9 combinações.
- **Fonte dos dados:** a revocação dos obrigatórios subiu (9b `sem_rag` 13 → 16 de 19; 4b `sem_rag` 11 → 17), menos no 9b `hibrido`, parado em 12.
- **Formato do 4b:** palavras por metodologia de 6,2 para 2,5; itens exatos de 37% para 79–88%.
- **Temáticas:** a regra "sem lugar nem instituição" não mudou nada mensurável (margem e acerto@1 iguais ou melhores).
- O 2b continua copiando frase e escrevendo temáticas de ~20 palavras: é o fraco de verdade.

### 5.4 Defeito na busca `hibrido` e correção

**O que foi achado:** o que sobrou de erro no 9b vinha dos verbetes que a busca `hibrido` oferecia. Os sinais da base passavam por uma limpeza que tira preposições e corta as palavras em 6 letras, então "no município de" virava "munici" e "em uma instituição", "instit". Quase todo resumo de um programa de estudos territoriais cita município ou instituição, e o verbete de estudo de caso ia para o modelo em **10 das 20** dissertações (no `denso`, em 1). Dos métodos da base que o 9b inventou no `hibrido`, 13 de 14 (`v1`) estavam entre os verbetes oferecidos.

**Correção** (branch `feature/parte-2-correcao-busca`): sinal de várias palavras só casa como expressão inteira; `estudo_de_caso` perde os sinais de lugar e instituição. Depois dela, o verbete vai em **1 das 20**.

**Rodada 3** (`v2`, `hibrido`, busca corrigida × antiga, F1 pareado [IC95], ganhou/perdeu/empatou):

| Modelo | Diferença | F1 antes → depois |
| --- | --- | --- |
| 9b | +0,055 [+0,000; +0,146], 3/0/17 | 0,695 → 0,750 |
| 4b | −0,032 [−0,131; +0,045], 3/2/15 | sem efeito |
| 2b | −0,051 [−0,131; +0,013], 2/4/14 | sem efeito |

A correção ajudou o modelo que era puxado pelos verbetes, e ele não perdeu em nenhuma dissertação. Métodos fora da base achados pelo 9b: de 12 para 18 de 27, porque os verbetes deixaram de prendê-lo à base. Temáticas: nada muda (±0,002). Mesmo corrigido, o `hibrido` continua o pior para o 9b (0,750, contra 0,825 do `sem_rag` e 0,789 do `denso`).

### 5.5 Prompt `v3` e versão final

O `v3` mexeu só nos padrões que sobraram no `v2` com a busca corrigida: nome técnico no lugar da descrição ("exame de prontuários" é pesquisa documental); a abordagem sempre como "Abordagem quantitativa" etc.; plataformas e bancos de outras instituições como dados secundários; pesquisa bibliográfica só quando o resumo diz que fez revisão; postura, objeto e referencial teórico não são metodologia. Foi commitado antes de rodar.

**Critério** (escrito no PROGRESSO.md e implementado em `notebooks/parte5_criterio_v3.py` antes de qualquer resposta do `v3` existir): fica o `v3` se a média do F1 pareado (v3 − v2) nas 9 combinações for ≥ 0, e nenhuma destas disparar: alguma combinação com IC95 inteiro abaixo de zero; acerto@1 médio mais de 0,05 abaixo do `v2`; itens exatos médios abaixo do `v2`. A linha de base é o `v2` de `sem_rag` e `denso` e o `hibrido` com a busca corrigida.

**Veredito: fica o `v3`.**

| | `v2` | `v3` |
| --- | --- | --- |
| F1 médio (9 combinações) | 0,7425 | 0,7477 |
| F1 pareado médio (v3 − v2) | | +0,0052 |
| Acerto@1 das temáticas | 0,8333 | 0,8333 |
| Itens exatos | 0,7797 | 0,7804 |
| Combinação com IC95 inteiro abaixo de zero | | nenhuma |

**A margem é mínima e precisa ir junto com o veredito.** +0,005 está dentro do ruído de 20 dissertações (uns ±0,03), e a trava dos itens exatos passou por 0,0007, menos de um item. A frase certa é "o `v3` não piorou o conjunto e melhorou o 9b", não "o `v3` é melhor".

**Por combinação** (F1 `v2` → `v3`, diferença [IC95], ganhou/perdeu/empatou):

| | `sem_rag` | `denso` | `hibrido` |
| --- | --- | --- | --- |
| 2b | 0,657 → 0,637; −0,021 [−0,072; +0,029]; 3/5/12 | 0,589 → 0,600; +0,010 [−0,093; +0,142]; 3/3/14 | 0,622 → 0,634; +0,013 [−0,056; +0,099]; 3/3/14 |
| 4b | 0,828 → 0,789; −0,039 [−0,103; +0,021]; 4/5/11 | 0,816 → 0,776; −0,040 [−0,126; +0,046]; 3/6/11 | 0,807 → 0,810; +0,003 [−0,085; +0,088]; 3/3/14 |
| 9b | 0,825 → 0,849; +0,024 [−0,005; +0,064]; 5/2/13 | 0,789 → 0,808; +0,019 [−0,047; +0,098]; 3/4/13 | 0,750 → 0,828; +0,078 [+0,009; +0,165]; 6/1/13 |

O `v3` serve ao 9b (melhora nas três técnicas, e no `hibrido` com o intervalo acima de zero) e não ao 4b (−0,04 no `sem_rag` e no `denso`, dentro do ruído). Com o `v3`, a escada fica 2b < 4b < 9b também em qualidade; no `v2`, o 4b e o 9b empatavam.

**O que sobrou, registrado como limitação** (não virou `v4`, pela regra combinada):

- **4b:** não absorveu as regras novas. Itens descritivos subiram de 18 para 24 ("Abordagem interdisciplinar", "Análise quantitativa", "Banco de dados"); dados secundários continuam faltando em 9 de 12 casos; e passou a deixar de fora mais métodos fora da base (de 20 para 28 de 81), o que explica o −0,04.
- **9b:** absorveu (itens descritivos de 14 para 6; dados secundários faltando em 3 de 12; pesquisa bibliográfica sem base quase sumiu). Sobra pesquisa documental aplicada demais (2 a 4 vezes por execução) e análise de conteúdo ainda como padrão (1 ou 2).
- **Os dois:** entrevista promovida a semiestruturada só no `hibrido` (1 ou 2 vezes), porque esse verbete é oferecido em 8 das 20; e instrumentos ou técnicas com nome próprio fora da base seguem sendo o limite dos modelos.
- **2b:** fora do alcance do prompt; continua copiando frase e escrevendo temáticas longas.

### 5.6 Execução nas 59 (Parte 4)

Depois de fixados o prompt `v3` e a base (tag `v1-fixado`), a ferramenta rodou nas 59 dissertações com os 3 modelos e as 3 técnicas: `python -m src.pipeline --todos`. Nada foi ajustado depois de ver o resultado.

| Modelo | Tempo por dissertação | 59 dissertações, por técnica | Metodologias por resposta | Erros / 2ª tentativa | Campos sem evidência |
| --- | --- | --- | --- | --- | --- |
| qwen3.5:2b | 1,6–1,7 s | ~1,7 min | 1,6–1,7 | 0 / 0 | 1 (de 641) |
| qwen3.5:4b | 3,6–3,7 s (6,4 s no `denso`) | 3,5–6,3 min | 3,4–3,7 | 0 / 0 | 3 (de 980) |
| qwen3.5:9b | 4,8–4,9 s | ~4,8 min | 3,6–3,8 | 0 / 0 | 0 (de 1.009) |

São 531 respostas (59 × 9) e 2.630 campos; 4 sem evidência.

Nenhuma resposta saiu como "Não informado no resumo". O 4b no `denso` marcou 6,4 s de média, mas a mediana é 4,3 s: a diferença vem de 5 dissertações consecutivas na fila (a pior com 61,9 s), sem repetição e com saída de tamanho normal, e as mesmas levaram de 2 a 5 s nas outras técnicas. Aponta para um episódio passageiro da máquina, não do modelo nem do texto; sem causa confirmada.

**Indicadores sem gabarito** (Parte 5, `data/metricas/corpus/`). Não há referência para as 59, então estes indicadores medem a forma e a estabilidade das respostas, não o acerto.

- **A forma nas 59 é a mesma das 20.** Medida com a mesma régua da calibração (vocabulário só da base), nenhum indicador varia mais que uns 5 pontos de um conjunto para o outro. Não há sinal de que o prompt ajustado nas 20 escreva pior fora delas.
- **Termo da base e tamanho das temáticas.** O 9b e o 4b escrevem de 65% a 72% dos itens de metodologia como termo da base; o 2b, cerca de metade. As temáticas têm 4 a 5 palavras no 9b, 6 a 8 no 4b e 17 a 19 no 2b.
- **Eixos cobertos.** A cobertura dos quatro eixos (abordagem, procedimento, coleta e análise) é de 2,1 a 2,3 no 4b e no 9b e de 1,2 a 1,5 no 2b. É um piso, porque método de fora da base não tem eixo conhecido.
- **O modelo pesa mais que a técnica na concordância.** O mesmo modelo com técnicas diferentes concorda 0,68 (4b) e 0,70 (9b) nas metodologias (Jaccard), e o 4b com o 9b, na mesma técnica, 0,67; com o 2b, a concordância cai para cerca de 0,4. Nas temáticas, a similaridade entre execuções vai de 0,90 a 0,97, mais alta entre técnicas do mesmo modelo (0,97) do que entre modelos (0,90 a 0,94).
- **Dissertações estáveis e instáveis.** Por dissertação, a mediana do Jaccard nos 36 pares de execuções é 0,50: 19 das 59 têm metodologias estáveis (acima de 0,6) e 10 são instáveis (abaixo de 0,3). Essas 10 são as que mais pedem conferência humana; estão por dissertação em `data/metricas/corpus/comparacao.json`.

**Concordância alta não é acerto**, porque dois modelos podem errar igual. Estes números dizem que a ferramenta roda de ponta a ponta, sem falha, quanto custa e onde ela hesita — não se as respostas estão certas. A qualidade nas 59 só se mede quando chegarem as respostas da análise manual (Parte 5, tarefas 7 a 9).

**Qual planilha os analistas vão consultar** na análise com a ferramenta é decisão do grupo (seção 12 do planejamento). Na calibração, o 9b com o `v3` teve o melhor F1 nas três técnicas, mas escolher pela execução que mais concordar com a análise manual empurraria a nova análise na direção da antiga.

## 6. Onde está cada coisa

| Caminho | O que é |
| --- | --- |
| `data/sugestoes/<modelo>__<técnica>__v3/respostas.xlsx` | **As planilhas das 59**: abas `respostas` (as 6 colunas), `detalhes` (evidência como texto da frase) e `execucao`. Com `respostas.json` e `execucao.json` ao lado |
| `data/sugestoes/calibracao/<modelo>__<técnica>__<prompt>[__sufixo]/respostas.json` | As respostas de cada rodada de calibração, no formato `RespostaIA` (com a saída bruta do modelo); as do `v3` também têm a planilha |
| `.../execucao.json` | Modelo e digest, prompt e sha256, sha256 da base e da busca (da rodada 3 em diante), parâmetros, máquina, versão do Ollama, tempo e tentativas por dissertação |
| `src/prompts/v1.txt`, `v2.txt`… | Cada versão do prompt, guardada sem alteração |
| `notebooks/parte3_calibracao.py` | O script que roda a calibração (não tem opção para as 59, de propósito) |
| `src/comparar.py`, `notebooks/parte5_diagnosticos.py`, `notebooks/parte5_criterio_v3.py` | As métricas, os diagnósticos e o critério do `v3` (Parte 5) |
| `data/metricas/calibracao/rodada1` a `rodada4/` | As métricas de cada rodada de calibração, em JSON (e `comparacao.xlsx`, com gráficos). O `origem.json` de cada uma traz o sha256 das respostas medidas, da régua, do prompt, da base e da busca |
| `data/metricas/corpus/` | Os indicadores sem gabarito das 9 execuções nas 59: `comparacao.json`/`.xlsx` (com concordância e gráficos), um relatório por execução e o `origem.json` |
| `src/relatorio_excel.py` | Gera os `comparacao.xlsx` a partir das métricas já gravadas (Parte 5) |

**Rodadas:** 1 = `v1` (5 modelos, `hibrido`; e os 3 Qwen3.5 em `sem_rag` e `denso`); 2 = `v2` (Qwen3.5, 3 técnicas); 3 = `v2` no `hibrido` com a busca corrigida (pastas `__busca-corrigida`); 4 = `v3` (Qwen3.5, 3 técnicas, busca corrigida).

A referência de IA usada nas métricas **ainda não está no repositório**: se o grupo for escrever o gabarito humano da calibração, quem ler a referência antes escreveria influenciado.

## 7. Limitações

- **20 dissertações.** Os intervalos de confiança são largos; diferenças de F1 abaixo de ~0,05 podem ser ruído.
- **A referência é de uma IA, não do grupo.** Os ajustes do prompt foram medidos contra ela. Quando existir o gabarito humano da calibração, `v1`, `v2` e `v3` devem ser medidos contra ele também: um ganho que só aparece na referência de IA foi ajuste ao estilo dela.
- **O ganho do `v3` na calibração tende a sair otimista.** Os exemplos escritos no prompt são inventados, mas as regras novas do `v3` (plataformas como dados secundários, pesquisa bibliográfica só com revisão declarada, postura e objeto não são método) nasceram de erros vistos nas 20, e as categorias que elas citam aparecem no texto da calibração. O teste de verdade é nas 59, e contra o gabarito humano. O tamanho do risco: o `v2` e o `v3` foram escritos depois de ver duas vezes os erros medidos contra a mesma referência, e essa régua tem um autor só (a IA). Sem o gabarito humano, o número do `v3` quer dizer "melhor que o `v2` nesta referência", não "melhor".
- **O reconhecimento de termos da avaliação mudou depois da rodada 1** (passou a achar método dentro de frase). A mudança valeu igual para todos os modelos, e a referência não mudou.
- **Temáticas com lugar:** o `v2` tira lugar e instituição das temáticas; falta o grupo confirmar se é assim que vocês escreveram no Forms.
- **Sugestões para a base (Parte 2), não aplicadas** para não mudar a régua no meio da comparação: "revisão teórica" como sinônimo de pesquisa bibliográfica e "análise quantitativa" levando à abordagem quantitativa.
