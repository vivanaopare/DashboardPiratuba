import json
import os
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="23/08/2026 Pedal Piratuba", layout="wide")

SHEET_ID = "1lwExfW6GPS198QuLNfvJN8LzWEvms4_1bgoB-ogNq00"

ABAS = {
    "GERAL": None,
    "LIGHT": 1307686260,
    "EBIKE": 979975317,
    "SPORT FEM": 2081351294,
    "SPORT MAS": 310681045,
    "PRO FEM": 250811187,
    "PRO MAS": 1318274495,
    "R$ 5,00 Doação Bombeiros/APAE": 2109328800,
    "City Tour": 971261230,
    "Almoço Ad. Adulto": 1193796668,
    "Almoço Ad. Infantil": 183066336,
    "5 Choop BERG": 1502844235,
}

# Define quais abas farão parte da totalização no GERAL
CATEGORIAS_GERAL = [
    "LIGHT",
    "EBIKE",
    "SPORT FEM",
    "SPORT MAS",
    "PRO FEM",
    "PRO MAS",
]


@st.cache_data(ttl=60)
def carregar(gid: int) -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    df = pd.read_csv(url, header=1)
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
    df.columns = df.columns.astype(str).str.strip()

    # Remove linhas totalmente vazias ou que contenham apenas espaços em branco
    df = df.dropna(how="all")
    linhas_validas = df.apply(
        lambda row: row.astype(str).str.strip().str.len().sum() > 0, axis=1
    )
    df = df[linhas_validas]

    return df


def encontrar_coluna(df: pd.DataFrame, nomes_possiveis: list):
    for col in df.columns:
        for nome in nomes_possiveis:
            if nome.lower() in col.lower():
                return col
    return None


# --- BOTÕES DE NAVEGAÇÃO POR CATEGORIA ---
categoria = st.segmented_control(
    "Utilize os Filtros:", options=list(ABAS.keys()), default="GERAL"
)

if not categoria:
    categoria = "GERAL"


# --- CARREGAMENTO DOS DADOS ---
if categoria == "GERAL":
    dfs = []
    for nome in CATEGORIAS_GERAL:
        gid = ABAS.get(nome)
        if gid is None:
            continue
        try:
            temp = carregar(gid)
            if not temp.empty:
                temp["Categoria"] = nome
                dfs.append(temp)
        except Exception:
            pass
    df = pd.concat(dfs, ignore_index=True) if len(dfs) > 0 else pd.DataFrame()
else:
    df = carregar(ABAS[categoria])


df.columns = df.columns.str.strip()

# --- TRATAMENTO GLOBAL PARA REMOVER 'None', 'NaN' E VALORES NULOS ---
df = df.fillna("")
df = df.replace(["None", "none", "nan", "NaN"], "")

if not df.empty:
    df = df[df.apply(lambda row: row.astype(str).str.strip().ne("").any(), axis=1)]

col_cidade = encontrar_coluna(df, ["cidade", "municipio"])
col_estado = encontrar_coluna(df, ["uf", "estado"])
col_nome = encontrar_coluna(df, ["nome", "atleta", "inscrito", "participante"])


# --- KPI CONTADOR ---
st.write("")
c1, c2 = st.columns([1, 4])

with c1:
    st.metric("Total de Inscritos", len(df))

st.divider()


# --- BLOCO: TOP 20 CIDADES EM 2 COLUNAS ---
st.subheader("📊 Top 20 Cidades com Mais Inscritos")

if (
    col_cidade
    and col_estado
    and col_cidade in df.columns
    and col_estado in df.columns
):
    dados_barras = df.copy()

    dados_barras[col_cidade] = dados_barras[col_cidade].astype(str).str.strip()
    dados_barras[col_estado] = (
        dados_barras[col_estado].astype(str).str.strip().str.upper()
    )

    filtro_validos = (
        dados_barras[col_cidade].ne("")
        & dados_barras[col_cidade].ne("-")
        & dados_barras[col_estado].ne("")
        & dados_barras[col_estado].ne("-")
    )

    dados_filtrados = dados_barras[filtro_validos].copy()

    dados_filtrados["CidadeUF"] = (
        dados_filtrados[col_cidade].str.upper()
        + " - "
        + dados_filtrados[col_estado]
    )

    dados_top20 = (
        dados_filtrados["CidadeUF"]
        .value_counts()
        .head(20)
        .reset_index()
    )
    dados_top20.columns = ["Cidade", "Quantidade"]

    # Divisão do Top 20 em duas metades (1 a 10 e 11 a 20)
    top_1_10 = dados_top20.iloc[0:10]
    top_11_20 = dados_top20.iloc[10:20]

    col_top1, col_top2 = st.columns(2)

    with col_top1:
        fig1 = px.bar(
            top_1_10,
            x="Quantidade",
            y="Cidade",
            orientation="h",
            text="Quantidade",
            title="Top 1 a 10 Cidades",
        )
        fig1.update_yaxes(autorange="reversed")
        fig1.update_traces(textposition="outside", cliponaxis=False)
        fig1.update_layout(
            yaxis_title="",
            xaxis_title="Inscritos",
            showlegend=False,
            margin=dict(l=10, r=40, t=40, b=10),
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_top2:
        if not top_11_20.empty:
            fig2 = px.bar(
                top_11_20,
                x="Quantidade",
                y="Cidade",
                orientation="h",
                text="Quantidade",
                title="Top 11 a 20 Cidades",
            )
            fig2.update_yaxes(autorange="reversed")
            fig2.update_traces(textposition="outside", cliponaxis=False)
            fig2.update_layout(
                yaxis_title="",
                xaxis_title="Inscritos",
                showlegend=False,
                margin=dict(l=10, r=40, t=40, b=10),
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Não há cidades suficientes para exibir do 11º ao 20º lugar.")
else:
    st.info("Colunas de localidade não encontradas para o gráfico.")


# --- TABELA DE INSCRITOS ---
st.divider()
st.subheader("Inscritos")

styler = df.style.set_table_styles(
    [{"selector": "th", "props": [("font-weight", "bold")]}]
)

st.dataframe(styler, hide_index=True, use_container_width=True)


# --- CONSULTA: PESSOAS EM OUTRAS ABAS QUE NÃO ESTÃO NO GERAL ---
st.write("---")
st.subheader("🔍 Compraram outros ingressos, mas NÃO compraram ingresso do Pedal")

dfs_geral = []
for nome_cat in CATEGORIAS_GERAL:
    gid_cat = ABAS.get(nome_cat)
    if gid_cat is not None:
        try:
            t = carregar(gid_cat)
            if not t.empty:
                dfs_geral.append(t)
        except Exception:
            pass

df_base_geral = (
    pd.concat(dfs_geral, ignore_index=True) if dfs_geral else pd.DataFrame()
)

col_nome_geral = encontrar_coluna(
    df_base_geral, ["nome", "atleta", "inscrito", "participante"]
)

if (
    col_nome_geral
    and col_nome_geral in df_base_geral.columns
    and not df_base_geral.empty
):
    nomes_geral = set(
        df_base_geral[col_nome_geral]
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
    )
    nomes_geral.discard("")

    resultados_ausentes = []

    for nome_aba, gid_aba in ABAS.items():
        if gid_aba is None or nome_aba in CATEGORIAS_GERAL:
            continue

        try:
            df_aba = carregar(gid_aba)
        except Exception:
            continue

        col_nome_aba = encontrar_coluna(
            df_aba, ["nome", "atleta", "inscrito", "participante"]
        )

        if col_nome_aba and col_nome_aba in df_aba.columns:
            for idx, row in df_aba.iterrows():
                nome_pessoa = str(row[col_nome_aba]).strip()
                nome_upper = nome_pessoa.upper()

                if (
                    nome_pessoa
                    and nome_upper not in ["", "NAN", "NONE"]
                    and nome_upper not in nomes_geral
                ):
                    resultados_ausentes.append({
                        "Nome": nome_pessoa,
                        "Ingresso comprado": nome_aba,
                    })

    if resultados_ausentes:
        df_resultado = pd.DataFrame(resultados_ausentes).drop_duplicates()
        st.warning(
            f"**{len(df_resultado)}** pessoa(s) sem inscrição para o pedal:"
        )
        st.dataframe(df_resultado, use_container_width=True, hide_index=True)
    else:
        st.success("🎉 Todos os que compraram extras também estão inscritos no pedal!")
else:
    st.error("Não foi possível carregar a lista base de inscritos no Pedal para validação.")


# --- CONSULTA FINAL: SEGUNDO CICLISTA / DUPLICIDADES ---
st.write("---")
st.subheader("⚠️ Comprou 2 inscrições. Falta indicar os dados do segundo ciclista")

if col_nome and col_nome in df.columns and not df.empty:
    df_duplicados = df.copy()
    df_duplicados["Nome_Normalizado"] = (
        df_duplicados[col_nome].astype(str).str.strip().str.upper()
    )
    
    # Descarta nomes em branco
    df_duplicados = df_duplicados[
        ~df_duplicados["Nome_Normalizado"].isin(["", "NAN", "NONE"])
    ]

    # Identifica registros duplicados
    mascara_duplicados = df_duplicados.duplicated(
        subset=["Nome_Normalizado"], keep=False
    )
    df_dups_encontrados = df_duplicados[mascara_duplicados].sort_values(
        by="Nome_Normalizado"
    )

    if not df_dups_encontrados.empty:
        st.warning("Contate o Ipiratuba Bike para ajustar os dados do outro ciclista.")
        
        # Seleciona colunas principais para exibir
        colunas_exibir = [col_nome]
        if "Categoria" in df_dups_encontrados.columns:
            colunas_exibir.append("Categoria")
        if col_cidade in df_dups_encontrados.columns:
            colunas_exibir.append(col_cidade)
        if col_estado in df_dups_encontrados.columns:
            colunas_exibir.append(col_estado)

        st.dataframe(
            df_dups_encontrados[colunas_exibir],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("🎉 Nenhuma pendência de dados encontrada no filtro selecionado!")
else:
    st.info("Coluna de nomes não identificada para checar pendências.")
