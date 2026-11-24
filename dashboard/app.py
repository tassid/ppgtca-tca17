"""Sistema de agendamento e monitoramento de descargas (protótipo).

Rodar:  streamlit run app.py
Totem:  abrir http://localhost:8501/?modo=totem em modo quiosque.
"""
import streamlit as st

import db

st.set_page_config(page_title="Descargas de grãos", page_icon="🚚", layout="wide")


@st.cache_resource
def conexao():
    return db.iniciar()


st.session_state["con"] = conexao()
totem = st.query_params.get("modo") == "totem"
st.session_state["totem"] = totem

if totem:
    st.markdown(
        "<style>[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl']{display:none}"
        " html{font-size:20px}</style>",
        unsafe_allow_html=True,
    )
    paginas = [st.Page("telas/agendamento.py", title="Agendamento", icon="📝")]
else:
    paginas = [
        st.Page("telas/planejamento.py", title="Planejamento", icon="📊", default=True),
        st.Page("telas/agendamento.py", title="Agendamento", icon="📝"),
        st.Page("telas/monitoramento.py", title="Monitoramento", icon="🚦"),
    ]

st.navigation(paginas, position="hidden" if totem else "sidebar").run()
