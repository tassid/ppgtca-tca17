"""Tela 1: demanda de descargas estimada com dados públicos (parte A)."""
import math
from datetime import date, time, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

import db
import ui

con = st.session_state["con"]
ui.cabecalho(
    "Planejamento da safra",
    "Fontes: IBGE PAM (produção municipal), Deral e Aprosoja MS (colheita 2025/26), "
    "Stamm Junior e Pereira, 2009 (carga por caminhão).",
)

# ---------- parâmetros ----------
cargas = db.ler(con, "SELECT * FROM carga")
cargas["nome"] = cargas["configuracao"].str.split(" ").str[0]
with st.sidebar:
    st.subheader("Parâmetros")
    ano = st.selectbox("Safra base (produção IBGE)", list(range(2024, 2014, -1)), index=0)
    tipo = st.radio("Caminhão", cargas["nome"], index=1,
                    format_func=lambda n: f"{n} ({cargas.loc[cargas['nome'] == n, 'carga_t'].iloc[0]:.2f} t)".replace(".", ","))
    carga_t = float(cargas.loc[cargas["nome"] == tipo, "carga_t"].iloc[0])
    participacao = st.slider(
        "Participação da cooperativa (%)", 0, 100, 100,
        help="Parcela da soja do município recebida pela cooperativa. 100% é o teto.",
    )

dem = db.demanda(con, ano, participacao, carga_t)
r = db.ritmos(con)

with st.container(border=True, key="card_pl1"):
    c1, c2 = st.columns([1, 4])
    uf = c1.segmented_control("UF", ["PR", "MS"], default="PR", selection_mode="single") or "PR"
    d = dem[dem["uf"] == uf].copy()
    muns = c2.multiselect("Municípios", d["municipio"].tolist(), default=d["municipio"].tolist())
    d = d[d["municipio"].isin(muns)]

if participacao == 100:
    st.info("Com participação de 100%, os números são o teto do município, não o recebimento da unidade.")

# ---------- indicadores ----------
rr = r[db.CURVA_DA_UF[uf]]
k1, k2, k3, k4 = st.columns(4)
k1.metric("Caminhões por dia no pico", ui.inteiro(d["caminhoes_dia_pico"].sum()), border=True)
k2.metric("Caminhões por dia na média", ui.inteiro(d["caminhoes_dia_media"].sum()), border=True)
k3.metric("Caminhões por semana no pico", ui.inteiro(d["caminhoes_semana_pico"].sum()), border=True)
k4.metric("Razão pico/média", f"{rr['pico'] / rr['media']:.2f}".replace(".", ","), border=True)

# ---------- gráficos ----------
g1, g2 = st.columns(2)
col = db.ler(con, "SELECT * FROM colheita")
col["curva"] = col["uf"] + ", " + col["regiao"]
fig = px.line(
    col, x="data_referencia", y="pct_area_colhida", color="curva", markers=True,
    labels={"data_referencia": "", "pct_area_colhida": "% da área colhida", "curva": ""},
    title="Colheita de soja, safra 2025/26",
)
fig.update_traces(line_width=2, marker_size=6)
fig.update_xaxes(tickformat="%d/%m")
with g1.container(border=True, key="card_pl2"):
    st.plotly_chart(fig, width="stretch", theme=None)

prod = db.ler(con, "SELECT * FROM producao_municipal WHERE uf = ?", (uf,))
prod = prod[prod["municipio"].isin(muns)].groupby("ano", as_index=False)["producao_t"].sum()
cores = [ui.LARANJA if a == ano else ui.AZUL for a in prod["ano"]]
fig2 = px.bar(prod, x="ano", y="producao_t", labels={"ano": "", "producao_t": "Produção (t)"},
              title=f"Produção de soja, safra base {ano} em destaque")
fig2.update_traces(marker_color=cores)
fig2.update_xaxes(dtick=1)
with g2.container(border=True, key="card_pl3"):
    st.plotly_chart(fig2, width="stretch", theme=None)

# ---------- tabela ----------
with st.container(border=True, key="card_pl4"):
    st.subheader("Demanda por município")
    tab = d[["municipio", "n_unidades", "producao_t", "t_dia_pico", "caminhoes_dia_pico",
             "caminhoes_dia_media", "caminhoes_semana_pico"]]
    st.dataframe(
        tab, hide_index=True, width="stretch",
        column_config={
            "municipio": st.column_config.TextColumn("Município"),
            "n_unidades": st.column_config.NumberColumn("Unidades", format="%d"),
            "producao_t": st.column_config.NumberColumn(f"Produção {ano} (t)", format="%.0f"),
            "t_dia_pico": st.column_config.NumberColumn("t/dia no pico", format="%.0f"),
            "caminhoes_dia_pico": st.column_config.ProgressColumn(
                "Caminhões/dia no pico", format="%.0f", min_value=0, max_value=float(max(tab["caminhoes_dia_pico"].max(), 1))),
            "caminhoes_dia_media": st.column_config.NumberColumn("Caminhões/dia na média", format="%.0f"),
            "caminhoes_semana_pico": st.column_config.NumberColumn("Caminhões/semana no pico", format="%.0f"),
        },
    )
    st.download_button("Baixar tabela (CSV)", tab.round(0).to_csv(index=False).encode("utf-8"), "demanda_descargas.csv")

# ---------- grade de horários ----------
with st.container(border=True, key="card_pl5"):
    st.subheader("Grade de horários de uma unidade")
    st.caption("Horas de recebimento e duração da janela não têm fonte pública. Confirmar na visita.")
    if db.NO_NAVEGADOR:
        st.info("Nesta versão no navegador, cada unidade já começa com uma grade de exemplo, "
                "das 07:00 às 19:00 nos próximos 7 dias. Os dados ficam só neste navegador.")
    un = db.ler(con, "SELECT * FROM unidade WHERE uf = ? ORDER BY municipio", (uf,))
    un["rotulo"] = un["id_unidade"] + ", " + un["municipio"] + " (" + un["tipo"] + ")"
    a, b, c, e = st.columns(4)
    rot = a.selectbox("Unidade", un["rotulo"])
    id_un = rot.split(",")[0]
    mun_un = un.loc[un["id_unidade"] == id_un, "municipio"].iloc[0]
    n_mesmo_mun = int(un["municipio"].eq(mun_un).sum())
    HORAS = [time(h, m) for h in range(24) for m in (0, 30)]
    h_ini = b.selectbox("Início do recebimento", HORAS, index=None, format_func=lambda t: t.strftime("%H:%M"), placeholder="escolher")
    h_fim = c.selectbox("Fim do recebimento", HORAS, index=None, format_func=lambda t: t.strftime("%H:%M"), placeholder="escolher")
    minutos = e.selectbox("Duração da janela (min)", [30, 60, 120], index=1)

    if h_ini and h_fim and h_fim > h_ini:
        linha = dem[(dem["uf"] == uf) & (dem["municipio"] == mun_un)].iloc[0]
        cam_unidade = linha["caminhoes_dia_pico"] / n_mesmo_mun
        n_jan = int((pd.Timestamp.combine(date.today(), h_fim) - pd.Timestamp.combine(date.today(), h_ini)).seconds // 60 // minutos)
        vagas = math.ceil(cam_unidade / n_jan) if n_jan else 0
        m1, m2, m3 = st.columns(3)
        m1.metric("Caminhões/dia no pico na unidade", ui.inteiro(cam_unidade), border=True,
                  help=f"Município dividido por {n_mesmo_mun} unidade(s).")
        m2.metric("Janelas por dia", n_jan, border=True)
        m3.metric("Vagas por janela", vagas, border=True)
        d1, d2, d3 = st.columns(3)
        ini = d1.date_input("Primeiro dia", value=date.today(), format="DD/MM/YYYY")
        dias = d2.number_input("Quantos dias", 1, 120, 7)
        vagas_ed = d3.number_input("Vagas por janela", 1, 1000, max(vagas, 1))
        if st.button("Criar janelas no banco", type="primary"):
            datas = [ini + timedelta(days=i) for i in range(int(dias))]
            n = db.criar_janelas(con, id_un, datas, h_ini, h_fim, minutos, vagas_ed)
            st.success(f"{n} janelas criadas para {id_un}.")
    else:
        st.warning("Informe o início e o fim do recebimento para calcular as vagas.")
