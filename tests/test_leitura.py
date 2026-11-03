from datetime import date
from decimal import Decimal

import pytest

from auditor.leitura import converter_valor, ler_limites, ler_transacoes

CABECALHO = "data,descricao,categoria,valor\n"


def escrever(tmp_path, conteudo, nome="entrada.csv", encoding="utf-8"):
    caminho = tmp_path / nome
    caminho.write_text(conteudo, encoding=encoding)
    return caminho


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("10", "10"),
        ("1234.56", "1234.56"),
        ("1234,56", "1234.56"),
        ("1.234,56", "1234.56"),
        ("R$ 99,90", "99.90"),
        (" -45.00 ", "-45.00"),
    ],
)
def test_converter_valor_aceita_formatos(texto, esperado):
    assert converter_valor(texto) == Decimal(esperado)


@pytest.mark.parametrize("texto", ["abc", "", "NaN", "Infinity", "12,3,4"])
def test_converter_valor_rejeita_invalidos(texto):
    with pytest.raises(ValueError):
        converter_valor(texto)


def test_le_transacoes_validas(tmp_path):
    caminho = escrever(tmp_path, CABECALHO + "2026-10-01,Aluguel,Moradia,1800.00\n2026-10-02,Padaria,Alimentação,\"18,50\"\n")
    transacoes, erros = ler_transacoes(caminho)

    assert erros == []
    assert len(transacoes) == 2
    assert transacoes[0].data == date(2026, 10, 1)
    assert transacoes[0].valor == Decimal("1800.00")
    assert transacoes[1].valor == Decimal("18.50")
    assert transacoes[1].linha == 3  # linha 1 é o cabeçalho


def test_linhas_com_erro_nao_interrompem_a_leitura(tmp_path):
    conteudo = (
        CABECALHO
        + "2026-10-01,Aluguel,Moradia,1800.00\n"
        + "31/10/2026,Data ruim,Lazer,10.00\n"
        + "2026-10-03,Valor ruim,Lazer,abc\n"
        + "2026-10-04,,Lazer,5.00\n"
        + "2026-10-05,Padaria,Alimentação,12.00\n"
    )
    transacoes, erros = ler_transacoes(escrever(tmp_path, conteudo))

    assert [t.descricao for t in transacoes] == ["Aluguel", "Padaria"]
    assert len(erros) == 3
    assert "Linha 3" in erros[0] and "data inválida" in erros[0]
    assert "Linha 4" in erros[1] and "valor inválido" in erros[1]
    assert "Linha 5" in erros[2] and "descricao" in erros[2]


def test_cabecalho_ignora_maiusculas_e_espacos(tmp_path):
    conteudo = " Data , DESCRICAO ,Categoria,Valor\n2026-10-01,Aluguel,Moradia,1800\n"
    transacoes, erros = ler_transacoes(escrever(tmp_path, conteudo))
    assert erros == [] and len(transacoes) == 1


def test_aceita_bom_do_excel(tmp_path):
    caminho = escrever(tmp_path, CABECALHO + "2026-10-01,Aluguel,Moradia,1800\n", encoding="utf-8-sig")
    transacoes, erros = ler_transacoes(caminho)
    assert erros == [] and len(transacoes) == 1


def test_coluna_ausente_levanta_erro(tmp_path):
    caminho = escrever(tmp_path, "data,descricao,valor\n2026-10-01,Aluguel,1800\n")
    with pytest.raises(ValueError, match="categoria"):
        ler_transacoes(caminho)


def test_arquivo_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        ler_transacoes(tmp_path / "nao_existe.csv")


def test_ler_limites(tmp_path):
    caminho = escrever(tmp_path, '{"Lazer": 400, "Moradia": 2500.5}', nome="limites.json")
    assert ler_limites(caminho) == {"Lazer": Decimal("400"), "Moradia": Decimal("2500.5")}


@pytest.mark.parametrize(
    "conteudo",
    ['{"Lazer": -10}', '{"Lazer": 0}', '{"Lazer": "muito"}', '{"Lazer": true}', "[1, 2, 3]"],
)
def test_ler_limites_invalidos(tmp_path, conteudo):
    caminho = escrever(tmp_path, conteudo, nome="limites.json")
    with pytest.raises(ValueError):
        ler_limites(caminho)
