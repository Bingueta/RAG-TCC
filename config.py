"""Todos os parâmetros do projeto, num único lugar (regra de reprodutibilidade).

Cada parte edita só a sua seção e justifica cada valor num comentário.
Formato e seções: seção 3.7 de docs/divisao-tarefas.md.
"""

from pathlib import Path

# Pasta raiz do repositório: os caminhos abaixo funcionam de qualquer pasta onde o
# comando for rodado.
RAIZ = Path(__file__).resolve().parent

# ===== PARTE 1: dados =====
# Original das 59 dissertações, passado do PDF para JSON pelo grupo. Só leitura.
CAMINHO_ORIGINAL = RAIZ / "data" / "brutos" / "dissertacoes.json"
# Gerado pela Parte 1 a partir do original (com id e palavras-chave em lista).
CAMINHO_CORPUS = RAIZ / "data" / "corpus.json"
# 3 a 5 dissertações de fora das 59, usadas só para ajustar prompt e base. O original vai
# no mesmo formato de dissertacoes.json; o preparado ganha ids C001, C002…
CAMINHO_ORIGINAL_CALIBRACAO = RAIZ / "data" / "brutos" / "calibracao.json"
CAMINHO_CALIBRACAO = RAIZ / "data" / "calibracao" / "corpus_calibracao.json"
# Modelo do spaCy para dividir os resumos em frases. O "sm" (pequeno) basta para achar
# fim de frase em português e roda rápido sem placa de vídeo. Versão fixa no requirements.
MODELO_SPACY = "pt_core_news_sm"

# ===== PARTE 2: base de conhecimento e busca =====
# Base de metodologias que o RAG consulta (v1 feita a partir de manuais; o grupo pode
# trocar por uma versão própria só substituindo o arquivo).
CAMINHO_BASE = RAIZ / "data" / "base_metodologia.json"
# Vetores das frases e dos verbetes, gerados por "python -m src.indexar" (fora do git).
PASTA_INDICES = RAIZ / "data" / "indices"
# Modelo de embedding: multilíngue, bom em português, testado no projeto de referência.
# Exige os prefixos "query: " (consulta) e "passage: " (texto). O "-small" é a alternativa
# se ficar lento; aqui o "-base" roda em ~30 s na CPU.
MODELO_EMBEDDING = "intfloat/multilingual-e5-base"
DISPOSITIVO_EMBEDDING = "cpu"  # a placa de vídeo fica livre para o Ollama
# Técnicas comparadas: sem_rag (linha de base), denso (por sentido), hibrido (sentido + BM25).
TECNICAS = ["sem_rag", "denso", "hibrido"]
# Quantas frases do resumo e quantos verbetes vão para o modelo. 5 frases é o que o projeto
# de referência usava para perguntas factuais; os resumos têm de 5 a 18 frases (mediana 10).
TOP_K_FRASES = 5
TOP_K_VERBETES = 5
# Constante do Reciprocal Rank Fusion: valor padrão da literatura, usado no projeto de referência.
RRF_K = 60
