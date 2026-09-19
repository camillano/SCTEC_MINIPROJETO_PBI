# -*- coding: utf-8 -*-
"""
04 - INSIGHTS a partir da base tratada (Dados/Tratados/BPS_20_26_CamillaNascimento.csv).
Gera Docs/insights.md com números confiáveis (com e sem outliers).
Lê o CSV no formato pt-BR (decimal vírgula).
"""
import pandas as pd
from pathlib import Path
import functools, io, sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
print = functools.partial(print, flush=True)

BASE = Path(r'C:\Users\Milla\Documents\Mini_Projeto_BPS')
PATH = BASE / 'Dados' / 'Tratados' / 'BPS_20_26_CamillaNascimento.csv'

cols = ['ano_compra','sg_uf','ds_regiao','ds_esfera','no_municipio','no_pdm','no_classe',
        'no_fornecedor','fg_generico_desc','qt_medicamento','vl_preco_unitario',
        'vl_preco_total','fl_outlier_preco','fl_outlier_qtd']
df = pd.read_csv(PATH, sep=';', encoding='utf-8-sig', usecols=cols, dtype=str)
# formato pt-BR: vírgula decimal -> float
for c in ['qt_medicamento','vl_preco_unitario','vl_preco_total']:
    df[c] = pd.to_numeric(df[c].str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
                          errors='coerce')

buf = io.StringIO()
def w(*a):
    line = ' '.join(str(x) for x in a); print(line); buf.write(line + '\n')
def BRL(v): return ('R$ %0.2f' % v).replace(',', 'X').replace('.', ',').replace('X', '.')

w('# Insights-chave — BPS 2020–2026 (base tratada)\n')
w(f'- Registros (após limpeza): {len(df):,}')
w(f'- Gasto total: **{BRL(df.vl_preco_total.sum())}**')
w(f'- Preço unitário — média {df.vl_preco_unitario.mean():.2f} | mediana {df.vl_preco_unitario.median():.2f}')
w(f'- Linhas sinalizadas: outlier de preço {int((df.fl_outlier_preco=="Sim").sum()):,} | '
  f'outlier de qtd {int((df.fl_outlier_qtd=="Sim").sum()):,}\n')

def bloco(titulo, col, valor='vl_preco_total', n=10, base=None):
    d = base if base is not None else df
    w(f'## {titulo}')
    g = d.groupby(col)[valor].sum().sort_values(ascending=False).head(n)
    for k, v in g.items(): w(f'- {k}: {BRL(v)}')
    w('')

# --- COM todos os dados ---
bloco('Gasto por esfera', 'ds_esfera')
bloco('Gasto por região', 'ds_regiao')

# --- Rankings CONFIÁVEIS: excluindo outliers de preço e de quantidade ---
dc = df[(df.fl_outlier_preco == 'Não') & (df.fl_outlier_qtd == 'Não')]
w('---')
w(f'# Rankings confiáveis (sem outliers de preço nem de quantidade) — {len(dc):,} linhas')
w(f'- Gasto total (limpo): **{BRL(dc.vl_preco_total.sum())}** '
  f'(vs {BRL(df.vl_preco_total.sum())} com outliers)\n')
bloco('Top 10 UF por gasto (limpo)', 'sg_uf', base=dc)
bloco('Top 10 medicamentos/itens por gasto (limpo)', 'no_pdm', base=dc)
bloco('Top 10 classes por gasto (limpo)', 'no_classe', base=dc)
bloco('Top 10 fornecedores por gasto (limpo)', 'no_fornecedor', base=dc)

with open(BASE / 'Docs' / 'insights.md', 'w', encoding='utf-8') as f:
    f.write(buf.getvalue())
print('\n[OK] Docs/insights.md atualizado')
