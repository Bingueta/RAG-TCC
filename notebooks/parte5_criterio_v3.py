"""Parte 5: aplica o critério do prompt v3, como foi fixado ANTES da rodada.

Texto da decisão (docs/PROGRESSO.md, Parte 3, 2026-10-07):
    fica o v3 se a média do F1 pareado (v3 − v2) nas 9 combinações (3 modelos × 3
    técnicas) for ≥ 0, comparando com o v2 de sem_rag e denso das rodadas antigas e de
    hibrido da rodada __busca-corrigida. Qualquer uma destas derruba o v3: alguma
    combinação com IC95 pareado inteiro abaixo de zero; acerto@1 das temáticas, na
    média, mais de 0,05 abaixo do v2; itens exatos (nome limpo) abaixo do v2.

Este arquivo foi escrito e commitado antes de existir o resultado do v3, para que a
decisão saia de uma conta e não de olhar o número. O híbrido do v2 é o da busca
corrigida: comparar com o antigo daria ao v3 o crédito da correção da busca.

Uso (da raiz do repositório):
    python notebooks/parte5_criterio_v3.py PASTA_SUGESTOES REFERENCIA SAIDA.json
"""

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from src.comparar import (  # noqa: E402
    CodificadorE5, Vocabulario, avaliar_execucao, carregar_referencia, diferenca_pareada,
)
from src.indexar import carregar_base  # noqa: E402

MODELOS = ["qwen3.5-2b-q4_K_M", "qwen3.5-4b-q4_K_M", "qwen3.5-9b-q4_K_M"]
TECNICAS = ["sem_rag", "denso", "hibrido"]
# A régua do v2 para cada técnica (só o híbrido tem a pasta da busca corrigida).
PASTA_V2 = {"sem_rag": "{m}__sem_rag__v2", "denso": "{m}__denso__v2", "hibrido": "{m}__hibrido__v2__busca-corrigida"}
FOLGA_ACERTO_1 = 0.05


def aplicar(pasta: Path, referencias, vocabulario, codificar, nova: str = "v3") -> dict:
    combinacoes, f1_v2, f1_nova = [], [], []
    medidas = {"v2": {"acerto_1": [], "itens_exatos": []}, nova: {"acerto_1": [], "itens_exatos": []}}
    for m in MODELOS:
        for t in TECNICAS:
            pastas = {"v2": pasta / PASTA_V2[t].format(m=m), nova: pasta / f"{m}__{t}__{nova}"}
            relatorios = {v: avaliar_execucao(p, vocabulario, referencias, codificar) for v, p in pastas.items()}
            f1 = {v: {l["dissertacao_id"]: l["f1"] for l in r["contra_referencia"]["por_dissertacao"]}
                  for v, r in relatorios.items()}
            for v, r in relatorios.items():
                medidas[v]["itens_exatos"].append(r["sem_gabarito"]["formato_metodologias"]["itens_exatos"])
                if codificar is not None:
                    medidas[v]["acerto_1"].append(r["contra_referencia"]["tematicas"]["acerto_1"])
            dif = diferenca_pareada(f1[nova], f1["v2"])
            f1_v2.append(mean(f1["v2"].values()))
            f1_nova.append(mean(f1[nova].values()))
            combinacoes.append({"modelo": m, "tecnica": t, "v2": pastas["v2"].name, nova: pastas[nova].name,
                                "f1_v2": f1_v2[-1], f"f1_{nova}": f1_nova[-1], "diferenca_f1": dif})

    principal = mean(c["diferenca_f1"]["media"] for c in combinacoes)
    travas = {"combinacao_com_ic95_abaixo_de_zero":
                  [f'{c["modelo"]}__{c["tecnica"]}' for c in combinacoes if c["diferenca_f1"]["ic95"][1] < 0],
              "itens_exatos": {"v2": mean(medidas["v2"]["itens_exatos"]), nova: mean(medidas[nova]["itens_exatos"])}}
    derrubou = []
    if travas["combinacao_com_ic95_abaixo_de_zero"]:
        derrubou.append("alguma combinação com IC95 pareado inteiro abaixo de zero")
    if travas["itens_exatos"][nova] < travas["itens_exatos"]["v2"]:
        derrubou.append("itens exatos abaixo do v2")
    if codificar is not None:
        travas["acerto_1"] = {"v2": mean(medidas["v2"]["acerto_1"]), nova: mean(medidas[nova]["acerto_1"])}
        if travas["acerto_1"][nova] < travas["acerto_1"]["v2"] - FOLGA_ACERTO_1:
            derrubou.append(f"acerto@1 mais de {FOLGA_ACERTO_1} abaixo do v2")
    else:
        travas["acerto_1"] = "não medido (--sem-embedding): a decisão não vale sem esta trava"
    if principal < 0:
        derrubou.insert(0, "média do F1 pareado abaixo de zero")
    return {"fica": "v2" if derrubou else nova, "motivos": derrubou,
            "principal_media_f1_pareado": principal,
            "f1_medio": {"v2": mean(f1_v2), nova: mean(f1_nova)},
            "travas": travas, "combinacoes": combinacoes}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sugestoes")
    parser.add_argument("referencia")
    parser.add_argument("saida")
    parser.add_argument("--nova", default="v3", help="versão a julgar (outra só para ensaiar o script)")
    parser.add_argument("--sem-embedding", action="store_true", help="só para ensaio: pula a trava do acerto@1")
    args = parser.parse_args()
    vocabulario = Vocabulario(carregar_base(config.CAMINHO_BASE))
    referencias = carregar_referencia(args.referencia, vocabulario)
    resultado = aplicar(Path(args.sugestoes), referencias, vocabulario,
                        None if args.sem_embedding else CodificadorE5(), args.nova)
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: resultado[k] for k in ("fica", "motivos", "principal_media_f1_pareado", "f1_medio", "travas")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
