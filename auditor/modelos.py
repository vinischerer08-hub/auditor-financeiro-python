"""Estruturas de dados usadas em todo o projeto."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

# Ordem importa: da mais grave para a menos grave.
SEVERIDADES = ("alta", "media", "baixa")


@dataclass(frozen=True)
class Transacao:
    """Uma linha válida do arquivo CSV."""

    linha: int
    data: date
    descricao: str
    categoria: str
    valor: Decimal


@dataclass(frozen=True)
class Anomalia:
    """Um indício de problema encontrado por uma regra de auditoria.

    `linha` fica vazio quando a anomalia não pertence a uma única
    transação (por exemplo, limite mensal de uma categoria excedido).
    """

    tipo: str
    severidade: str
    motivo: str
    linha: Optional[int] = None
    descricao: str = ""
    valor: Optional[Decimal] = None
