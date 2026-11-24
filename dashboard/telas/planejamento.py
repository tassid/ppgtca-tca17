"""Tela 1: demanda de descargas estimada com dados públicos (parte A)."""
import math
from datetime import date, time, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

import db

con = st.session_state["con"]
st.title("Planejamento da safra")
st.caption(
    "Estimativa com dados públicos: produção municipal (IBGE PAM), ritmo da colheita 2025/26 "
    "(Deral no PR, Aprosoja MS na região Sul do MS) e carga por caminhão (Stamm Junior e Pereira, 2009)."
)

# ---------- controles ----------
cargas = db.ler(con, "SELECT * FROM carga")
with st.sidebar:
    st.header("Parâmetros")
    ano = st.selectbox("Safra base (produção IBGE)", list(range(2024, 2014, -1)), index=0)
    tipo = st.radio("Caminhão", cargas["configuracao"], index=1)
    carga_t = float(cargas.loc[cargas["configuracao"] == tipo, "carga_t"].iloc[0])
    participacao = st.slider(
        "Participação da cooperativa na soja do município (%)", 0, 100, 100,
        help="100% é o teto. Trocar pelo valor informado pela cooperativa.",
    )
    st.caption(f"Carga usada: {carga_t:.2f} t por caminhão")

dem = db.demanda(con, ano, participacao, carga_t)
r = db.ritmos(con)

c1, c2 = st.columns([1, 3])
uf = c1.radio("UF", ["PR", "MS"], horizontal=True)
d = dem[dem["uf"] == uf].copy()
muns = c2.multiselect("Municípios", d["municipio"].tolist(), default=d["municipio"].tolist())
d = d[d["municipio"].isin(muns)]

if participacao == 100:
    st.info("Com participação de 100%, os números são o teto do município, não o recebimento da unidade.")

# ---------- indicadores ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Caminhões por dia no pico", f"{d['caminhoes_dia_pico'].sum():,.0f}".replace(",", "."))
k2.metric("Caminhões por dia na média", f"{d['caminhoes_dia_media'].sum():,.0f}".replace(",", "."))
k3.metric("Caminhões por semana no pico", f"{d['caminhoes_semana_pico'].sum():,.0f}".replace(",", "."))
rr = r[db.CURVA_DA_UF[uf]]
k4.metric("Razão pico/média", f"{rr['pico'] / rr['media']:.2f}".replace(".", ","))

# ---------- gráficos ----------
g1, g2 = st.columns(2)
col = db.ler(con, "SELECT * FROM colheita")
col["curva"] = col["uf"] + ", " + col["regiao"]
fig = px.line(
    col, x="data_referencia", y="pct_area_colhida", color="curva", markers=True,
    labels={"data_referencia": "Data do boletim", "pct_area_colhida": "% da área colhida", "curva": ""},
    title="Colheita de soja, safra 2025/26",
)
g1.plotly_chart(fig, width="stretch")

prod = db.ler(con, "SELECT * FROM producao_municipal WHERE uf = ?", (uf,))
prod = prod[prod["municipio"].isin(muns)].groupby("ano", as_index=False)["producao_t"].sum()
fig2 = px.bar(prod, x="ano", y="producao_t", labels={"ano": "Ano", "producao_t": "Produção (t)"},
              title="Produção de soja")
g2.plotly_chart(fig2, width="stretch")

# ---------- tabela ----------
st.subheader("Demanda por município")
tab = d[["municipio", "n_unidades", "producao_t", "t_dia_pico", "caminhoes_dia_pico",
         "caminhoes_dia_media", "caminhoes_semana_pico"]].rename(columns={
    "municipio": "Município", "n_unidades": "Unidades", "producao_t": f"Produção {ano} (t)",
    "t_dia_pico": "t/dia no pico", "caminhoes_dia_pico": "Caminhões/dia no pico",
    "caminhoes_dia_media": "Caminhões/dia na média", "caminhoes_semana_pico": "Caminhões/semana no pico"})
st.dataframe(tab.round(0), hide_index=True, width="stretch")
st.download_button("Baixar tabela (CSV)", tab.to_csv(index=False).encode("utf-8"), "demanda_descargas.csv")

# ---------- grade de horários ----------
st.subheader("Grade de horários de uma unidade")
st.caption("Horas de recebimento e duração da janela não têm fonte pública. Confirmar na visita.")
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
    st.write(
        f"Caminhões por dia no pico nesta unidade: **{cam_unidade:,.0f}** "
        f"(município dividido por {n_mesmo_mun} unidade(s)) → {n_jan} janelas → **{vagas} vagas por janela**."
    )
    d1, d2, d3 = st.columns(3)
    ini = d1.date_input("Primeiro dia", value=date.today())
    dias = d2.number_input("Quantos dias", 1, 120, 7)
    vagas_ed = d3.number_input("Vagas por janela", 1, 1000, max(vagas, 1))
    if st.button("Criar janelas no banco", type="primary"):
        datas = [ini + timedelta(days=i) for i in range(int(dias))]
        n = db.criar_janelas(con, id_un, datas, h_ini, h_fim, minutos, vagas_ed)
        st.success(f"{n} janelas criadas para {id_un}.")
else:
    st.warning("Informe o início e o fim do recebimento para calcular as vagas.")
