import csv
from datetime import datetime
from decimal import Decimal

import pytest

from auditor.formatacao import formatar_brl
from auditor.modelos import Anomalia
from auditor.relatorio import exportar_anomalias_csv, gerar_texto


@pytest.mark.parametrize(
    "valor, esperado",
    [
        ("0", "R$ 0,00"),
        ("5", "R$ 5,00"),
        ("1234.5", "R$ 1.234,50"),
        ("1234567.89", "R$ 1.234.567,89"),
        ("-45", "-R$ 45,00"),
    ],
)
def test_formatar_brl(valor, esperado):
    assert formatar_brl(Decimal(valor)) == esperado


def test_texto_do_relatorio(criar):
    transacoes = [
        criar(2, "2026-10-01", "Aluguel", "Moradia", "1800.00"),
        criar(3, "2026-10-02", "Padaria", "Alimentação", "18.50"),
    ]
    anomalias = [
        Anomalia("duplicada", "alta", "Possível cobrança duplicada", linha=3, descricao="Padaria", valor=Decimal("18.50")),
        Anomalia("limite_excedido", "alta", "Acima do limite", descricao="Moradia"),
    ]
    texto = gerar_texto(
        "entrada.csv", transacoes, anomalias, ["Linha 9: valor inválido: 'abc'"], datetime(2026, 10, 29, 22, 30)
    )

    assert "RELATÓRIO DE AUDITORIA FINANCEIRA" in texto
    assert "entrada.csv" in texto
    assert "29/10/2026 22:30" in texto
    assert "Transações lidas  : 2" in texto
    assert "Anomalias         : 2 (alta: 2, media: 0, baixa: 0)" in texto
    assert "R$ 1.800,00" in texto
    assert "Linha 9: valor inválido" in texto
    assert "[ALTA] Linha 3 | duplicada | Padaria | R$ 18,50" in texto
    assert "[ALTA] Geral | limite_excedido | Moradia" in texto


def test_texto_sem_anomalias(criar):
    texto = gerar_texto(
        "entrada.csv", [criar(2, "2026-10-01", "Padaria", "Alimentação", "10")], [], [], datetime(2026, 10, 29)
    )
    assert "Nenhuma anomalia encontrada." in texto
    assert "LINHAS IGNORADAS" not in texto


def test_exportar_csv_e_ler_de_volta(tmp_path):
    anomalias = [
        Anomalia("duplicada", "alta", "Repetida, com vírgula", linha=3, descricao="Padaria", valor=Decimal("18.50")),
        Anomalia("limite_excedido", "alta", "Geral", descricao="Moradia"),
    ]
    caminho = tmp_path / "anomalias.csv"
    exportar_anomalias_csv(anomalias, caminho)

    with caminho.open(newline="", encoding="utf-8-sig") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    assert len(linhas) == 2
    assert linhas[0]["linha"] == "3" and linhas[0]["valor"] == "18.50"
    assert linhas[0]["motivo"] == "Repetida, com vírgula"
    assert linhas[1]["linha"] == "" and linhas[1]["valor"] == ""
