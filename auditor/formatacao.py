"""Funções de formatação de valores para exibição."""

from __future__ import annotations

from decimal import Decimal


def formatar_brl(valor: Decimal) -> str:
    """Formata um Decimal como moeda brasileira: R$ 1.234,56."""
    texto = f"{abs(valor):,.2f}"  # ex.: 1,234.56 (padrão americano)
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    prefixo = "-R$ " if valor < 0 else "R$ "
    return prefixo + texto
