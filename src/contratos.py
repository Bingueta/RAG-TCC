"""Contratos entre as partes: o formato dos dados que uma parte entrega para a outra.

Definidos na seção 3.1 de docs/divisao-tarefas.md. Ninguém altera este arquivo sozinho:
qualquer mudança passa por pull request aprovado pelas partes afetadas e é registrada
como decisão em docs/PROGRESSO.md.

Por enquanto existem os tipos das Partes 1 e 2. Os das outras partes entram quando elas
começarem.
"""

from dataclasses import dataclass, field


# ---------- Parte 1 entrega ----------

@dataclass
class Dissertacao:
    id: str                       # "D001"
    titulo: str
    resumo: str
    palavras_chave: list[str]
    ano: int | None = None        # opcional: o original não tem o ano


@dataclass
class Frase:
    id: str                       # "F1", "F2"... a numeração recomeça em cada dissertação
    texto: str


@dataclass
class DissertacaoUnitarizada:
    dissertacao: Dissertacao
    frases: list[Frase]           # na ordem em que aparecem no resumo


# ---------- Parte 2 entrega ----------

@dataclass
class Verbete:
    id: str                       # "entrevista_semiestruturada"
    termo: str                    # "Entrevista semiestruturada"
    eixo: str                     # natureza, objetivos, abordagem, procedimento, coleta ou analise
    definicao: str
    sinais: list[str]             # expressões típicas no resumo: "roteiro de entrevista", "entrevistados"
    sinonimos: list[str]          # outras formas de escrever: "entrevistas semi-estruturadas"


@dataclass
class TrechoRecuperado:
    frase_id: str                 # "F3"
    texto: str
    score: float                  # quanto maior, mais parecido


@dataclass
class Contexto:
    dissertacao_id: str
    tecnica: str                  # sem_rag, denso, hibrido ou hibrido_rerank
    frases_tematicas: list[TrechoRecuperado]
    frases_metodologia: list[TrechoRecuperado]
    verbetes: list[Verbete]
    titulos_parecidos: list[str] = field(default_factory=list)
