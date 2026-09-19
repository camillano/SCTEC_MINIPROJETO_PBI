# Mini-Projeto BPS — Módulo 2 (Visualização de Dados e BI)

Análise das compras públicas de medicamentos e materiais de saúde a partir do
Banco de Preços em Saúde (BPS) — Ministério da Saúde, anos 2020 a 2026,
com dashboard em Power BI.


## 1. Estrutura do projeto

Mini_Projeto_BPS/
├─ Dados/
│  ├─ Brutos/          7 CSVs anuais originais (2020..2026)
│  └─ Tratados/        BPS_20_26_CamillaNascimento.csv  ← base final para o Power BI
├─ SRC/
│  ├─ 01_exploracao_bases.py    exploração inicial
│  ├─ 02_qualidade_dados.py     investigação de qualidade (gera Docs/relatorio_qualidade.md)
│  └─ 03_limpeza_tratamento.py  limpeza + tratamento (gera o CSV e Docs/log_limpeza.md)
├─ Docs/
│  ├─ relatorio_qualidade.md    evidências da investigação
│  ├─ log_limpeza.md            registro auditável do tratamento
│  ├─ dicionario_de_dados.md
│  ├─ roteiro_power_query.md
│  ├─ modelo_e_medidas_dax.md
│  └─ roteiro_dashboard.md
├─ Dashboard/          arquivo .pbix
├─ Notebooks/
└─ Readme.md


## 2. Fonte e granularidade
- Fonte: Banco de Preços em Saúde (BPS) — Ministério da Saúde.
- Período: 01/01/2020 a 27/08/2026.
- Grão: 1 linha = 1 item comprado em uma compra pública (chave `co_seq_bps`).
- Volume bruto: 367.365 registros, 36 colunas, 7 arquivos anuais.


## 3. Análise de Qualidade dos Dados

Investigação completa em `SRC/02_qualidade_dados.py` → `Docs/relatorio_qualidade.md`.
Principais achados:

### 3.1 Estrutura (tudo consistente)
- Os 7 arquivos têm as mesmas 36 colunas.
- `co_seq_bps` é chave 100% única (367.365 valores distintos).
- 0 linhas totalmente idênticas.
- `vl_preco_total` = `qt_medicamento` × `vl_preco_unitario` em 100% das linhas
  → o preço total é totalmente derivado; qualquer erro no total vem de erro no
  preço unitário ou na quantidade.
- O ano da compra bate com o ano do arquivo de origem em **100%** dos casos.

### 3.2 Duplicidades
| Tipo | Qtd |
|---|---:|
| Linhas 100% idênticas | 0 |
| `co_seq_bps` repetidos | 0 |
| Duplicatas de negócio** (mesma instituição + item + fornecedor + data + qtd + preço + processo, com `co_seq_bps` diferente) | 1.414 linhas em grupos (731 excedentes) |

### 3.3 Ausências (valores nulos)
| Coluna | % nulos | Decisão |
|---|---:|---|
| `nu_ata` | 75,8% | preencher "Não informado" |
| `sg_unidade_medida`, `vl_capacidade` | 63,6% | manter (capacidade é opcional) |
| `registro_anvisa`, `fg_generico` | 48,9% | preencher "Não informado" |
| `ds_observacao` | 15,9% | manter |
| `dt_insercao` | 0,6% | manter |
| `no_grupo`/`no_classe`/`no_pdm`/`co_*` | 0,1% (398) | preencher "Não informado" |
| `no_instituicao` | 285 | preencher "Não informado" |

> # Colunas críticas (preço unitário, quantidade, preço total, data, CATMAT, UF,
> #CNPJ do fornecedor) têm **0 nulos** — nenhuma linha precisou ser descartada por ausência.

### 3.4 Inconsistências e valores estranhos
- Preço unitário < R$ 0,01 (abaixo de 1 centavo, não representável em reais):
  1.119 linhas — ex.: Ácido Fólico, 3.000 unidades a R$ 0,0001. → erro de lançamento.
- Outliers de preço (IQR×3 por item, itens com ≥8 compras): ~15,7 mil linhas.
  Ex.: 1 compra de R$ 22,8 bilhões (Penicilamina) e preço unitário de
  R$ 8,19 milhões (Tezepelumabe).
- Quantidades absurdas: máximo de 4,3 bilhões de unidades numa única compra.
- `dt_insercao` anterior à `dt_compra` em 12 linhas (impossível logicamente).

### 3.5 Observações de cobertura (não são erros, mas limitam a análise)
- 3 UFs ausentes na base: AM, AP e DF — provavelmente não reportaram ao BPS
  neste extrato. Análises geográficas devem citar essa lacuna.
- 92% dos registros são da esfera Municipal, mas o gasto concentra-se na
  esfera Estadual (compras maiores e menos numerosas).
- `no_grupo` tem apenas 4 categorias amplas; a granularidade real de tipo de produto
  está em `no_classe` (16 categorias, ex.: "Drogas e Medicamentos").


## 4. Tratamento aplicado

Executado em `SRC/03_limpeza_tratamento.py` → `Docs/log_limpeza.md`.

### 4.1 Remoções (erros inequívocos) — 1.848 linhas (0,50%)
| Critério | Linhas removidas |
|---|---:|
| Duplicatas de negócio (mantida a 1ª ocorrência) | 731 |
| Preço unitário < R$ 0,01 | 1.117 |
| Total | 1.848 |

### 4.2 Sinalizações (mantidas na base, para filtrar no Power BI)
Optou-se por sinalizar os outliers em vez de removê-los, porque nem todo preço
alto é erro (medicamentos de alto custo são legítimos). Assim nenhum dado válido é
perdido e é possível mostrar o "antes/depois" ao ativar o filtro.
| Coluna criada | "Sim" |
|---|---:|
| `fl_outlier_preco` (IQR×3 por item) | 15.588 |
| `fl_outlier_qtd` (IQR×3 por item) | 34.530 |

### 4.3 Preenchimento de ausências
Categóricas usadas como filtro/dimensão preenchidas com "Não informado":
`no_pdm`, `no_grupo`, `no_classe`, `modalidade`, `un_fornecimento`,
`sg_unidade_medida`, `no_municipio`, `no_instituicao`, `registro_anvisa`, `nu_ata`.

### 4.4 Enriquecimento (colunas novas)
| Coluna | Descrição |
|---|---|
| `ds_regiao` | Região a partir da UF (N/NE/CO/SE/S) |
| `fg_generico_desc` | Genérico / Não genérico / Não informado |
| `mes_compra`, `ano_mes` | Tempo derivado de `dt_compra` |
| `mediana_preco_item` | Mediana do preço unitário do mesmo item (`co_catmat`) |
| `razao_preco_mediana` | `vl_preco_unitario` ÷ mediana do item (>1 = acima da mediana) |
| `fl_outlier_preco`, `fl_outlier_qtd` | Sinalização de outliers |

### 4.5 Formato de saída
- CSV `;`-separado, encoding UTF-8 (com BOM), datas em `AAAA-MM-DD`.
- Números no padrão brasileiro (separador decimal **vírgula**), com **precisão por coluna**:
  `vl_preco_unitario`/`mediana_preco_item` = **4 casas** (precisão da fonte, para os
  cálculos fecharem no Power BI), `razao_preco_mediana` = 3, `vl_preco_total`/`vl_capacidade`
  = 2, `qt_medicamento` = inteiro.
- No Power BI, importar as colunas numéricas com Tipo → usando Localidade →
  Português (Brasil).

### 4.6 Base final
- 365.517 linhas × 44 colunas.


## 5. Como reproduzir
```bash
python SRC/02_qualidade_dados.py     # investigação -> Docs/relatorio_qualidade.md (+ cache)
python SRC/03_limpeza_tratamento.py  # tratamento  -> Dados/Tratados/BPS_20_26_CamillaNascimento.csv
```

## 6. Como usar no Power BI
1. Importe `Dados/Tratados/BPS_20_26_CamillaNascimento.csv` (encoding 65001/UTF-8, separador `;`,
   números em localidade pt-BR). Ou faça o ETL no próprio Power BI seguindo
   `Docs/roteiro_power_query.md`.
2. Crie a tabela Calendário e as medidas de `Docs/modelo_e_medidas_dax.md`.
3. Monte as páginas conforme `Docs/roteiro_dashboard.md`.

## 7. Nota metodológica
Nas análises de preço e nos rankings de gasto, prefira mediana à média e
ofereça o filtro `fl_outlier_preco = "Não"` (e `fl_outlier_qtd = "Não"`). Sem esse
cuidado, poucas linhas com erro de lançamento distorcem os resultados — por exemplo,
a UF líder em gasto muda de PR para SP ao aplicar o filtro.

## 8. Próximos passos (opcional)
- Enriquecimento por API de CNPJ (BrasilAPI/ReceitaWS): complementar razão social,
  município e porte dos ~3.700 fornecedores distintos, respeitando limites de requisição.
