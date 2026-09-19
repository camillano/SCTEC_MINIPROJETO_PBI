#IMPORTANDO ARQUIVOS

import pandas as pd
from pathlib import Path

#Localização da pasta com os arquivos originais
pasta_dados = Path("dados/brutos")

#Arquivos CSV
arquivos = sorted(pasta_dados.glob("*.csv"))

print("Arquivos encontrados:")
for arquivo in arquivos:
    print(arquivo.name)

#Abre o arquivo de 2020
arquivo_2020 = pasta_dados / "2020.csv"

df = pd.read_csv(
    arquivo_2020,
    sep=";",
    encoding="utf-8"
)

print("\nPrimeiras linhas:")
print(df.head())

print("\nColunas:")
print(df.columns.tolist())

print("\nDimensões da base:")
print(df.shape)


#Explorando a base de dados

print("\n" + "=" * 60)
print("COMPARAÇÃO DAS BASES ANUAIS")
print("=" * 60)

bases = {}

for arquivo in arquivos:
    print(f"\nLendo: {arquivo.name}")

    df_temp = pd.read_csv(
        arquivo,
        sep=";",
        encoding="utf-8"
    )

    ano = arquivo.stem
    bases[ano] = df_temp

    print(f"Linhas: {df_temp.shape[0]}")
    print(f"Colunas: {df_temp.shape[1]}")

print("\n" + "=" * 60)
print("COMPARAÇÃO DOS NOMES DAS COLUNAS")
print("=" * 60)

colunas_2020 = set(bases["2020"].columns)

for ano, df_temp in bases.items():
    colunas_ano = set(df_temp.columns)

    faltantes = colunas_2020 - colunas_ano
    novas = colunas_ano - colunas_2020

    print(f"\nAno: {ano}")
    print(f"Colunas: {df_temp.shape[1]}")
    print(f"Faltantes em relação a 2020: {faltantes}")
    print(f"Novas em relação a 2020: {novas}")

#INVESTIGAÇÃO DOS DADOS

    print("\n" + "=" * 60)
print("TIPOS DE DADOS DAS BASES")
print("=" * 60)

for ano, df_temp in bases.items():
    print(f"\nAno: {ano}")
    print(df_temp.dtypes)

#VERIFICAÇÃO DE NULOS

    print("\n" + "=" * 60)
print("INVESTIGAÇÃO DE VALORES NULOS")
print("=" * 60)

for ano, df_temp in bases.items():

    print(f"\nAno: {ano}")

    nulos = df_temp.isnull().sum()

    nulos = nulos[nulos > 0]

    print(nulos)

#VERIFICAR DUPLICIDADE DE REGISTROS

print("\n" + "=" * 60)
print("INVESTIGAÇÃO DE DUPLICIDADES")
print("=" * 60)

for ano, df_temp in bases.items():

    duplicados = df_temp.duplicated().sum()

    print(f"\nAno: {ano}")
    print(f"Registros duplicados: {duplicados}") 


    print("\n" + "=" * 60)
print("INVESTIGAÇÃO DE PREÇOS E QUANTIDADES")
print("=" * 60)

for ano, df_temp in bases.items():

    print(f"\nAno: {ano}")

    print("\nQuantidade de medicamentos:")
    print("Valores nulos:", df_temp["qt_medicamento"].isna().sum())
    print("Valores iguais a zero:", (df_temp["qt_medicamento"] == 0).sum())
    print("Valores negativos:", (df_temp["qt_medicamento"] < 0).sum())
    print("Menor quantidade:", df_temp["qt_medicamento"].min())
    print("Maior quantidade:", df_temp["qt_medicamento"].max())

    print("\nPreço unitário:")
    print("Valores nulos:", df_temp["vl_preco_unitario"].isna().sum())
    print("Valores iguais a zero:", (df_temp["vl_preco_unitario"] == 0).sum())
    print("Valores negativos:", (df_temp["vl_preco_unitario"] < 0).sum())
    print("Menor preço:", df_temp["vl_preco_unitario"].min())
    print("Maior preço:", df_temp["vl_preco_unitario"].max())

    print("\nPreço total:")
    print("Valores nulos:", df_temp["vl_preco_total"].isna().sum())
    print("Valores iguais a zero:", (df_temp["vl_preco_total"] == 0).sum())
    print("Valores negativos:", (df_temp["vl_preco_total"] < 0).sum())
    print("Menor preço total:", df_temp["vl_preco_total"].min())
    print("Maior preço total:", df_temp["vl_preco_total"].max())

#IMPORTANDO TABELAS 2

import pandas as pd
from pathlib import Path

#Configuração de diretórios

pasta_brutos = Path("dados/brutos")
pasta_tratados = Path("dados/tratados")
pasta_tratados.mkdir(parents=True, exist_ok=True)

arquivos = sorted(pasta_brutos.glob("*.csv"))
lista_dfs = []

print("=== INICIANDO CONCATENAÇÃO E TRATAMENTO DE DADOS ===")

for arquivo in arquivos:
    ano = arquivo.stem
    print(f"\nProcessando ano: {ano}...")
    
#1. Leitura com tratamento de encoding

    try:
        df_temp = pd.read_csv(arquivo, sep=";", encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        df_temp = pd.read_csv(arquivo, sep=";", encoding="latin1", low_memory=False)

#2. Padronização de nomes das colunas

    df_temp.columns = df_temp.columns.str.strip().str.lower()
    
#3. Garantir a coluna ano_compra

    if 'ano_compra' not in df_temp.columns:
        df_temp['ano_compra'] = int(ano)
        
    lista_dfs.append(df_temp)

#4. Concatenação (Append) de todas as bases 2020-2026

df_consolidado = pd.concat(lista_dfs, ignore_index=True)
print(f"\nTotal de registros concatenados: {len(df_consolidado)}")

#5. Tratamento de duplicidade

duplicados_qtd = df_consolidado.duplicated().sum()
if duplicados_qtd > 0:
    df_consolidado = df_consolidado.drop_duplicates()
    print(f"Registros duplicados removidos: {duplicados_qtd}")

#6. Recálculo/Validação de vl_preco_total (qt_medicamento * vl_preco_unitario)
#Garante consistência matemática caso haja divergência na fonte pública

if 'qt_medicamento' in df_consolidado.columns and 'vl_preco_unitario' in df_consolidado.columns:
    df_consolidado['vl_preco_total_calculado'] = (
        df_consolidado['qt_medicamento'] * df_consolidado['vl_preco_unitario']
    )

#7. Salvar base unificada 

arquivo_saida = pasta_tratados / "BPS_20_26_CamillaNascimento.csv"
df_consolidado.to_csv(arquivo_saida, index=False, sep=";", encoding="utf-8-sig")

print(f"\n[SUCESSO] Base consolidada salva em: {arquivo_saida}")

