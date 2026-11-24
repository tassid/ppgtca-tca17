"""Tela 3: monitoramento da portaria, com atualização automática."""
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import db
import ui

con = st.session_state["con"]
ui.cabecalho("Monitoramento da portaria")

un = db.ler(con, "SELECT DISTINCT u.* FROM unidade u JOIN janela j ON j.id_unidade = u.id_unidade ORDER BY uf, municipio")
if un.empty:
    st.warning("Nenhuma unidade tem janelas. Crie a grade na tela de planejamento.")
    st.stop()
un["rotulo"] = un["id_unidade"] + ", " + un["municipio"] + " " + un["uf"]
with st.container(border=True, key="card_mo1"):
    c1, c2, c3 = st.columns([2, 1, 1], vertical_alignment="bottom")
    id_un = c1.selectbox("Unidade", un["rotulo"]).split(",")[0]
    prox = db.ler(con, """SELECT MIN(j.data) AS d FROM agendamento a JOIN janela j ON j.id_janela = a.id_janela
                         WHERE j.id_unidade = ? AND j.data >= ?""", (id_un, date.today().isoformat()))["d"].iloc[0]
    dia = c2.date_input("Dia", value=date.fromisoformat(prox) if prox else date.today(), format="DD/MM/YYYY")
    so_reais = c3.toggle("Ocultar registros de teste", value=False)


def minutos(a, b):
    return (pd.to_datetime(b) - pd.to_datetime(a)).dt.total_seconds() / 60


def pct(v):
    return f"{v:.0%}".replace(".", ",")


@st.fragment(run_every="10s")
def painel_ao_vivo():
    db.marcar_nao_comparecidos(con)
    p = db.painel(con, id_un, dia.isoformat())
    if so_reais:
        p = p[p["teste"] == 0]
    cont = p["status"].value_counts()

    fila = minutos(p["chegada"], p["inicio_descarga"])
    perm = minutos(p["chegada"], p["saida"])
    chegou = p["chegada"].notna()
    no_prazo = chegou & (pd.to_datetime(p["chegada"]).dt.strftime("%H:%M") <= p["hora_fim"])
    encerrados = p["status"].isin(["chegou", "em descarga", "concluído", "não compareceu"])

    # a fila atual é o número que a portaria acompanha; os demais ficam menores ao lado
    a, b = st.columns([1, 3])
    with a.container(border=True, key="card_mo2", height="stretch"):
        st.caption("Na fila agora")
        st.markdown(f"<div style='font-size:3.4rem;font-weight:600;line-height:1.1;color:#0F6CBD'>{int(cont.get('chegou', 0))}</div>",
                    unsafe_allow_html=True)
        st.caption(f"Atualizado às {datetime.now():%H:%M:%S}")
    with b:
        k = st.columns(4)
        for col, s in zip(k, ["agendado", "em descarga", "concluído", "não compareceu"]):
            col.metric(s.capitalize(), int(cont.get(s, 0)), border=True)
        m = st.columns(4)
        m[0].metric("Tempo médio de fila (min)", f"{fila.mean():.0f}" if fila.notna().any() else "sem dado", border=True)
        m[1].metric("Permanência média (min)", f"{perm.mean():.0f}" if perm.notna().any() else "sem dado", border=True)
        m[2].metric("Pontualidade", pct(no_prazo.sum() / chegou.sum()) if chegou.any() else "sem dado", border=True)
        m[3].metric("Não comparecimento",
                    pct((p["status"] == "não compareceu").sum() / encerrados.sum()) if encerrados.any() else "sem dado",
                    border=True)

    jan = db.janelas_livres(con, id_un, dia.isoformat())
    if not jan.empty:
        longo = jan.melt(id_vars="hora_inicio", value_vars=["ocupadas", "livres"], var_name="situacao", value_name="qtd")
        longo["situacao"] = longo["situacao"].map({"ocupadas": "Ocupadas", "livres": "Livres"})
        fig = px.bar(longo, x="hora_inicio", y="qtd", color="situacao", barmode="stack",
                     color_discrete_map={"Ocupadas": ui.AZUL, "Livres": "#E0E0E0"},
                     labels={"hora_inicio": "", "qtd": "", "situacao": ""},
                     title="Ocupação das janelas")
        fig.update_layout(height=320, bargap=0.35, margin=dict(l=8, r=8, t=52, b=32))
        fig.update_yaxes(dtick=1, rangemode="tozero")
        with st.container(border=True, key="card_mo3"):
            st.plotly_chart(fig, width="stretch", theme=None)

    with st.container(border=True, key="card_mo4"):
        st.subheader("Caminhões do dia")
        if p.empty:
            st.info("Nenhum agendamento neste dia.")
        else:
            v = p.assign(codigo=p["id_agendamento"].map(db.codigo),
                         janela=p["hora_inicio"] + " às " + p["hora_fim"],
                         status=p["status"].str.capitalize(),
                         canal=p["canal"].str.capitalize(),
                         teste=p["teste"].astype(bool))
            for c in ["chegada", "inicio_descarga", "saida"]:
                v[c] = pd.to_datetime(v[c]).dt.strftime("%H:%M").fillna("")
            st.dataframe(
                v[["codigo", "janela", "status", "placa", "nome_motorista", "produto", "nota_fiscal",
                   "local_descarga", "canal", "chegada", "inicio_descarga", "saida", "teste"]],
                hide_index=True, width="stretch",
                column_config={
                    "codigo": "Código", "janela": "Janela", "status": "Status", "placa": "Placa",
                    "nome_motorista": "Motorista", "produto": "Produto", "nota_fiscal": "Nota",
                    "local_descarga": "Local de descarga", "canal": "Canal", "chegada": "Chegada",
                    "inicio_descarga": "Início da descarga", "saida": "Saída",
                    "teste": st.column_config.CheckboxColumn("Teste"),
                },
            )


painel_ao_vivo()

with st.container(border=True, key="card_mo5"):
    st.subheader("Avançar status")
    with st.form("status", clear_on_submit=True, border=False):
        f1, f2 = st.columns([3, 1], vertical_alignment="bottom")
        cod = f1.text_input("Código", placeholder="A00001")
        ok = f2.form_submit_button("Avançar para a próxima etapa", type="primary", width="stretch")
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
