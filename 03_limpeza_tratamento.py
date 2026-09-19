# -*- coding: utf-8 -*-
"""
03 - LIMPEZA E TRATAMENTO (a partir do cache consolidado)
Aplica os critérios definidos após a investigação de qualidade:
    REMOVE  : duplicatas de negócio + preço unitário < R$ 0,01
    SINALIZA: outliers de preço e de quantidade (IQR×3 por item)
    PREENCHE: ausências categóricas -> "Não informado"
    ENRIQUECE: região, faixa genérico, mês/ano-mês, mediana e razão de preço
Saídas:
  - Dados/Tratados/BPS_20_26_CamillaNascimento.csv
  - Docs/log_limpeza.md  (registro auditável do que foi feito)
"""
import pandas as pd
import numpy as np
from pathlib import Path
import functools, io, sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
print = functools.partial(print, flush=True)

BASE = Path(r'C:\Users\Milla\Documents\Mini_Projeto_BPS')
TRATADOS = BASE / 'Dados' / 'Tratados'
DOCS = BASE / 'Docs'

log = io.StringIO()
def w(*a):
    line = ' '.join(str(x) for x in a); print(line); log.write(line + '\n')

# ---------------------------------------------------------------------------
df = pd.read_pickle(TRATADOS / '_consolidado_raw.pkl').drop(columns=['_arquivo'], errors='ignore')
N0 = len(df)
w('# Log de Limpeza e Tratamento — BPS 2020–2026\n')
w(f'Base bruta consolidada: **{N0:,}** linhas.\n')

# ---------------------------------------------------------------------------
# 1. TIPAGEM
# ---------------------------------------------------------------------------
num_cols = ['vl_preco_unitario', 'vl_preco_total', 'qt_medicamento', 'vl_capacidade']
for c in num_cols:
    df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.', regex=False), errors='coerce')
df['ano_compra'] = pd.to_numeric(df['ano_compra'], errors='coerce').astype('Int64')
df['validade_compra'] = pd.to_numeric(df['validade_compra'], errors='coerce').astype('Int64')
df['dt_compra'] = pd.to_datetime(df['dt_compra'], format='%d/%m/%Y', errors='coerce')
df['dt_insercao'] = pd.to_datetime(df['dt_insercao'], format='%d/%m/%Y', errors='coerce')
for c in df.select_dtypes(include='object').columns:
    df[c] = df[c].str.strip()

# ---------------------------------------------------------------------------
# 2. REMOÇÃO CRITERIOSA
# ---------------------------------------------------------------------------
w('## Remoções (erros inequívocos)\n')

# 2.1 Duplicatas de negócio (mantém a 1ª ocorrência)
bkey = ['cnpj_instituicao', 'co_catmat', 'cnpj_fornecedor', 'dt_compra',
        'qt_medicamento', 'vl_preco_unitario', 'nu_processo_compra']
dup_mask = df.duplicated(subset=bkey, keep='first')
n_dup = int(dup_mask.sum())
df = df[~dup_mask].copy()
w(f'- Duplicatas de negócio removidas (excedentes): **{n_dup:,}**')

# 2.2 Preço unitário abaixo de 1 centavo (não representável em R$ -> erro)
sub = df['vl_preco_unitario'] < 0.01
n_sub = int(sub.sum())
df = df[~sub].copy()
w(f'- Preço unitário < R$ 0,01 removidos: **{n_sub:,}**')

N1 = len(df)
w(f'\n**Total removido: {N0-N1:,} ({100*(N0-N1)/N0:.2f}%). Linhas restantes: {N1:,}.**\n')

# ---------------------------------------------------------------------------
# 3. SINALIZAÇÃO DE OUTLIERS (IQR×3 por item, itens com >=8 compras)
# ---------------------------------------------------------------------------
def flag_iqr(col):
    t = pd.DataFrame({'k': df['co_catmat'].values, 'v': df[col].values})
    g = t.groupby('k')['v']
    st = g.agg(cnt='count')
    q = g.quantile([.25, .75]).unstack()
    st['q1'] = q[.25]; st['q3'] = q[.75]; st['iqr'] = st['q3'] - st['q1']
    m = t.merge(st, left_on='k', right_index=True, how='left')
    fl = (m['cnt'] >= 8) & ((m['v'] < m['q1'] - 3*m['iqr']) | (m['v'] > m['q3'] + 3*m['iqr']))
    return np.where(fl.values, 'Sim', 'Não'), st

df['fl_outlier_preco'], _ = flag_iqr('vl_preco_unitario')
df['fl_outlier_qtd'], _ = flag_iqr('qt_medicamento')
w('## Sinalizações (mantidas na base)\n')
w(f'- `fl_outlier_preco` = "Sim": **{(df.fl_outlier_preco=="Sim").sum():,}**')
w(f'- `fl_outlier_qtd`  = "Sim": **{(df.fl_outlier_qtd=="Sim").sum():,}**\n')

# ---------------------------------------------------------------------------
# 4. ENRIQUECIMENTO
# ---------------------------------------------------------------------------
df['fg_generico_desc'] = df['fg_generico'].map({'S': 'Genérico', 'N': 'Não genérico'}).fillna('Não informado')
regiao = {
    'AC':'Norte','AP':'Norte','AM':'Norte','PA':'Norte','RO':'Norte','RR':'Norte','TO':'Norte',
    'AL':'Nordeste','BA':'Nordeste','CE':'Nordeste','MA':'Nordeste','PB':'Nordeste','PE':'Nordeste','PI':'Nordeste','RN':'Nordeste','SE':'Nordeste',
    'DF':'Centro-Oeste','GO':'Centro-Oeste','MT':'Centro-Oeste','MS':'Centro-Oeste',
    'ES':'Sudeste','MG':'Sudeste','RJ':'Sudeste','SP':'Sudeste',
    'PR':'Sul','RS':'Sul','SC':'Sul',
}
df['ds_regiao'] = df['sg_uf'].map(regiao).fillna('Não informado')
df['mes_compra'] = df['dt_compra'].dt.month
df['ano_mes'] = df['dt_compra'].dt.to_period('M').astype(str)

med = df.groupby('co_catmat')['vl_preco_unitario'].transform('median')
df['mediana_preco_item'] = med.round(4)
df['razao_preco_mediana'] = (df['vl_preco_unitario'] / med).round(3)

# ---------------------------------------------------------------------------
# 5. PREENCHIMENTO DE AUSÊNCIAS (categóricas usadas como filtro/dimensão)
# ---------------------------------------------------------------------------
cat_fill = ['no_pdm','no_grupo','no_classe','modalidade','un_fornecimento',
            'sg_unidade_medida','no_municipio','no_instituicao','registro_anvisa','nu_ata']
for c in cat_fill:
    df[c] = df[c].fillna('Não informado').replace('', 'Não informado')
w('## Preenchimento de ausências\n')
w(f'- Colunas categóricas preenchidas com "Não informado": {", ".join("`"+c+"`" for c in cat_fill)}\n')

# ---------------------------------------------------------------------------
# 6. EXPORTAÇÃO
# ---------------------------------------------------------------------------
ordem = [
    'co_seq_bps','ano_compra','mes_compra','ano_mes','dt_compra','dt_insercao','validade_compra',
    'sg_uf','ds_regiao','no_municipio','ds_esfera','tp_compra','modalidade',
    'cnpj_instituicao','no_instituicao',
    'co_catmat','ds_item','no_pdm','co_pdm','co_grupo','no_grupo','co_classe','no_classe',
    'fg_generico','fg_generico_desc','registro_anvisa',
    'un_fornecimento','sg_unidade_medida','un_medida_capacidade','vl_capacidade',
    'cnpj_fornecedor','no_fornecedor','cnpj_fabricante','no_fabricante',
    'qt_medicamento','vl_preco_unitario','vl_preco_total',
    'mediana_preco_item','razao_preco_mediana','fl_outlier_preco','fl_outlier_qtd',
    'nu_processo_compra','nu_ata','ds_observacao',
]
ordem = [c for c in ordem if c in df.columns]
df = df[ordem]
out = TRATADOS / 'BPS_20_26_CamillaNascimento.csv'

# Formato pt-BR (vírgula decimal) com PRECISÃO POR COLUNA:
# preserva as casas do preço unitário (fonte tem até 4) para os cálculos
# fecharem no Power BI; mantém 2 casas nos valores monetários totais.
precisao = {
    'vl_preco_unitario': 4, 'mediana_preco_item': 4, 'razao_preco_mediana': 3,
    'vl_preco_total': 2, 'vl_capacidade': 2, 'qt_medicamento': 0,
}
def fmt_br(valor, casas):
    if pd.isna(valor):
        return ''
    return (f'%.{casas}f' % valor).replace('.', ',')
for col, casas in precisao.items():
    if col in df.columns:
        df[col] = df[col].map(lambda v, c=casas: fmt_br(v, c))

df.to_csv(out, sep=';', index=False, encoding='utf-8-sig', date_format='%Y-%m-%d')
w('## Resultado final\n')
w(f'- Arquivo: `Dados/Tratados/BPS_20_26_CamillaNascimento.csv`')
w(f'- Linhas: **{len(df):,}** | Colunas: **{len(df.columns)}**')
w('- Formato numérico: separador decimal **vírgula** (pt-BR), com **precisão por coluna**:')
w('  `vl_preco_unitario`/`mediana_preco_item` = 4 casas, `razao_preco_mediana` = 3,')
w('  `vl_preco_total`/`vl_capacidade` = 2, `qt_medicamento` = inteiro.')
w('  Ao importar no Power BI, use **Tipo → usando Localidade → Português (Brasil)** nas colunas numéricas.')

with open(DOCS / 'log_limpeza.md', 'w', encoding='utf-8') as fh:
    fh.write(log.getvalue())
print('\n[OK] CSV tratado e Docs/log_limpeza.md gravados')
