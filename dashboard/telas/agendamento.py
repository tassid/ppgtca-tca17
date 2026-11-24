"""Tela 2: agendamento pelo motorista e registro de chegada.

No celular ou no computador a tela abre com as duas abas. No totem
(?modo=totem&unidade=U20) a unidade é fixa e a tela vira um fluxo de toque:
início com dois botões grandes, um passo por vez e confirmação em tela cheia.
"""
import re
import time
from datetime import date, timedelta

import streamlit as st

import db
import ui

con = st.session_state["con"]
totem = st.session_state.get("totem", False)
canal = "totem" if totem else "app"
PLACA = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")  # padrão antigo e Mercosul
ss = st.session_state

if totem:
    teste = st.query_params.get("teste", "1") != "0"
else:
    with st.sidebar:
        teste = st.checkbox("Marcar como registro de teste", value=True,
                            help="Registros feitos em demonstração não entram em resultados.")


# ---------- consultas ----------

def unidades_com_janela():
    un = db.ler(con, "SELECT * FROM unidade ORDER BY uf, municipio")
    com = db.ler(con, "SELECT DISTINCT id_unidade FROM janela WHERE data >= ?", (date.today().isoformat(),))
    un = un[un["id_unidade"].isin(com["id_unidade"])].copy()
    un["rotulo"] = un["id_unidade"] + ", " + un["municipio"] + " " + un["uf"]
    return un


def janelas_abertas(id_un, dia):
    jan = db.janelas_livres(con, id_un, dia.isoformat())
    if dia == date.today():  # só janelas que ainda não acabaram
        jan = jan[jan["hora_fim"] > db.agora()[11:16]]
    return jan[jan["livres"] > 0]


def dias_com_vaga(id_un, n=5):
    dias = []
    d = date.today()
    for _ in range(30):
        if not janelas_abertas(id_un, d).empty:
            dias.append(d)
            if len(dias) == n:
                break
        d += timedelta(days=1)
    return dias


def nome_dia(d):
    if d == date.today():
        return f"Hoje, {d:%d/%m}"
    if d == date.today() + timedelta(days=1):
        return f"Amanhã, {d:%d/%m}"
    return f"{['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'][d.weekday()]}, {d:%d/%m}"


def validar(placa, nota, motorista):
    erros = []
    if not PLACA.match(placa):
        erros.append("Placa inválida.")
    if not nota:
        erros.append("Informe o número da nota.")
    if not motorista:
        erros.append("Informe o nome do motorista.")
    return erros


def registrar_chegada(cod_ou_placa):
    """Aceita o código (A00001) ou a placa com agendamento para hoje."""
    txt = cod_ou_placa.strip().upper().replace("-", "").replace(" ", "")
    i = db.id_do_codigo(txt) if re.fullmatch(r"A?\d+", txt) else None
    if i is None and PLACA.match(txt):
        r = db.ler(con, """SELECT a.id_agendamento FROM agendamento a JOIN janela j ON j.id_janela = a.id_janela
                           WHERE a.placa = ? AND j.data = ? AND a.status = 'agendado'
                           ORDER BY j.hora_inicio LIMIT 1""", (txt, date.today().isoformat()))
        i = int(r["id_agendamento"].iloc[0]) if not r.empty else None
    if i is None:
        return "erro", "Agendamento não encontrado. Confira o código ou a placa."
    reg = db.ler(con, "SELECT status, placa FROM agendamento WHERE id_agendamento = ?", (i,))
    if reg.empty:
        return "erro", "Agendamento não encontrado. Confira o código ou a placa."
    if reg["status"].iloc[0] != "agendado":
        return "aviso", f"Este agendamento está como '{reg['status'].iloc[0]}'."
    db.mudar_status(con, i, "chegou")
    return "ok", f"Chegada registrada para a placa {reg['placa'].iloc[0]}. Aguarde a chamada para descarga."


# ---------- formulário (usado no app e no totem) ----------

def formulario(id_un, chave):
    dias = dias_com_vaga(id_un)
    if not dias:
        st.warning("Sem vagas nos próximos dias nesta unidade.")
        return None
    dia = st.segmented_control("Dia", dias, default=dias[0], format_func=nome_dia, key=f"dia_{chave}") or dias[0]
    jan = janelas_abertas(id_un, dia)
    opcoes = {f"{r.hora_inicio} às {r.hora_fim}": r.id_janela for r in jan.itertuples()}
    livres = {f"{r.hora_inicio} às {r.hora_fim}": r.livres for r in jan.itertuples()}
    janela = st.pills("Horário", list(opcoes), key=f"jan_{chave}",
                      format_func=lambda k: f"{k} ({livres[k]} {'vaga' if livres[k] == 1 else 'vagas'})")
    with st.form(f"form_{chave}", clear_on_submit=True, border=False):
        c1, c2 = st.columns(2)
        produto = c1.selectbox("Tipo de produto", db.PRODUTOS)
        placa = c2.text_input("Placa", max_chars=8, placeholder="ABC1D23")
        nota = c1.text_input("Número da nota")
        motorista = c2.text_input("Nome do motorista")
        local = st.text_input("Local de descarregamento", placeholder="moega, armazém ou silo indicado pela unidade")
        ok = st.form_submit_button("Confirmar agendamento", type="primary", width="stretch")
    if not ok:
        return None
    if janela is None:
        st.error("Escolha um horário.")
        return None
    placa_n = placa.upper().replace("-", "").replace(" ", "")
    erros = validar(placa_n, nota.strip(), motorista.strip())
    if erros:
        st.error(" ".join(erros))
        return None
    agora_livres = db.janelas_livres(con, id_un, dia.isoformat()).set_index("id_janela")["livres"]
    if agora_livres.get(opcoes[janela], 0) <= 0:
        st.error("Esta janela acabou de lotar. Escolha outro horário.")
        return None
    i = db.agendar(con, opcoes[janela], produto, placa_n, nota.strip(), motorista.strip(), local.strip(), canal, teste)
    return {"codigo": db.codigo(i), "dia": nome_dia(dia), "janela": janela, "placa": placa_n}


# ---------- totem ----------

VOLTA_EM = 20  # segundos até o totem voltar sozinho ao início depois de concluir


def voltar():
    ss["passo"] = "inicio"
    ss.pop("confirmado", None)
    ss.pop("fim_em", None)


@st.fragment(run_every="1s")
def volta_automatica():
    ss.setdefault("fim_em", time.time() + VOLTA_EM)
    falta = int(ss["fim_em"] - time.time())
    if falta <= 0:
        voltar()
        st.rerun(scope="app")
    st.caption(f"A tela volta ao início em {falta} s.")


def tela_totem():
    un = unidades_com_janela()
    id_un = st.query_params.get("unidade")
    if id_un not in set(un["id_unidade"]):
        if un.empty:
            st.warning("Nenhuma unidade tem janelas abertas. Crie a grade na tela de planejamento.")
            return
        st.markdown("# Escolha a unidade deste totem")
        rot = st.selectbox("Unidade", un["rotulo"])
        if st.button("Usar esta unidade", type="primary", width="stretch"):
            st.query_params["unidade"] = rot.split(",")[0]
            st.rerun()
        return
    linha = un.loc[un["id_unidade"] == id_un].iloc[0]
    ss.setdefault("passo", "inicio")

    if ss["passo"] == "inicio":
        st.markdown(f"# Recebimento de grãos, {linha['municipio']}")
        st.caption(f"Unidade {id_un}")
        a, b = st.columns(2)
        with a.container(key="tile_chegada"):
            if st.button("Tenho agendamento\n\nRegistrar chegada", type="primary", width="stretch"):
                ss["passo"] = "chegada"
                st.rerun()
        with b.container(key="tile_agendar"):
            if st.button("Não tenho agendamento\n\nAgendar descarga", width="stretch"):
                ss["passo"] = "agendar"
                st.rerun()

    elif ss["passo"] == "chegada":
        st.button("Voltar", on_click=voltar)
        st.markdown("# Registrar chegada")
        with st.container(border=True, key="card_tot1"):
            with st.form("chegada_totem", clear_on_submit=True, border=False):
                txt = st.text_input("Código do agendamento ou placa", placeholder="A00001 ou ABC1D23")
                ok = st.form_submit_button("Registrar chegada", type="primary", width="stretch")
            if ok:
                tipo, msg = registrar_chegada(txt)
                {"ok": st.success, "aviso": st.warning, "erro": st.error}[tipo](msg)
                if tipo == "ok":
                    st.button("Concluir", type="primary", width="stretch", on_click=voltar)
                    volta_automatica()

    elif ss["passo"] == "agendar":
        if "confirmado" in ss:
            c = ss["confirmado"]
            with st.container(border=True, key="card_tot2"):
                st.markdown("# Agendamento confirmado")
                st.markdown(f"<div class='codigo-grande'>{c['codigo']}</div>", unsafe_allow_html=True)
                st.markdown(f"**{c['dia']}, {c['janela']}**  \nPlaca {c['placa']}")
                st.caption("Apresente este código na portaria ou digite a placa no totem ao chegar.")
                st.button("Concluir", type="primary", width="stretch", on_click=voltar)
                volta_automatica()
            return
        st.button("Voltar", on_click=voltar)
        st.markdown("# Agendar descarga")
        with st.container(border=True, key="card_tot3"):
            r = formulario(id_un, "totem")
        if r:
            ss["confirmado"] = r
            st.rerun()


# ---------- app ----------

def tela_app():
    ui.cabecalho("Agendamento de descarga")
    aba_agendar, aba_chegada = st.tabs(["Agendar", "Cheguei na unidade"])
    with aba_agendar, st.container(border=True, key="card_ag1"):
        un = unidades_com_janela()
        if un.empty:
            st.warning("Nenhuma unidade tem janelas abertas. Crie a grade na tela de planejamento.")
        else:
            id_un = st.selectbox("Unidade", un["rotulo"]).split(",")[0]
            r = formulario(id_un, "app")
            if r:
                st.success(f"Agendado. Código: **{r['codigo']}**. {r['dia']}, {r['janela']}. Apresente este código na portaria.")
    with aba_chegada, st.container(border=True, key="card_ag2"):
        with st.form("chegada", clear_on_submit=True, border=False):
            txt = st.text_input("Código do agendamento ou placa", placeholder="A00001 ou ABC1D23")
            ok = st.form_submit_button("Registrar chegada", type="primary", width="stretch")
        if ok:
            tipo, msg = registrar_chegada(txt)
            {"ok": st.success, "aviso": st.warning, "erro": st.error}[tipo](msg)


if totem:
    tela_totem()
else:
    tela_app()
