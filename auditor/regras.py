"""Regras de auditoria. Cada regra é uma função pura: recebe dados e devolve anomalias."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import quantiles
from typing import Dict, List, Optional

from auditor.formatacao import formatar_brl
from auditor.modelos import SEVERIDADES, Anomalia, Transacao


def detectar_valores_invalidos(transacoes: List[Transacao]) -> List[Anomalia]:
    """Valores zerados ou negativos (estorno legítimo ou erro de digitação)."""
    return [
        Anomalia(
            tipo="valor_invalido",
            severidade="media",
            motivo="Valor zerado ou negativo: confirmar se é estorno ou erro de digitação",
            linha=t.linha,
            descricao=t.descricao,
            valor=t.valor,
        )
        for t in transacoes
        if t.valor <= 0
    ]


def detectar_duplicadas(transacoes: List[Transacao]) -> List[Anomalia]:
    """Mesma data, descrição e valor repetidos. A primeira ocorrência é mantida."""
    vistas: Dict[tuple, int] = {}
    anomalias: List[Anomalia] = []
    for t in transacoes:
        chave = (t.data, t.descricao.casefold(), t.valor)
        if chave in vistas:
            anomalias.append(
                Anomalia(
                    tipo="duplicada",
                    severidade="alta",
                    motivo=f"Possível cobrança duplicada (igual à linha {vistas[chave]})",
                    linha=t.linha,
                    descricao=t.descricao,
                    valor=t.valor,
                )
            )
        else:
            vistas[chave] = t.linha
    return anomalias


def detectar_datas_futuras(transacoes: List[Transacao], hoje: date) -> List[Anomalia]:
    """Transações com data posterior a hoje."""
    return [
        Anomalia(
            tipo="data_futura",
            severidade="media",
            motivo=f"Data posterior a {hoje:%d/%m/%Y}",
            linha=t.linha,
            descricao=t.descricao,
            valor=t.valor,
        )
        for t in transacoes
        if t.data > hoje
    ]


def detectar_valores_atipicos(
    transacoes: List[Transacao],
    fator_iqr: float = 1.5,
    minimo_amostras: int = 5,
) -> List[Anomalia]:
    """Valores muito acima do padrão da própria categoria (método IQR de Tukey).

    Limite = Q3 + fator * (Q3 - Q1). Usamos IQR em vez de média e desvio padrão
    porque o próprio valor atípico distorce a média e o desvio, escondendo o problema.
    Categorias com poucas transações são ignoradas: não há amostra para comparar.
    """
    por_categoria: Dict[str, List[Transacao]] = defaultdict(list)
    for t in transacoes:
        if t.valor > 0:
            por_categoria[t.categoria].append(t)

    anomalias: List[Anomalia] = []
    for categoria, itens in por_categoria.items():
        if len(itens) < minimo_amostras:
            continue
        valores = [float(t.valor) for t in itens]
        q1, _, q3 = quantiles(valores, n=4, method="inclusive")
        limite = q3 + fator_iqr * (q3 - q1)
        for t in itens:
            if float(t.valor) > limite:
                teto = formatar_brl(Decimal(str(round(limite, 2))))
                anomalias.append(
                    Anomalia(
                        tipo="valor_atipico",
                        severidade="alta",
                        motivo=f"Muito acima do padrão de '{categoria}' (limite estatístico: {teto})",
                        linha=t.linha,
                        descricao=t.descricao,
                        valor=t.valor,
                    )
                )
    return anomalias


def detectar_limites_excedidos(
    transacoes: List[Transacao], limites: Dict[str, Decimal]
) -> List[Anomalia]:
    """Soma mensal por categoria acima do limite definido pelo usuário."""
    totais: Dict[tuple, Decimal] = defaultdict(Decimal)
    for t in transacoes:
        totais[(t.data.strftime("%Y-%m"), t.categoria)] += t.valor

    anomalias: List[Anomalia] = []
    for (mes, categoria), total in sorted(totais.items()):
        limite = limites.get(categoria)
        if limite is not None and total > limite:
            anomalias.append(
                Anomalia(
                    tipo="limite_excedido",
                    severidade="alta",
                    motivo=(
                        f"'{categoria}' em {mes}: total de {formatar_brl(total)} "
                        f"acima do limite de {formatar_brl(limite)}"
                    ),
                    descricao=categoria,
                    valor=total,
                )
            )
    return anomalias


def auditar(
    transacoes: List[Transacao],
    limites: Optional[Dict[str, Decimal]] = None,
    hoje: Optional[date] = None,
    fator_iqr: float = 1.5,
) -> List[Anomalia]:
    """Executa todas as regras e devolve as anomalias da mais grave para a menos grave."""
    hoje = hoje or date.today()
    anomalias = [
        *detectar_valores_invalidos(transacoes),
        *detectar_duplicadas(transacoes),
        *detectar_datas_futuras(transacoes, hoje),
        *detectar_valores_atipicos(transacoes, fator_iqr=fator_iqr),
        *detectar_limites_excedidos(transacoes, limites or {}),
    ]
    ordem = {severidade: posicao for posicao, severidade in enumerate(SEVERIDADES)}
    sem_linha = 10**9  # anomalias sem linha ficam no fim do seu grupo
    return sorted(
        anomalias,
        key=lambda a: (ordem[a.severidade], a.linha if a.linha is not None else sem_linha, a.tipo),
    )
