from datetime import date
from decimal import Decimal

from auditor.regras import (
    auditar,
    detectar_datas_futuras,
    detectar_duplicadas,
    detectar_limites_excedidos,
    detectar_valores_atipicos,
    detectar_valores_invalidos,
)


def test_valores_invalidos_pega_zero_e_negativo(criar):
    transacoes = [
        criar(2, "2026-10-01", "Ok", "Lazer", "10.00"),
        criar(3, "2026-10-01", "Zero", "Lazer", "0"),
        criar(4, "2026-10-01", "Estorno", "Lazer", "-5.00"),
    ]
    anomalias = detectar_valores_invalidos(transacoes)
    assert [a.linha for a in anomalias] == [3, 4]
    assert {a.tipo for a in anomalias} == {"valor_invalido"}


def test_duplicada_marca_apenas_a_repeticao(criar):
    transacoes = [
        criar(2, "2026-10-21", "Mensalidade academia", "Saúde", "129.90"),
        criar(3, "2026-10-21", "MENSALIDADE ACADEMIA", "Saúde", "129.90"),
        criar(4, "2026-10-22", "Mensalidade academia", "Saúde", "129.90"),  # outro dia: não é duplicada
    ]
    anomalias = detectar_duplicadas(transacoes)
    assert len(anomalias) == 1
    assert anomalias[0].linha == 3
    assert "linha 2" in anomalias[0].motivo


def test_datas_futuras(criar):
    hoje = date(2026, 10, 29)
    transacoes = [
        criar(2, "2026-10-29", "Hoje", "Lazer", "1"),
        criar(3, "2026-10-30", "Amanhã", "Lazer", "1"),
    ]
    anomalias = detectar_datas_futuras(transacoes, hoje)
    assert [a.linha for a in anomalias] == [3]


def test_valor_atipico_e_detectado(criar):
    valores = ["18.50", "19.80", "21.30", "48.90", "52.10", "92.40", "198.70", "276.10", "312.45", "2850.00"]
    transacoes = [criar(i + 2, "2026-10-01", f"Compra {i}", "Alimentação", v) for i, v in enumerate(valores)]
    anomalias = detectar_valores_atipicos(transacoes)
    assert [a.linha for a in anomalias] == [11]  # apenas o 2850.00
    assert anomalias[0].valor == Decimal("2850.00")


def test_valor_atipico_ignora_categoria_com_poucas_amostras(criar):
    transacoes = [criar(i + 2, "2026-10-01", "x", "Lazer", v) for i, v in enumerate(["10", "11", "12", "9999"])]
    assert detectar_valores_atipicos(transacoes) == []


def test_valor_atipico_nao_mistura_categorias(criar):
    transacoes = [criar(i + 2, "2026-10-01", "x", "Lazer", "10") for i in range(6)]
    transacoes += [criar(i + 20, "2026-10-01", "x", "Moradia", "1800") for i in range(6)]
    assert detectar_valores_atipicos(transacoes) == []


def test_valor_atipico_desconsidera_negativos_e_zero(criar):
    transacoes = [criar(i + 2, "2026-10-01", "x", "Lazer", "10") for i in range(6)]
    transacoes.append(criar(9, "2026-10-01", "estorno", "Lazer", "-5000"))
    assert detectar_valores_atipicos(transacoes) == []


def test_limite_excedido_e_calculado_por_mes_e_categoria(criar):
    transacoes = [
        criar(2, "2026-10-01", "a", "Lazer", "300"),
        criar(3, "2026-10-02", "b", "Lazer", "200"),  # outubro: 500 > 400
        criar(4, "2026-11-01", "c", "Lazer", "350"),  # novembro: 350 <= 400
        criar(5, "2026-10-03", "d", "Moradia", "9999"),  # sem limite definido
    ]
    anomalias = detectar_limites_excedidos(transacoes, {"Lazer": Decimal("400")})
    assert len(anomalias) == 1
    assert "2026-10" in anomalias[0].motivo
    assert anomalias[0].valor == Decimal("500")
    assert anomalias[0].linha is None


def test_total_exatamente_no_limite_nao_e_anomalia(criar):
    transacoes = [criar(2, "2026-10-01", "a", "Lazer", "400")]
    assert detectar_limites_excedidos(transacoes, {"Lazer": Decimal("400")}) == []


def test_auditar_ordena_da_mais_grave_para_a_menos_grave(criar):
    transacoes = [
        criar(2, "2026-10-01", "Estorno", "Lazer", "-5"),  # media
        criar(3, "2026-10-02", "Assinatura", "Lazer", "30"),
        criar(4, "2026-10-02", "Assinatura", "Lazer", "30"),  # alta (duplicada)
    ]
    anomalias = auditar(transacoes, hoje=date(2026, 10, 29))
    assert [a.severidade for a in anomalias] == ["alta", "media"]
    assert [a.tipo for a in anomalias] == ["duplicada", "valor_invalido"]


def test_auditar_sem_anomalias(criar):
    transacoes = [criar(2, "2026-10-01", "Padaria", "Alimentação", "10")]
    assert auditar(transacoes, hoje=date(2026, 10, 29)) == []
