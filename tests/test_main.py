"""Testes de integração: rodam o programa inteiro como o usuário rodaria."""

from pathlib import Path

import pytest

import main

DADOS = Path(__file__).resolve().parent.parent / "dados"
CSV = str(DADOS / "transacoes_exemplo.csv")
LIMITES = str(DADOS / "limites_exemplo.json")


def executar(tmp_path, *extras):
    return main.main([CSV, "--limites", LIMITES, "--saida", str(tmp_path / "saida"), "--hoje", "2026-10-29", *extras])


def test_execucao_completa_com_dados_de_exemplo(tmp_path, capsys):
    assert executar(tmp_path) == 0
    saida = capsys.readouterr().out

    pasta = tmp_path / "saida"
    assert (pasta / "relatorio.txt").exists()
    assert (pasta / "anomalias.csv").exists()
    assert (pasta / "auditoria.db").exists()

    # Os dados de exemplo foram montados para acionar cada regra e cada erro de leitura.
    for tipo in ("duplicada", "valor_atipico", "data_futura", "valor_invalido", "limite_excedido"):
        assert tipo in saida
    assert "Linhas com erro   : 2" in saida


def test_historico_registra_cada_execucao(tmp_path, capsys):
    executar(tmp_path)
    executar(tmp_path)
    capsys.readouterr()

    assert main.main(["--historico", "--saida", str(tmp_path / "saida")]) == 0
    linhas = capsys.readouterr().out.strip().splitlines()
    assert len(linhas) == 3  # cabeçalho + 2 execuções
    assert "transacoes_exemplo.csv" in linhas[1]


def test_historico_sem_banco(tmp_path, capsys):
    assert main.main(["--historico", "--saida", str(tmp_path / "vazio")]) == 0
    assert "Nenhuma execução registrada" in capsys.readouterr().out


def test_arquivo_inexistente_retorna_erro(tmp_path, capsys):
    codigo = main.main([str(tmp_path / "nao_existe.csv"), "--saida", str(tmp_path / "saida")])
    assert codigo == 2
    assert "arquivo não encontrado" in capsys.readouterr().err


def test_csv_sem_coluna_obrigatoria(tmp_path, capsys):
    ruim = tmp_path / "ruim.csv"
    ruim.write_text("data,valor\n2026-10-01,10\n", encoding="utf-8")
    assert main.main([str(ruim), "--saida", str(tmp_path / "saida")]) == 2
    assert "colunas obrigatórias ausentes" in capsys.readouterr().err


def test_csv_sem_nenhuma_linha_valida(tmp_path, capsys):
    ruim = tmp_path / "ruim.csv"
    ruim.write_text("data,descricao,categoria,valor\nontem,x,y,abc\n", encoding="utf-8")
    assert main.main([str(ruim), "--saida", str(tmp_path / "saida")]) == 2
    assert "nenhuma transação válida" in capsys.readouterr().err


def test_sem_argumentos_mostra_ajuda():
    with pytest.raises(SystemExit) as saida:
        main.main([])
    assert saida.value.code == 2


def test_data_de_referencia_invalida():
    with pytest.raises(SystemExit) as saida:
        main.main([CSV, "--hoje", "29/10/2026"])
    assert saida.value.code == 2
