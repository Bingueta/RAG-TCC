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

# ===== PARTE 3: geração com LLM e validação =====
# Ollama rodando na própria máquina (endereço padrão da instalação). Nada sai para a internet.
OLLAMA_HOST = "http://127.0.0.1:11434"
# Os 3 modelos comparados (decisão do grupo: um fraco, um forte e um mais potente). Mesma
# família e mesma compactação (q4_K_M), para que a diferença medida seja o tamanho.
# Máquina: RTX 3060 Ti (8 GB de VRAM), 16 GB de RAM. Medido na calibração (20 de 2022):
# - família: o qwen3.5:9b passou o qwen2.5:7b (F1 das metodologias +0,16) e empatou com o
#   qwen3:8b, com temáticas e formato melhores;
# - escada: o 2b é claramente o fraco (F1 0,40 contra 0,80 do 4b, prompt v1); 4b e 9b
#   empatam em qualidade, então a ordem forte/potente é pelo tamanho;
# - tempo por dissertação: 2b ~1,6 s, 4b ~3,5 s, 9b ~5 s (o 9b fica ~88% na VRAM com o
#   Windows e outros programas abertos).
MODELOS_LLM = {
    "fraco": "qwen3.5:2b-q4_K_M",
    "forte": "qwen3.5:4b-q4_K_M",
    "potente": "qwen3.5:9b-q4_K_M",
}
# Versão do prompt: o arquivo src/prompts/<versão>.txt. Cada ajuste vira um arquivo novo
# (v1, v2…), para que toda execução registre exatamente com que texto rodou.
VERSAO_PROMPT = "v1"
# Temperatura 0 e seed fixa: a mesma dissertação gera sempre a mesma resposta na mesma máquina.
TEMPERATURA = 0
SEED = 42
# Janela de contexto. O padrão do Ollama (2048) estourava no projeto de referência com 5
# passagens; aqui o prompt com o maior resumo da calibração (~3.400 caracteres) + verbetes
# fica bem abaixo de 8192.
NUM_CTX = 8192
# Os Qwen3/3.5 "pensam" antes de responder por padrão. Desligado: o pensamento sai fora do
# JSON, deixa cada resposta várias vezes mais lenta e não é o que os outros modelos fazem.
PENSAR = False
# Quantas vezes pedir a resposta. A segunda tentativa manda o erro de volta ao modelo (com
# temperatura 0, repetir o mesmo pedido daria a mesma resposta quebrada).
TENTATIVAS = 2
# Tempo máximo de uma chamada ao modelo, em segundos. O 9b com parte na RAM é o mais lento.
TEMPO_LIMITE = 300
