"""Parte 1: testes da normalizar_texto."""

import pytest

from src.preparar_dados import normalizar_texto


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        # quebras de linha (Windows e Linux), tabulações e espaços repetidos
        ("MARLIÉRIA\r\nVIZINHA", "MARLIÉRIA VIZINHA"),
        ("linha um\nlinha dois", "linha um linha dois"),
        ("muitos    espaços\taqui", "muitos espaços aqui"),
        ("  pontas  ", "pontas"),
        # espaço não separável e hífen invisível
        ("Lei n.º 12.318", "Lei n.º 12.318"),
        ("pala­vra", "palavra"),
        # palavra cortada por hífen no fim da linha
        ("investiga-\nção", "investigação"),
        ("coope-\r\nrativa", "cooperativa"),
        ("investiga- \n ção", "investigação"),
        # hífen que NÃO é corte de linha fica como está
        ("NAF- Núcleo", "NAF- Núcleo"),
        ("cirurgião- dentista", "cirurgião- dentista"),
        ("bem-estar", "bem-estar"),
        ("2022-\n2023", "2022- 2023"),
    ],
)
def test_espacos_quebras_e_hifens(entrada, esperado):
    assert normalizar_texto(entrada) == esperado


def test_nao_troca_ordinal_por_letra():
    # O NFKC trocaria "º" por "o" e "ª" por "a"; o NFC usado aqui não.
    assert normalizar_texto("Lei n.º 12.318, 1ª vara") == "Lei n.º 12.318, 1ª vara"


def test_acento_decomposto_vira_um_caractere_so():
    decomposto = "a" + "̃" + "o"  # "ã" escrito como "a" + til separado
    assert normalizar_texto(decomposto) == "ão"


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("\x93Então a gente é o cartógrafo\x94", "“Então a gente é o cartógrafo”"),
        ("Programa Olhos D\x92água", "Programa Olhos D’água"),
        ("olhos d\x91água", "olhos d‘água"),
    ],
)
def test_aspas_do_windows_corrompidas(entrada, esperado):
    assert normalizar_texto(entrada) == esperado


def test_texto_ja_limpo_nao_muda():
    texto = "Trata-se de uma pesquisa qualitativa, segundo Bardin (2016)."
    assert normalizar_texto(texto) == texto
