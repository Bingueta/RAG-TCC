"""Parte 5: diagnósticos da calibração, as contagens que explicam os números do comparar.

Não é métrica nova. São as contas que levaram às decisões da Parte 3 (regras do prompt
v2, escada de modelos) e da Parte 2 (sinais da base), guardadas para dar para refazer:
- F1 só com reconhecimento exato, sem achar método dentro de frase: separa o conteúdo
  certo do formato limpo (a vantagem do 4b no v1 dependia disso);
- estudo de caso inventado (regra 7 do prompt v2);
- fonte dos dados: pesquisa documental, dados secundários, pesquisa bibliográfica e
  análise documental (regra 8);
- métodos de fora da base achados (requisito 2 da Parte 3);
- com --verbetes: quantas vezes a busca oferece cada verbete e quantos dos métodos da
  base inventados estavam entre os oferecidos (por que o híbrido atrapalhou o 9b).

- com --pares: a diferença pareada entre duas execuções que o comparar não pareia
  sozinho, porque mudam algo fora de modelo, técnica e prompt (ex.: a busca corrigida).

A saída só tem contagens agregadas por execução: nenhuma linha diz qual termo a
referência tem em qual dissertação.

Os verbetes oferecidos dependem do src/recuperar.py da árvore onde a busca roda. Para
medir execuções feitas com outra versão da busca, calcule lá com --gravar-oferecidos e
traga o arquivo com --oferecidos.

Uso (da raiz do repositório):
    python notebooks/parte5_diagnosticos.py PASTA_SUGESTOES REFERENCIA SAIDA.json
        [--verbetes | --oferecidos ARQ.json] [--pares DEPOIS=ANTES ...] [--sem-embedding]
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from src.comparar import (  # noqa: E402
    CodificadorE5, Vocabulario, avaliar_contra_referencia, carregar_referencia, carregar_respostas,
    diferenca_pareada, encontrar_execucoes, metodologias_da_resposta, placar, separar_termos,
)
from src.indexar import carregar_base  # noqa: E402

FONTE_DOS_DADOS = {"pesquisa_documental", "dados_secundarios", "pesquisa_bibliografica", "analise_documental"}


def metodologias_exatas(resposta: dict, vocabulario: Vocabulario) -> set[str]:
    """Como metodologias_da_resposta, mas sem procurar método dentro de frase."""
    ids = set()
    for campo in resposta.get("metodologias") or []:
        if campo.get("status") in ("nao_informado", "erro"):
            continue
        ids.update(vocabulario.reconhecer(t)[0] for t in separar_termos(campo.get("texto", ""), vocabulario))
    return ids


def verbetes_oferecidos() -> dict[str, dict[str, list[str]]]:
    """{técnica: {dissertação: ids dos verbetes}} que a busca da Parte 2 entrega nas 20 da calibração."""
    from src.preparar_dados import carregar_corpus
    from src.recuperar import recuperar
    from src.unitarizar import unitarizar
    corpus = [unitarizar(d) for d in carregar_corpus(config.CAMINHO_CALIBRACAO)]
    return {t: {u.dissertacao.id: [v.id for v in recuperar(u, t).verbetes] for u in corpus}
            for t in ("denso", "hibrido")}


def diagnosticar(pasta: Path, referencias, vocabulario: Vocabulario, oferecidos=None) -> dict:
    respostas = [r for r in carregar_respostas(pasta) if r["dissertacao_id"] in referencias]
    tecnica = respostas[0].get("tecnica") if respostas else None
    c = Counter()
    f1_exato = []
    for r in respostas:
        ref = referencias[r["dissertacao_id"]]
        validos = set(ref.obrigatorios) | set(ref.aceitaveis)
        previstos = set(metodologias_da_resposta(r, vocabulario))
        f1_exato.append(placar(metodologias_exatas(r, vocabulario), set(ref.obrigatorios), set(ref.aceitaveis)).f1)
        if "estudo_de_caso" in previstos:
            c["estudo_de_caso_certo" if "estudo_de_caso" in validos else "estudo_de_caso_inventado"] += 1
        fonte = set(ref.obrigatorios) & FONTE_DOS_DADOS
        c["fonte_obrigatorios"] += len(fonte)
        c["fonte_achados"] += len(fonte & previstos)
        c["fonte_inventados"] += len((previstos & FONTE_DOS_DADOS) - validos)
        fora_da_base = {t for t in ref.obrigatorios if t.startswith("ref:")}
        c["fora_da_base_obrigatorios"] += len(fora_da_base)
        c["fora_da_base_achados"] += len(fora_da_base & previstos)
        # Inventado da base: termo que a base tem, a IA disse e a referência não aceita.
        inventados = {t for t in previstos - validos if not t.startswith(("livre:", "ref:"))}
        c["base_inventados"] += len(inventados)
        if oferecidos is not None:
            # sem_rag não recebe verbete: compara com o que o híbrido teria oferecido (controle).
            lista = oferecidos["hibrido" if tecnica == "sem_rag" else tecnica][r["dissertacao_id"]]
            c["base_inventados_entre_oferecidos"] += len(inventados & set(lista))
    saida = {"execucao": pasta.name, "tecnica": tecnica, "dissertacoes": len(respostas),
             "f1_exato": mean(f1_exato) if f1_exato else None, **dict(sorted(c.items()))}
    if oferecidos is None:
        saida.pop("base_inventados_entre_oferecidos", None)
    return saida


def diferenca_entre(pasta_depois: Path, pasta_antes: Path, referencias, vocabulario, codificar) -> dict:
    """F1 (e, com codificar, similaridade das temáticas) pareado: depois − antes."""
    linhas = {}
    for nome, pasta in (("depois", pasta_depois), ("antes", pasta_antes)):
        av = avaliar_contra_referencia(carregar_respostas(pasta), referencias, vocabulario, codificar)
        linhas[nome] = {l["dissertacao_id"]: l for l in av["por_dissertacao"]}
    saida = {"depois": pasta_depois.name, "antes": pasta_antes.name,
             "f1": diferenca_pareada({k: l["f1"] for k, l in linhas["depois"].items()},
                                     {k: l["f1"] for k, l in linhas["antes"].items()})}
    if codificar is not None:
        saida["similaridade_tematicas"] = diferenca_pareada(
            {k: l["similaridade_tematicas"] for k, l in linhas["depois"].items()},
            {k: l["similaridade_tematicas"] for k, l in linhas["antes"].items()})
    return saida


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sugestoes")
    parser.add_argument("referencia")
    parser.add_argument("saida")
    parser.add_argument("--verbetes", action="store_true", help="roda a busca da Parte 2 desta árvore (carrega o e5)")
    parser.add_argument("--oferecidos", help="verbetes oferecidos já calculados (de --gravar-oferecidos)")
    parser.add_argument("--gravar-oferecidos", help="com --verbetes, grava os verbetes oferecidos neste arquivo")
    parser.add_argument("--pares", nargs="*", default=[], metavar="DEPOIS=ANTES",
                        help="nomes de pastas a parear (depois − antes)")
    parser.add_argument("--sem-embedding", action="store_true", help="nos --pares, pula as temáticas")
    args = parser.parse_args()

    vocabulario = Vocabulario(carregar_base(config.CAMINHO_BASE))
    referencias = carregar_referencia(args.referencia, vocabulario)
    oferecidos = None
    if args.oferecidos:
        oferecidos = json.loads(Path(args.oferecidos).read_text(encoding="utf-8"))
    elif args.verbetes:
        oferecidos = verbetes_oferecidos()
        if args.gravar_oferecidos:
            Path(args.gravar_oferecidos).write_text(json.dumps(oferecidos, ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
    resultado = {"execucoes": [diagnosticar(p, referencias, vocabulario, oferecidos)
                               for p in encontrar_execucoes(args.sugestoes)]}
    if args.pares:
        codificar = None if args.sem_embedding else CodificadorE5()
        resultado["pares"] = [diferenca_entre(Path(args.sugestoes) / d, Path(args.sugestoes) / a,
                                              referencias, vocabulario, codificar)
                              for d, a in (p.split("=", 1) for p in args.pares)]
    if oferecidos is not None:
        resultado["verbetes_oferecidos"] = {
            t: {"estudo_de_caso_em": sum("estudo_de_caso" in x for x in por_id.values()),
                "entrevista_semiestruturada_em": sum("entrevista_semiestruturada" in x for x in por_id.values()),
                "mais_oferecidos": Counter(i for x in por_id.values() for i in x).most_common(10),
                "dissertacoes": len(por_id)}
            for t, por_id in oferecidos.items()}
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=False, indent=1)[:3000])


if __name__ == "__main__":
    main()
