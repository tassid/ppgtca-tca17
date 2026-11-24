"""Tela 2: agendamento pelo motorista (app ou totem) e registro de chegada."""
import re
from datetime import date

import streamlit as st

import db

con = st.session_state["con"]
totem = st.session_state.get("totem", False)
canal = "totem" if totem else "app"
PLACA = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")  # padrão antigo e Mercosul

st.title("Agendamento de descarga")
teste = True
if not totem:
    with st.sidebar:
        teste = st.checkbox("Marcar como registro de teste", value=True,
                            help="Registros feitos em demonstração não entram em resultados.")

aba_agendar, aba_chegada = st.tabs(["Agendar", "Cheguei na unidade"])

def proximo_dia_com_vaga(id_un):
    """Primeiro dia, a partir de hoje, com alguma janela ainda aberta e com vaga."""
    agora = db.agora()
    d = db.ler(con, """SELECT j.data FROM janela j LEFT JOIN agendamento a
                         ON a.id_janela = j.id_janela AND a.status <> 'não compareceu'
                       WHERE j.id_unidade = ? AND (j.data > ? OR (j.data = ? AND j.hora_fim > ?))
                       GROUP BY j.id_janela HAVING j.vagas > COUNT(a.id_agendamento)
                       ORDER BY j.data LIMIT 1""", (id_un, agora[:10], agora[:10], agora[11:16]))
    return date.fromisoformat(d["data"].iloc[0]) if not d.empty else date.today()


def formulario_agendamento():
    un = db.ler(con, "SELECT * FROM unidade ORDER BY uf, municipio")
    com_janela = db.ler(con, "SELECT DISTINCT id_unidade FROM janela WHERE data >= ?", (date.today().isoformat(),))
    un = un[un["id_unidade"].isin(com_janela["id_unidade"])]
    if un.empty:
        st.warning("Nenhuma unidade tem janelas abertas. Crie a grade na tela de planejamento.")
        return
    un["rotulo"] = un["id_unidade"] + ", " + un["municipio"] + " " + un["uf"]
    rot = st.selectbox("Unidade", un["rotulo"])
    id_un = rot.split(",")[0]
    dia = st.date_input("Dia", value=proximo_dia_com_vaga(id_un), min_value=date.today(), format="DD/MM/YYYY")
    jan = db.janelas_livres(con, id_un, dia.isoformat())
    if dia == date.today():  # só janelas que ainda não acabaram
        jan = jan[jan["hora_fim"] > db.agora()[11:16]]
    jan = jan[jan["livres"] > 0]
    if jan.empty:
        st.warning("Sem vagas neste dia. Escolha outro dia ou outra unidade.")
        return
    opcoes = {f"{r.hora_inicio} às {r.hora_fim} ({r.livres} {'vaga' if r.livres == 1 else 'vagas'})": r.id_janela for r in jan.itertuples()}

    with st.form("agendar", clear_on_submit=True):
        janela = st.radio("Horário", list(opcoes), horizontal=not totem)
        c1, c2 = st.columns(2)
        produto = c1.selectbox("Tipo de produto", db.PRODUTOS)
        placa = c2.text_input("Placa", max_chars=8, placeholder="ABC1D23")
        nota = c1.text_input("Número da nota")
        motorista = c2.text_input("Nome do motorista")
        local = st.text_input("Local de descarregamento", placeholder="moega, armazém ou silo indicado pela unidade")
        ok = st.form_submit_button("Confirmar agendamento", type="primary", width="stretch")

    if ok:
        placa_n = placa.upper().replace("-", "").replace(" ", "")
        erros = []
        if not PLACA.match(placa_n):
            erros.append("Placa inválida.")
        if not nota.strip():
            erros.append("Informe o número da nota.")
        if not motorista.strip():
            erros.append("Informe o nome do motorista.")
        if erros:
            st.error(" ".join(erros))
            return
        livres = db.janelas_livres(con, id_un, dia.isoformat()).set_index("id_janela")["livres"]
        if livres.get(opcoes[janela], 0) <= 0:
            st.error("Esta janela acabou de lotar. Escolha outro horário.")
            return
        i = db.agendar(con, opcoes[janela], produto, placa_n, nota.strip(), motorista.strip(),
                       local.strip(), canal, teste)
        st.success(f"Agendado. Código: **{db.codigo(i)}**. Apresente este código na portaria.")


with aba_agendar:
    formulario_agendamento()

with aba_chegada:
    with st.form("chegada", clear_on_submit=True):
        cod = st.text_input("Código do agendamento", placeholder="A00001")
        ok2 = st.form_submit_button("Registrar chegada", type="primary", width="stretch")
    if ok2:
        i = db.id_do_codigo(cod)
        reg = db.ler(con, "SELECT status, placa FROM agendamento WHERE id_agendamento = ?", (i,)) if i else None
        if reg is None or reg.empty:
            st.error("Código não encontrado.")
        elif reg["status"].iloc[0] != "agendado":
            st.warning(f"Este agendamento está como '{reg['status'].iloc[0]}'.")
        else:
            db.mudar_status(con, i, "chegou")
            st.success(f"Chegada registrada para a placa {reg['placa'].iloc[0]}. Aguarde a chamada para descarga.")
