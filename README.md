# Auditor Financeiro (Python)

![Testes](https://github.com/vinischerer08-hub/auditor-financeiro-python/actions/workflows/testes.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-green)

Ferramenta de linha de comando que lê um arquivo CSV de transações financeiras, aplica regras de auditoria para encontrar **indícios de erros e fraudes**, guarda o histórico em **SQLite** e gera um **relatório** em texto e em CSV.

Usa apenas a biblioteca padrão do Python: não precisa instalar nada para rodar.

> Projeto de estudo, inspirado nos projetos de auditoria do meu [portfólio](https://github.com/vinischerer08-hub/portfolio-vinicius-scherer-di-giorno). Todos os dados de exemplo são **fictícios**.

## O que ele detecta

| Regra | Severidade | O que procura |
|---|---|---|
| `duplicada` | alta | mesma data, descrição e valor repetidos (possível cobrança em duplicidade) |
| `valor_atipico` | alta | valor muito acima do padrão da própria categoria (método IQR) |
| `limite_excedido` | alta | soma mensal de uma categoria acima do limite definido por você |
| `valor_invalido` | média | valor zerado ou negativo (estorno ou erro de digitação) |
| `data_futura` | média | transação com data posterior à data de referência |

Linhas malformadas (data fora do padrão, valor que não é número, campo vazio) **não derrubam o programa**: elas são listadas no relatório e o restante do arquivo é processado.

## Como rodar

Requisito: Python 3.10 ou superior.

```bash
git clone https://github.com/vinischerer08-hub/auditor-financeiro-python.git
cd auditor-financeiro-python

python main.py dados/transacoes_exemplo.csv --limites dados/limites_exemplo.json
```

Opções:

| Opção | Para que serve |
|---|---|
| `--limites ARQUIVO.json` | limite mensal por categoria (opcional) |
| `--saida PASTA` | onde salvar os resultados (padrão: `saida/`) |
| `--banco ARQUIVO.db` | arquivo SQLite (padrão: `saida/auditoria.db`) |
| `--hoje AAAA-MM-DD` | data de referência para a regra de data futura (padrão: hoje) |
| `--historico` | lista as execuções anteriores gravadas no banco |

## Formato dos arquivos de entrada

**CSV de transações** (colunas obrigatórias, em qualquer ordem):

```csv
data,descricao,categoria,valor
2026-10-01,Aluguel outubro,Moradia,1800.00
2026-10-15,Supermercado,Alimentação,"276,10"
```

- `data` no formato `AAAA-MM-DD`.
- `valor` aceita `1234.56` e também o formato brasileiro `1.234,56` (entre aspas, por causa da vírgula).

**JSON de limites** (limite mensal por categoria):

```json
{ "Alimentação": 1500, "Lazer": 400 }
```

## Exemplo de saída

Resultado real de `python main.py dados/transacoes_exemplo.csv --limites dados/limites_exemplo.json --hoje 2026-10-29`:

```text
========================================================================
 RELATÓRIO DE AUDITORIA FINANCEIRA
========================================================================
Arquivo analisado : dados/transacoes_exemplo.csv
Gerado em         : 29/10/2026 22:57
Transações lidas  : 36
Linhas com erro   : 2
Anomalias         : 7 (alta: 4, media: 3, baixa: 0)

RESUMO POR CATEGORIA
------------------------------------------------------------------------
Categoria             Qtde             Total
Alimentação             10       R$ 3.890,25
Moradia                  3       R$ 2.062,70
Lazer                    8         R$ 622,70
Saúde                    4         R$ 597,10
Educação                 2         R$ 409,00
Transporte               9         R$ 343,90

LINHAS IGNORADAS NA LEITURA
------------------------------------------------------------------------
  - Linha 38: valor inválido: 'abc'
  - Linha 39: data inválida '31/10/2026' (use o formato AAAA-MM-DD)

ANOMALIAS ENCONTRADAS
------------------------------------------------------------------------
[ALTA] Linha 24 | valor_atipico | Supermercado Dia | R$ 2.850,00
        Muito acima do padrão de 'Alimentação' (limite estatístico: R$ 599,58)
[ALTA] Linha 27 | duplicada | Mensalidade academia | R$ 129,90
        Possível cobrança duplicada (igual à linha 26)
[ALTA] Geral | limite_excedido | Alimentação | R$ 3.890,25
        'Alimentação' em 2026-10: total de R$ 3.890,25 acima do limite de R$ 1.500,00
[ALTA] Geral | limite_excedido | Saúde | R$ 597,10
        'Saúde' em 2026-10: total de R$ 597,10 acima do limite de R$ 500,00
[MEDIA] Linha 30 | valor_invalido | Estorno indevido | -R$ 45,00
        Valor zerado ou negativo: confirmar se é estorno ou erro de digitação
[MEDIA] Linha 33 | valor_invalido | Taxa de teste | R$ 0,00
        Valor zerado ou negativo: confirmar se é estorno ou erro de digitação
[MEDIA] Linha 37 | data_futura | Passagem aérea | R$ 280,00
        Data posterior a 29/10/2026

Atenção: anomalias são INDÍCIOS para revisão humana, não conclusões.
========================================================================
```

Cada execução gera na pasta de saída:

- `relatorio.txt`: o relatório acima;
- `anomalias.csv`: as anomalias em formato de planilha (abre direto no Excel);
- `auditoria.db`: banco SQLite com o histórico (tabelas `execucoes`, `transacoes` e `anomalias`).

## Estrutura do projeto

```text
auditor-financeiro-python/
├── main.py                  # linha de comando (argparse)
├── auditor/
│   ├── modelos.py           # dataclasses Transacao e Anomalia
│   ├── leitura.py           # leitura e validação do CSV e do JSON
│   ├── regras.py            # as regras de auditoria (funções puras)
│   ├── banco.py             # persistência em SQLite
│   ├── relatorio.py         # relatório em texto e exportação em CSV
│   └── formatacao.py        # formatação de moeda (R$ 1.234,56)
├── dados/                   # arquivos de exemplo (fictícios)
├── tests/                   # testes automatizados (pytest)
└── .github/workflows/       # integração contínua (GitHub Actions)
```

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Os testes cobrem leitura (incluindo arquivos com erros), cada regra de auditoria, o banco de dados e o programa de ponta a ponta. A cada `push`, o GitHub Actions roda tudo nas versões 3.10 a 3.13 do Python.

## Decisões técnicas

- **`Decimal` em vez de `float` para dinheiro.** `0.1 + 0.2` em `float` não dá `0.3` exato; em auditoria financeira, centavos importam.
- **Valores gravados em centavos (inteiros) no SQLite**, pelo mesmo motivo.
- **Detecção de valores atípicos com IQR, não com média e desvio padrão.** O próprio valor atípico infla a média e o desvio, o que pode esconder o problema; o IQR é resistente a isso. Categorias com menos de 5 transações são ignoradas por falta de amostra.
- **Consultas SQL parametrizadas (`?`)**, nunca texto concatenado, para evitar SQL injection (há um teste para isso).
- **Regras como funções puras** (recebem dados, devolvem anomalias): fáceis de testar e de combinar.
- **Leitura tolerante:** uma linha ruim não impede a análise das demais.

## Limitações

- As regras indicam **suspeitas**, não provam fraude: um valor atípico pode ser legítimo.
- O método IQR depende do tamanho da amostra; com poucos dados por categoria, os resultados são menos confiáveis.
- O CSV precisa seguir o formato descrito acima (datas em `AAAA-MM-DD`).

## Próximos passos

- [ ] Regra de orçamento hierárquico (departamentos e subdepartamentos, com soma recursiva).
- [ ] Alerta automático (e-mail ou Telegram) quando houver anomalia de severidade alta, via automação no n8n.
- [ ] Opção de escolher o fator do IQR pela linha de comando.
- [ ] Importar extratos em outros formatos (por exemplo, OFX).

## Autor

**Vinicius Scherer Di Giorno**, estudante de Análise e Desenvolvimento de Sistemas (UNICID).

[LinkedIn](https://www.linkedin.com/in/vinicius-scherer-di-giorno-81932b332/) · [Portfólio](https://github.com/vinischerer08-hub/portfolio-vinicius-scherer-di-giorno)

## Licença

[MIT](LICENSE)
