from contextlib import closing
from datetime import datetime
from decimal import Decimal

import pytest

from auditor import banco
from auditor.modelos import Anomalia


@pytest.mark.parametrize(
    "valor, centavos",
    [("10.00", 1000), ("0.01", 1), ("1234.567", 123457), ("-45.00", -4500), ("0.1", 10)],
)
def test_conversao_para_centavos(valor, centavos):
    assert banco.para_centavos(Decimal(valor)) == centavos


def test_ida_e_volta_dos_centavos():
    assert banco.de_centavos(banco.para_centavos(Decimal("129.90"))) == Decimal("129.90")


def test_salvar_e_recuperar_execucao(criar):
    transacoes = [
        criar(2, "2026-10-01", "Aluguel", "Moradia", "1800.00"),
        criar(3, "2026-10-02", "Padaria", "Alimentação", "18.50"),
        criar(4, "2026-10-03", "Mercado", "Alimentação", "81.50"),
    ]
    anomalias = [
        Anomalia("duplicada", "alta", "teste", linha=3, descricao="Padaria", valor=Decimal("18.50")),
        Anomalia("limite_excedido", "alta", "geral", descricao="Alimentação"),
    ]
    with closing(banco.conectar(":memory:")) as conexao:
        execucao_id = banco.salvar_execucao(
            conexao, "entrada.csv", transacoes, anomalias, datetime(2026, 10, 29, 22, 0, 0)
        )
        execucoes = banco.listar_execucoes(conexao)
        salvas = banco.listar_anomalias(conexao, execucao_id)
        resumo = banco.resumo_por_categoria(conexao, execucao_id)

    assert len(execucoes) == 1
    assert execucoes[0]["total_transacoes"] == 3
    assert execucoes[0]["total_anomalias"] == 2
    assert execucoes[0]["executada_em"] == "2026-10-29T22:00:00"
    assert [a["tipo"] for a in salvas] == ["duplicada", "limite_excedido"]
    assert salvas[1]["linha"] is None and salvas[1]["valor_centavos"] is None
    assert resumo == {"Moradia": Decimal("1800.00"), "Alimentação": Decimal("100.00")}


def test_historico_persiste_entre_conexoes(tmp_path, criar):
    caminho = tmp_path / "auditoria.db"
    transacoes = [criar(2, "2026-10-01", "Aluguel", "Moradia", "1800.00")]
    for _ in range(2):
        with closing(banco.conectar(caminho)) as conexao:
            banco.salvar_execucao(conexao, "entrada.csv", transacoes, [])

    with closing(banco.conectar(caminho)) as conexao:
        execucoes = banco.listar_execucoes(conexao)
    assert [e["id"] for e in execucoes] == [2, 1]  # mais recente primeiro


def test_consulta_com_texto_malicioso_nao_quebra_o_banco(criar):
    """Parâmetros (?) tratam o texto como dado, nunca como SQL."""
    descricao = "x'); DROP TABLE transacoes; --"
    transacoes = [criar(2, "2026-10-01", descricao, "Lazer", "10")]
    with closing(banco.conectar(":memory:")) as conexao:
        execucao_id = banco.salvar_execucao(conexao, "entrada.csv", transacoes, [])
        total = conexao.execute("SELECT COUNT(*) FROM transacoes").fetchone()[0]
        gravada = conexao.execute("SELECT descricao FROM transacoes WHERE execucao_id = ?", (execucao_id,)).fetchone()[0]
    assert total == 1
    assert gravada == descricao
