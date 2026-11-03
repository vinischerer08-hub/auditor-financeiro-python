"""Geração do relatório em texto e da exportação das anomalias em CSV."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List

from auditor.formatacao import formatar_brl
from auditor.modelos import SEVERIDADES, Anomalia, Transacao

LARGURA = 72


def _totais_por_categoria(transacoes: List[Transacao]):
    totais = defaultdict(Decimal)
    quantidades = Counter()
    for t in transacoes:
        totais[t.categoria] += t.valor
        quantidades[t.categoria] += 1
    ordenadas = sorted(totais.items(), key=lambda item: item[1], reverse=True)
    return [(categoria, quantidades[categoria], total) for categoria, total in ordenadas]


def gerar_texto(
    arquivo,
    transacoes: List[Transacao],
    anomalias: List[Anomalia],
    erros_leitura: List[str],
    gerado_em: datetime,
) -> str:
    """Monta o relatório completo como texto puro."""
    por_severidade = Counter(a.severidade for a in anomalias)
    resumo_sev = ", ".join(f"{s}: {por_severidade.get(s, 0)}" for s in SEVERIDADES)

    linhas = [
        "=" * LARGURA,
        " RELATÓRIO DE AUDITORIA FINANCEIRA",
        "=" * LARGURA,
        f"Arquivo analisado : {arquivo}",
        f"Gerado em         : {gerado_em:%d/%m/%Y %H:%M}",
        f"Transações lidas  : {len(transacoes)}",
        f"Linhas com erro   : {len(erros_leitura)}",
        f"Anomalias         : {len(anomalias)} ({resumo_sev})",
        "",
        "RESUMO POR CATEGORIA",
        "-" * LARGURA,
        f"{'Categoria':<20}{'Qtde':>6}{'Total':>18}",
    ]
    for categoria, quantidade, total in _totais_por_categoria(transacoes):
        linhas.append(f"{categoria:<20}{quantidade:>6}{formatar_brl(total):>18}")

    if erros_leitura:
        linhas += ["", "LINHAS IGNORADAS NA LEITURA", "-" * LARGURA]
        linhas += [f"  - {erro}" for erro in erros_leitura]

    linhas += ["", "ANOMALIAS ENCONTRADAS", "-" * LARGURA]
    if not anomalias:
        linhas.append("  Nenhuma anomalia encontrada.")
    for a in anomalias:
        onde = f"Linha {a.linha}" if a.linha is not None else "Geral"
        valor = f" | {formatar_brl(a.valor)}" if a.valor is not None else ""
        linhas.append(f"[{a.severidade.upper()}] {onde} | {a.tipo} | {a.descricao}{valor}")
        linhas.append(f"        {a.motivo}")

    linhas += [
        "",
        "Atenção: anomalias são INDÍCIOS para revisão humana, não conclusões.",
        "=" * LARGURA,
    ]
    return "\n".join(linhas) + "\n"


def exportar_anomalias_csv(anomalias: List[Anomalia], caminho) -> None:
    """Salva as anomalias em CSV (utf-8-sig para o Excel abrir os acentos corretamente)."""
    with Path(caminho).open("w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["severidade", "tipo", "linha", "descricao", "valor", "motivo"])
        for a in anomalias:
            escritor.writerow(
                [
                    a.severidade,
                    a.tipo,
                    "" if a.linha is None else a.linha,
                    a.descricao,
                    "" if a.valor is None else a.valor,
                    a.motivo,
                ]
            )
