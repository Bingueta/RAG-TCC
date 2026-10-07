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
