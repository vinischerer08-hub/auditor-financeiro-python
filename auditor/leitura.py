"""Leitura e validação dos arquivos de entrada (CSV de transações e JSON de limites)."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Tuple

from auditor.modelos import Transacao

COLUNAS_OBRIGATORIAS = ("data", "descricao", "categoria", "valor")


def converter_valor(texto: str) -> Decimal:
    """Converte texto em Decimal.

    Aceita '1234.56' (ponto decimal) e '1.234,56' (formato brasileiro).
    Regra: se houver vírgula, o ponto é separador de milhar.
    """
    limpo = texto.strip().replace("R$", "").strip()
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(limpo)
    except InvalidOperation:
        raise ValueError(f"valor inválido: {texto!r}") from None
    if not valor.is_finite():  # rejeita NaN e Infinity
        raise ValueError(f"valor inválido: {texto!r}")
    return valor


def _converter_linha(numero: int, registro: dict) -> Transacao:
    campos = {c: (registro.get(c) or "").strip() for c in COLUNAS_OBRIGATORIAS}
    vazios = [c for c, v in campos.items() if not v]
    if vazios:
        raise ValueError(f"campo(s) vazio(s): {', '.join(vazios)}")
    try:
        data = datetime.strptime(campos["data"], "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(
            f"data inválida {campos['data']!r} (use o formato AAAA-MM-DD)"
        ) from None
    return Transacao(
        linha=numero,
        data=data,
        descricao=campos["descricao"],
        categoria=campos["categoria"],
        valor=converter_valor(campos["valor"]),
    )


def ler_transacoes(caminho) -> Tuple[List[Transacao], List[str]]:
    """Lê o CSV e devolve (transações válidas, mensagens de erro).

    Linhas com problema NÃO interrompem a leitura: elas são registradas
    na lista de erros e o restante do arquivo é processado.
    Levanta ValueError se faltar alguma coluna obrigatória.
    """
    transacoes: List[Transacao] = []
    erros: List[str] = []
    # utf-8-sig remove o BOM que o Excel costuma colocar no início do arquivo.
    with Path(caminho).open(newline="", encoding="utf-8-sig") as arquivo:
        leitor = csv.DictReader(arquivo)
        leitor.fieldnames = [c.strip().lower() for c in (leitor.fieldnames or [])]
        faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in leitor.fieldnames]
        if faltando:
            raise ValueError(f"colunas obrigatórias ausentes: {', '.join(faltando)}")
        for numero, registro in enumerate(leitor, start=2):  # linha 1 = cabeçalho
            try:
                transacoes.append(_converter_linha(numero, registro))
            except ValueError as erro:
                erros.append(f"Linha {numero}: {erro}")
    return transacoes, erros


def ler_limites(caminho) -> Dict[str, Decimal]:
    """Lê o JSON {"Categoria": limite_mensal} e devolve valores Decimal."""
    with Path(caminho).open(encoding="utf-8-sig") as arquivo:
        bruto = json.load(arquivo)
    if not isinstance(bruto, dict):
        raise ValueError("o arquivo de limites deve ser um objeto JSON {categoria: valor}")
    limites: Dict[str, Decimal] = {}
    for categoria, valor in bruto.items():
        if isinstance(valor, bool) or not isinstance(valor, (int, float, str)):
            raise ValueError(f"limite de {categoria!r} deve ser um número")
        limite = converter_valor(str(valor))
        if limite <= 0:
            raise ValueError(f"limite de {categoria!r} deve ser maior que zero")
        limites[categoria] = limite
    return limites
