"""Sistema de agendamento e monitoramento de descargas (protótipo).

Rodar:  streamlit run app.py
Totem:  abrir http://localhost:8501/?modo=totem em modo quiosque.
"""
import streamlit as st

import db
import ui

st.set_page_config(page_title="Descargas de grãos", page_icon="assets/icone.svg", layout="wide")


@st.cache_resource
def conexao():
    return db.iniciar()


st.session_state["con"] = conexao()
ui.estilo()
st.logo("assets/logo.svg", size="large")
totem = st.query_params.get("modo") == "totem"
st.session_state["totem"] = totem

if totem:
    ui.estilo_totem()
    paginas = [st.Page("telas/agendamento.py", title="Agendamento")]
else:
    paginas = {
        "Planejamento": [st.Page("telas/planejamento.py", title="Demanda e grade de horários", default=True)],
        "Operação": [
            st.Page("telas/agendamento.py", title="Agendamento"),
            st.Page("telas/monitoramento.py", title="Monitoramento da portaria"),
        ],
    }

st.navigation(paginas, position="hidden" if totem else "sidebar").run()
