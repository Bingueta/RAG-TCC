"""Contratos entre as partes: o formato dos dados que uma parte entrega para a outra.

Definidos na seção 3.1 de docs/divisao-tarefas.md. Ninguém altera este arquivo sozinho:
qualquer mudança passa por pull request aprovado pelas partes afetadas e é registrada
como decisão em docs/PROGRESSO.md.

Por enquanto só existem os tipos da Parte 1. Os das outras partes entram quando elas
começarem.
"""

from dataclasses import dataclass


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
