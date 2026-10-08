"""Parte 3: roda a geração nas 20 dissertações de calibração e guarda as respostas.

Serve para escolher modelos e ajustar o prompt (tarefas 5.1 e 5.2 do PROGRESSO.md).
Só roda na calibração, de propósito: não existe opção para as 59 aqui (decisão C3).
O comando geral é o pipeline da Parte 4 (python -m src.pipeline); este script só fixa o
corpus na calibração e acrescenta --ids e --sufixo, que o ajuste do prompt usou. Até
07/10/2026 a lógica morava aqui; foi para o src/pipeline.py, que agora a usa nos dois casos.

Uso (na raiz do repositório):
    .venv\\Scripts\\python notebooks/parte3_calibracao.py --modelos qwen3.5:9b-q4_K_M --tecnicas sem_rag hibrido
    ... --versao v2          outra versão do prompt
    ... --ids C001 C002      só algumas dissertações
    ... --sobrescrever       refaz o que já existe (sem isso, retoma de onde parou)
    ... --sufixo busca-corrigida   pasta nova para a mesma versão do prompt com outra busca

Saída, uma pasta por combinação (modelo × técnica × versão do prompt):
    data/sugestoes/calibracao/<modelo>__<tecnica>__<versao>[__sufixo]/
        respostas.json   lista de RespostaIA (dataclasses.asdict), na ordem C001…C020
        execucao.json    máquina, versões, parâmetros, hashes, segundos e tentativas por dissertação
        respostas.xlsx   a planilha (src/exportar.py)
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import config  # noqa: E402
from src.pipeline import executar  # noqa: E402
from src.sugerir import _cliente, verificar_ollama  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modelos", nargs="+", default=list(config.MODELOS_LLM.values()))
    parser.add_argument("--tecnicas", nargs="+", default=list(config.TECNICAS), choices=config.TECNICAS)
    parser.add_argument("--versao", default=config.VERSAO_PROMPT)
    parser.add_argument("--ids", nargs="+", help="só estas dissertações (ex.: C001 C002)")
    parser.add_argument("--sobrescrever", action="store_true")
    parser.add_argument("--sufixo", default="", help="acrescentado ao nome da pasta (ex.: busca-corrigida)")
    args = parser.parse_args()

    cliente = _cliente()
    for modelo in args.modelos:
        verificar_ollama(modelo, cliente)  # para já, com mensagem clara, se faltar Ollama ou modelo
    for modelo in args.modelos:
        for tecnica in args.tecnicas:
            executar(modelo, tecnica, "calibracao", args.versao, args.sobrescrever, args.sufixo, args.ids,
                     cliente=cliente)
        cliente.generate(model=modelo, keep_alive=0)  # libera a placa para o próximo modelo


if __name__ == "__main__":
    main()
