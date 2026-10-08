"""Regra de ouro (decisões C3/C5): a ferramenta nunca lê as respostas da análise manual.

Se lesse, estaria copiando o grupo, e a comparação com a análise manual não mediria nada.
(a) nenhum arquivo das Partes 1 a 4 sequer cita o arquivo; (b) o pipeline inteiro, em modo
mock, não abre nenhum arquivo com esse nome.
"""

import builtins
import io
from pathlib import Path

from src.pipeline import executar

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVOS_DAS_PARTES_1_A_4 = [
    "src/contratos.py", "src/preparar_dados.py", "src/unitarizar.py", "src/indexar.py", "src/recuperar.py",
    "src/sugerir.py", "src/validar.py", "src/pipeline.py", "src/exportar.py", "src/mocks.py",
    "notebooks/parte3_calibracao.py",
]
NOME = "analise" + "_manual"  # montado aqui para este arquivo não se acusar na busca


def test_nenhum_arquivo_das_partes_1_a_4_cita_a_analise_manual():
    citam = [a for a in ARQUIVOS_DAS_PARTES_1_A_4 if NOME in (RAIZ / a).read_text(encoding="utf-8").lower()]
    assert citam == []


def test_pipeline_nao_abre_a_analise_manual(tmp_path, monkeypatch):
    abertos = []
    abrir = io.open

    def espiao(arquivo, *args, **kwargs):
        abertos.append(str(arquivo))
        return abrir(arquivo, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", espiao)
    monkeypatch.setattr(io, "open", espiao)
    for tecnica in ("sem_rag", "denso", "hibrido"):
        executar("mock", tecnica, mock=True, base=tmp_path)
    assert abertos, "o espião não viu nenhum arquivo: o teste não está medindo nada"
    assert [a for a in abertos if NOME in a.lower()] == []
