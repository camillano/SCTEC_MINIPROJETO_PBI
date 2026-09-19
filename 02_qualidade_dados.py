# -*- coding: utf-8 -*-
"""
02 - INVESTIGAÇÃO DE QUALIDADE DOS DADOS (somente leitura, não altera nada)
Consolida os 7 CSVs brutos do BPS e roda uma bateria de checagens:
duplicidades, ausências, inconsistências e valores estranhos.
Saídas:
  - Docs/relatorio_qualidade.md   (relatório com evidências)
  - Dados/Tratados/_consolidado_raw.pkl  (cache p/ a etapa de limpeza)
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
BRUTOS = BASE / 'Dados' / 'Brutos'
TRATADOS = BASE / 'Dados' / 'Tratados'
DOCS = BASE / 'Docs'
TRATADOS.mkdir(parents=True, exist_ok=True)

buf = io.StringIO()
def w(*a):
    line = ' '.join(str(x) for x in a)
    print(line); buf.write(line + '\n')

def BRL(v):
    return f'R$ {v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

# ---------------------------------------------------------------------------
# CONSOLIDAÇÃO (guarda o ano do arquivo de origem)
# ---------------------------------------------------------------------------
frames = []
for f in sorted(BRUTOS.glob('*.csv')):
    d = pd.read_csv(f, sep=';', encoding='utf-8', dtype=str, keep_default_na=True)
    d.columns = [c.strip() for c in d.columns]
    d['_arquivo'] = f.stem
    frames.append(d)
    print(f'lido {f.name}: {len(d):,} linhas, {d.shape[1]-1} colunas')

# checa consistência de colunas entre arquivos
col_sets = {fr['_arquivo'].iloc[0]: set(fr.columns) - {'_arquivo'} for fr in frames}
base_cols = col_sets[list(col_sets)[0]]

df = pd.concat(frames, ignore_index=True)
N = len(df)

w('# Relatório de Qualidade dos Dados — BPS 2020–2026')
w('')
w(f'*Gerado por `SRC/02_qualidade_dados.py`. Base bruta consolidada: {N:,} linhas × {df.shape[1]-1} colunas.*')
w('')

w('## 1. Consistência estrutural entre os 7 arquivos')
todos_iguais = all(s == base_cols for s in col_sets.values())
w(f'- Todos os arquivos têm o mesmo conjunto de colunas? **{"Sim" if todos_iguais else "NÃO"}**')
if not todos_iguais:
    for ano, s in col_sets.items():
        falt = base_cols - s; nova = s - base_cols
        if falt or nova:
            w(f'    - {ano}: faltam {falt or "—"} | extras {nova or "—"}')
w('')

# ---------------------------------------------------------------------------
# Tipagem auxiliar p/ checagens (não sobrescreve df bruto de texto)
# ---------------------------------------------------------------------------
pu = pd.to_numeric(df['vl_preco_unitario'].str.replace(',', '.', regex=False), errors='coerce')
pt = pd.to_numeric(df['vl_preco_total'].str.replace(',', '.', regex=False), errors='coerce')
qt = pd.to_numeric(df['qt_medicamento'].str.replace(',', '.', regex=False), errors='coerce')
dtc = pd.to_datetime(df['dt_compra'], format='%d/%m/%Y', errors='coerce')
dti = pd.to_datetime(df['dt_insercao'], format='%d/%m/%Y', errors='coerce')

# ---------------------------------------------------------------------------
# 2. DUPLICIDADES
# ---------------------------------------------------------------------------
w('## 2. Duplicidades')
full_dup = df.drop(columns='_arquivo').duplicated().sum()
w(f'- Linhas 100% idênticas (todas as colunas): **{full_dup:,}**')

# chave declarada
key_dup = df['co_seq_bps'].duplicated().sum()
w(f'- `co_seq_bps` repetidos (chave declarada): **{key_dup:,}** '
  f'(distintos: {df["co_seq_bps"].nunique():,})')

# duplicidade de negócio: mesma compra lançada 2x com co_seq_bps diferente
bkey = ['cnpj_instituicao', 'co_catmat', 'cnpj_fornecedor', 'dt_compra',
        'qt_medicamento', 'vl_preco_unitario', 'nu_processo_compra']
biz_dup = df.duplicated(subset=bkey, keep=False).sum()
biz_extra = df.duplicated(subset=bkey, keep='first').sum()
w(f'- Possíveis duplicatas de negócio (mesma instituição+item+fornecedor+data+qtd+preço+processo): '
  f'**{biz_dup:,}** linhas em grupos repetidos ({biz_extra:,} excedentes se mantida 1 por grupo)')
w('')

# ---------------------------------------------------------------------------
# 3. AUSÊNCIAS (valores nulos)
# ---------------------------------------------------------------------------
w('## 3. Ausências (valores nulos) por coluna')
w('')
w('| Coluna | Nulos | % |')
w('|---|---:|---:|')
nulos = df.drop(columns='_arquivo').isna().sum().sort_values(ascending=False)
for c, n in nulos.items():
    if n > 0:
        w(f'| `{c}` | {n:,} | {100*n/N:.1f}% |')
w('')
CRITICAS = ['vl_preco_unitario', 'qt_medicamento', 'vl_preco_total', 'dt_compra',
            'co_catmat', 'sg_uf', 'cnpj_fornecedor']
w('**Colunas críticas (não podem faltar):**')
for c in CRITICAS:
    n = df[c].isna().sum()
    w(f'- `{c}`: {n:,} nulos')
w('')

# ---------------------------------------------------------------------------
# 4. INCONSISTÊNCIAS NUMÉRICAS
# ---------------------------------------------------------------------------
w('## 4. Inconsistências numéricas')
def resumo_num(nome, s):
    w(f'- `{nome}`: nulos={s.isna().sum():,} | zeros={(s==0).sum():,} | '
      f'negativos={(s<0).sum():,} | mín={s.min():,.4f} | máx={s.max():,.2f}')
resumo_num('vl_preco_unitario', pu)
resumo_num('vl_preco_total', pt)
resumo_num('qt_medicamento', qt)
w('')

# 4.1 coerência preço_total ≈ qtd × preço_unit
calc = qt * pu
mask_ok = pt.notna() & calc.notna() & (pt != 0)
dif_rel = (pt - calc).abs() / pt.where(mask_ok)
incoer = (dif_rel > 0.01) & mask_ok
w(f'- **Coerência `vl_preco_total` ≈ `qt_medicamento` × `vl_preco_unitario`** '
  f'(tolerância 1%): **{incoer.sum():,}** linhas inconsistentes '
  f'({100*incoer.sum()/mask_ok.sum():.1f}% das checáveis)')
if incoer.sum():
    ex = df.loc[incoer, ['_arquivo','no_pdm','qt_medicamento','vl_preco_unitario','vl_preco_total']].head(5)
    for _, r in ex.iterrows():
        w(f'    - ex: {str(r.no_pdm)[:25]} | qtd={r.qt_medicamento} × unit={r.vl_preco_unitario} '
          f'≠ total={r.vl_preco_total}')
w('')

# ---------------------------------------------------------------------------
# 5. DATAS
# ---------------------------------------------------------------------------
w('## 5. Datas')
w(f'- `dt_compra` inválidas/não parseáveis: {df["dt_compra"].notna().sum()-dtc.notna().sum():,}')
w(f'- `dt_compra` intervalo: {dtc.min().date()} a {dtc.max().date()}')
w(f'- `dt_insercao` nulas: {df["dt_insercao"].isna().sum():,}')
# data de inserção anterior à compra (impossível)
antes = (dti < dtc).sum()
w(f'- `dt_insercao` anterior à `dt_compra` (suspeito): {antes:,}')
# ano da compra diverge do arquivo
ano_arq = df['_arquivo'].astype(int)
div_ano = (dtc.dt.year != ano_arq) & dtc.notna()
w(f'- `dt_compra` com ano diferente do arquivo de origem: {div_ano.sum():,}')
if div_ano.sum():
    vc = dtc[div_ano].dt.year.value_counts().head(6).to_dict()
    w(f'    - anos encontrados nesses casos: {vc}')
w('')

# ---------------------------------------------------------------------------
# 6. GEOGRAFIA
# ---------------------------------------------------------------------------
w('## 6. Geografia (UF)')
UF27 = set('AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split())
presentes = set(df['sg_uf'].dropna().unique())
w(f'- UFs presentes: {len(presentes)} de 27')
w(f'- **UFs ausentes na base:** {sorted(UF27 - presentes) or "nenhuma"}')
w(f'- Valores de UF fora do padrão (não são UF válida): {sorted(presentes - UF27) or "nenhum"}')
w('')

# ---------------------------------------------------------------------------
# 7. VALORES ESTRANHOS / OUTLIERS
# ---------------------------------------------------------------------------
w('## 7. Valores estranhos e outliers')
# outlier por item via IQR (vetorizado: agg + merge)
tmp = pd.DataFrame({'co_catmat': df['co_catmat'].values, 'pu': pu.values})
gg = tmp.groupby('co_catmat')['pu']
st = gg.agg(cnt='count')
qq = gg.quantile([.25, .75]).unstack()
st['q1'] = qq[.25]; st['q3'] = qq[.75]
st['iqr'] = st['q3'] - st['q1']
m = tmp.merge(st[['cnt', 'q1', 'q3', 'iqr']], left_on='co_catmat', right_index=True, how='left')
out_iqr = ((m['cnt'] >= 8) &
           ((m['pu'] < m['q1'] - 3*m['iqr']) | (m['pu'] > m['q3'] + 3*m['iqr']))).values
out_iqr = pd.Series(out_iqr, index=df.index)
w(f'- Outliers de preço por item (IQR×3, itens c/ ≥8 compras): **{out_iqr.sum():,}** ({100*out_iqr.mean():.1f}%)')
# absolutos implausíveis
w(f'- Preço unitário < R$ 0,01 (praticamente zero): {(pu < 0.01).sum():,}')
w(f'- Preço unitário > R$ 100.000 (implausível p/ unidade): {(pu > 100000).sum():,}')
w(f'- Quantidade > 100 milhões de unidades (suspeita): {(qt > 1e8).sum():,}')
w('')
w('**As 10 maiores linhas por `vl_preco_total` (prováveis erros de lançamento):**')
w('')
w('| arquivo | UF | item | qtd | preço unit. | preço total |')
w('|---|---|---|---:|---:|---:|')
top = pt.nlargest(10)
for i in top.index:
    r = df.loc[i]
    w(f'| {r._arquivo} | {r.sg_uf} | {str(r.no_pdm)[:22]} | {qt[i]:,.0f} | {BRL(pu[i])} | {BRL(pt[i])} |')
w('')
w('**As 5 menores linhas por preço unitário:**')
for i in pu.nsmallest(5).index:
    r = df.loc[i]
    w(f'- {str(r.no_pdm)[:25]} | {r.sg_uf} | unit={BRL(pu[i])} | qtd={qt[i]:,.0f}')
w('')

# ---------------------------------------------------------------------------
# 8. OBSERVAÇÕES CATEGÓRICAS
# ---------------------------------------------------------------------------
w('## 8. Observações sobre categorias')
w(f'- `ds_esfera`: {df["ds_esfera"].value_counts(dropna=False).to_dict()}')
w(f'- `tp_compra`: {df["tp_compra"].value_counts(dropna=False).to_dict()}')
w(f'- `fg_generico` (S/N/nulo): {df["fg_generico"].value_counts(dropna=False).to_dict()}')
w(f'- `no_grupo` distintos: {df["no_grupo"].nunique()} — a maioria dos itens fica em um único grupo,')
w( '  embora medicamentos e materiais convivam sob o mesmo rótulo de grupo (checar `no_classe`).')
w(f'- `no_classe` distintos: {df["no_classe"].nunique()}')
w('')

# cache p/ etapa de limpeza
df.to_pickle(TRATADOS / '_consolidado_raw.pkl')
with open(DOCS / 'relatorio_qualidade.md', 'w', encoding='utf-8') as fh:
    fh.write(buf.getvalue())
print('\n[OK] Docs/relatorio_qualidade.md e cache _consolidado_raw.pkl gravados')
