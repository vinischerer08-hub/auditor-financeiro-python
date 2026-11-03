from datetime import date
from decimal import Decimal

import pytest

from auditor.modelos import Transacao


@pytest.fixture
def criar():
    """Fábrica de transações para os testes: criar(linha, 'AAAA-MM-DD', desc, categoria, valor)."""

    def _criar(linha, data, descricao, categoria, valor):
        return Transacao(
            linha=linha,
            data=date.fromisoformat(data),
            descricao=descricao,
            categoria=categoria,
            valor=Decimal(str(valor)),
        )

    return _criar
