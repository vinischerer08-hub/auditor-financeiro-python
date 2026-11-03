"""Persistência em SQLite: cada execução da auditoria fica registrada no histórico.

Os valores monetários são guardados em CENTAVOS (inteiros) para evitar os erros
de arredondamento de números de ponto flutuante.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional

from auditor.modelos import Anomalia, Transacao

ESQUEMA = """
CREATE TABLE IF NOT EXISTS execucoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    executada_em TEXT NOT NULL,
    arquivo TEXT NOT NULL,
    total_transacoes INTEGER NOT NULL,
    total_anomalias INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execucao_id INTEGER NOT NULL REFERENCES execucoes(id) ON DELETE CASCADE,
    linha INTEGER NOT NULL,
    data TEXT NOT NULL,
    descricao TEXT NOT NULL,
    categoria TEXT NOT NULL,
    valor_centavos INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS anomalias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execucao_id INTEGER NOT NULL REFERENCES execucoes(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,
    severidade TEXT NOT NULL,
    linha INTEGER,
    descricao TEXT NOT NULL,
    motivo TEXT NOT NULL,
    valor_centavos INTEGER
);
"""


def para_centavos(valor: Decimal) -> int:
    """Converte reais (Decimal) em centavos (int), arredondando meio para cima."""
    return int((valor * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def de_centavos(centavos: int) -> Decimal:
    """Converte centavos (int) de volta para reais (Decimal)."""
    return Decimal(centavos) / 100


def conectar(caminho) -> sqlite3.Connection:
    """Abre (ou cria) o banco e garante que as tabelas existem."""
    conexao = sqlite3.connect(str(caminho))
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.executescript(ESQUEMA)
    return conexao


def salvar_execucao(
    conexao: sqlite3.Connection,
    arquivo,
    transacoes: List[Transacao],
    anomalias: List[Anomalia],
    executada_em: Optional[datetime] = None,
) -> int:
    """Grava uma execução completa numa única transação e devolve o id dela.

    Todas as consultas usam parâmetros (?), nunca texto concatenado:
    isso impede SQL injection.
    """
    executada_em = executada_em or datetime.now()
    with conexao:  # confirma (commit) se tudo der certo, desfaz (rollback) se falhar
        cursor = conexao.execute(
            "INSERT INTO execucoes (executada_em, arquivo, total_transacoes, total_anomalias) "
            "VALUES (?, ?, ?, ?)",
            (executada_em.isoformat(timespec="seconds"), str(arquivo), len(transacoes), len(anomalias)),
        )
        execucao_id = cursor.lastrowid
        conexao.executemany(
            "INSERT INTO transacoes (execucao_id, linha, data, descricao, categoria, valor_centavos) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (execucao_id, t.linha, t.data.isoformat(), t.descricao, t.categoria, para_centavos(t.valor))
                for t in transacoes
            ],
        )
        conexao.executemany(
            "INSERT INTO anomalias (execucao_id, tipo, severidade, linha, descricao, motivo, valor_centavos) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    execucao_id,
                    a.tipo,
                    a.severidade,
                    a.linha,
                    a.descricao,
                    a.motivo,
                    None if a.valor is None else para_centavos(a.valor),
                )
                for a in anomalias
            ],
        )
    return execucao_id


def listar_execucoes(conexao: sqlite3.Connection) -> List[sqlite3.Row]:
    """Histórico de execuções, da mais recente para a mais antiga."""
    return conexao.execute("SELECT * FROM execucoes ORDER BY id DESC").fetchall()


def listar_anomalias(conexao: sqlite3.Connection, execucao_id: int) -> List[sqlite3.Row]:
    """Anomalias de uma execução, na ordem em que foram gravadas."""
    return conexao.execute(
        "SELECT * FROM anomalias WHERE execucao_id = ? ORDER BY id", (execucao_id,)
    ).fetchall()


def resumo_por_categoria(conexao: sqlite3.Connection, execucao_id: int) -> Dict[str, Decimal]:
    """Total por categoria de uma execução, calculado pelo próprio SQL."""
    linhas = conexao.execute(
        "SELECT categoria, SUM(valor_centavos) AS total FROM transacoes "
        "WHERE execucao_id = ? GROUP BY categoria ORDER BY total DESC",
        (execucao_id,),
    ).fetchall()
    return {linha["categoria"]: de_centavos(linha["total"]) for linha in linhas}
