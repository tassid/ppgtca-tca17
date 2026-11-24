"""Tela 3: monitoramento da portaria, com atualização automática."""
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

import db

con = st.session_state["con"]
st.title("Monitoramento da portaria")

un = db.ler(con, "SELECT DISTINCT u.* FROM unidade u JOIN janela j ON j.id_unidade = u.id_unidade ORDER BY uf, municipio")
if un.empty:
    st.warning("Nenhuma unidade tem janelas. Crie a grade na tela de planejamento.")
    st.stop()
un["rotulo"] = un["id_unidade"] + ", " + un["municipio"] + " " + un["uf"]
c1, c2, c3 = st.columns([2, 1, 1])
id_un = c1.selectbox("Unidade", un["rotulo"]).split(",")[0]
prox = db.ler(con, """SELECT MIN(j.data) AS d FROM agendamento a JOIN janela j ON j.id_janela = a.id_janela
                     WHERE j.id_unidade = ? AND j.data >= ?""", (id_un, date.today().isoformat()))["d"].iloc[0]
dia = c2.date_input("Dia", value=date.fromisoformat(prox) if prox else date.today(), format="DD/MM/YYYY")
so_reais = c3.toggle("Ocultar registros de teste", value=False)


def minutos(a, b):
    return (pd.to_datetime(b) - pd.to_datetime(a)).dt.total_seconds() / 60


@st.fragment(run_every="10s")
def painel_ao_vivo():
    db.marcar_nao_comparecidos(con)
    p = db.painel(con, id_un, dia.isoformat())
    if so_reais:
        p = p[p["teste"] == 0]
    cont = p["status"].value_counts()
    k = st.columns(5)
    for col, s in zip(k, db.STATUS):
        col.metric(s.capitalize(), int(cont.get(s, 0)))

    fila = minutos(p["chegada"], p["inicio_descarga"])
    perm = minutos(p["chegada"], p["saida"])
    chegou = p["chegada"].notna()
    no_prazo = chegou & (pd.to_datetime(p["chegada"]).dt.strftime("%H:%M") <= p["hora_fim"])
    encerrados = p["status"].isin(["chegou", "em descarga", "concluído", "não compareceu"])
    m = st.columns(4)
    m[0].metric("Tempo médio de fila (min)", f"{fila.mean():.0f}" if fila.notna().any() else "sem dado")
    m[1].metric("Permanência média (min)", f"{perm.mean():.0f}" if perm.notna().any() else "sem dado")
    m[2].metric("Pontualidade", f"{no_prazo.sum() / chegou.sum():.0%}" if chegou.any() else "sem dado")
    m[3].metric("Não comparecimento",
                f"{(p['status'] == 'não compareceu').sum() / encerrados.sum():.0%}" if encerrados.any() else "sem dado")

    jan = db.janelas_livres(con, id_un, dia.isoformat())
    if not jan.empty:
        fig = px.bar(jan, x="hora_inicio", y=["ocupadas", "livres"], barmode="stack",
                     labels={"hora_inicio": "Janela", "value": "Vagas", "variable": ""},
                     title="Ocupação das janelas")
        st.plotly_chart(fig, width="stretch")

    st.subheader("Caminhões do dia")
    if p.empty:
        st.info("Nenhum agendamento neste dia.")
    else:
        v = p.assign(codigo=p["id_agendamento"].map(db.codigo))
        st.dataframe(v[["codigo", "hora_inicio", "placa", "nome_motorista", "produto", "nota_fiscal",
                        "local_descarga", "canal", "status", "chegada", "inicio_descarga", "saida", "teste"]],
                     hide_index=True, width="stretch")


painel_ao_vivo()

st.subheader("Avançar status")
with st.form("status", clear_on_submit=True):
    cod = st.text_input("Código", placeholder="A00001")
    ok = st.form_submit_button("Avançar para a próxima etapa", type="primary")
if ok:
    i = db.id_do_codigo(cod)
    reg = db.ler(con, "SELECT status FROM agendamento WHERE id_agendamento = ?", (i,)) if i else None
    if reg is None or reg.empty:
        st.error("Código não encontrado.")
    else:
        atual = reg["status"].iloc[0]
        novo = db.PROXIMO.get(atual)
        if novo is None:
            st.warning(f"Agendamento já está como '{atual}'.")
        else:
            db.mudar_status(con, i, novo)
            st.success(f"{db.codigo(i)}: {atual} → {novo}")
            st.rerun()
