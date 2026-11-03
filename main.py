"""Linha de comando do Auditor Financeiro.

Exemplos:
    python main.py dados/transacoes_exemplo.csv
    python main.py dados/transacoes_exemplo.csv --limites dados/limites_exemplo.json
    python main.py --historico
"""

from __future__ import annotations

import argparse
import sys
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

from auditor import banco, relatorio
from auditor.leitura import ler_limites, ler_transacoes
from auditor.regras import auditar


def _data_iso(texto: str) -> date:
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"data inválida {texto!r}; use AAAA-MM-DD") from None


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auditor",
        description="Detecta anomalias em transações financeiras de um arquivo CSV.",
    )
    parser.add_argument("arquivo", nargs="?", help="CSV com as colunas: data,descricao,categoria,valor")
    parser.add_argument("--limites", help="JSON com o limite mensal por categoria")
    parser.add_argument("--saida", default="saida", help="pasta dos relatórios (padrão: saida)")
    parser.add_argument("--banco", help="arquivo SQLite (padrão: <saida>/auditoria.db)")
    parser.add_argument("--hoje", type=_data_iso, help="data de referência AAAA-MM-DD (padrão: hoje)")
    parser.add_argument("--historico", action="store_true", help="lista as execuções anteriores e sai")
    return parser


def _mostrar_historico(caminho_banco: Path) -> int:
    if not caminho_banco.exists():
        print("Nenhuma execução registrada ainda.")
        return 0
    with closing(banco.conectar(caminho_banco)) as conexao:
        execucoes = banco.listar_execucoes(conexao)
    if not execucoes:
        print("Nenhuma execução registrada ainda.")
        return 0
    print(f"{'#':>3}  {'Data':<19}  {'Transações':>10}  {'Anomalias':>9}  Arquivo")
    for e in execucoes:
        momento = e["executada_em"].replace("T", " ")
        print(f"{e['id']:>3}  {momento:<19}  {e['total_transacoes']:>10}  {e['total_anomalias']:>9}  {e['arquivo']}")
    return 0


def main(argv=None) -> int:
    parser = criar_parser()
    args = parser.parse_args(argv)

    pasta = Path(args.saida)
    caminho_banco = Path(args.banco) if args.banco else pasta / "auditoria.db"

    if args.historico:
        return _mostrar_historico(caminho_banco)
    if not args.arquivo:
        parser.error("informe o arquivo CSV ou use --historico")

    try:
        transacoes, erros = ler_transacoes(args.arquivo)
        limites = ler_limites(args.limites) if args.limites else {}
    except FileNotFoundError as erro:
        print(f"Erro: arquivo não encontrado: {erro.filename}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 2

    if not transacoes:
        print("Erro: nenhuma transação válida encontrada no arquivo.", file=sys.stderr)
        for erro in erros:
            print(f"  - {erro}", file=sys.stderr)
        return 2

    anomalias = auditar(transacoes, limites, args.hoje or date.today())
    agora = datetime.now()

    pasta.mkdir(parents=True, exist_ok=True)
    with closing(banco.conectar(caminho_banco)) as conexao:
        execucao_id = banco.salvar_execucao(conexao, args.arquivo, transacoes, anomalias, agora)

    texto = relatorio.gerar_texto(args.arquivo, transacoes, anomalias, erros, agora)
    (pasta / "relatorio.txt").write_text(texto, encoding="utf-8")
    relatorio.exportar_anomalias_csv(anomalias, pasta / "anomalias.csv")

    print(texto)
    print(f"Execução #{execucao_id} salva em '{pasta}' (relatorio.txt, anomalias.csv e {caminho_banco.name}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
