"""Banco SQLite do protótipo e cálculos da demanda de descargas.

Tabelas públicas (unidade, producao_municipal, colheita, carga) são recarregadas
dos CSVs em data/. Tabelas de uso (janela, agendamento, evento_portaria) só
recebem o que for registrado nas telas.
"""
import math
import os
import sqlite3
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
DATA = BASE / "data"
DB = Path(os.environ.get("DB_PATH", DATA / "recebimento.db"))
# versão que roda no navegador (stlite, GitHub Pages)
NO_NAVEGADOR = sys.platform == "emscripten"

PRODUTOS = ["Soja", "Milho", "Trigo", "Outro"]
STATUS = ["agendado", "chegou", "em descarga", "concluído", "não compareceu"]
# evento gravado quando o status muda para cada valor
EVENTO_DO_STATUS = {"chegou": "chegada", "em descarga": "inicio_descarga", "concluído": "saida"}
PROXIMO = {"agendado": "chegou", "chegou": "em descarga", "em descarga": "concluído"}
CURVA_DA_UF = {"PR": ("PR", "Estado"), "MS": ("MS", "Sul")}


def conectar():
    con = sqlite3.connect(DB, check_same_thread=False)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def iniciar():
    """Cria as tabelas de uso e recarrega as públicas a partir dos CSVs."""
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = conectar()
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS janela (
            id_janela INTEGER PRIMARY KEY AUTOINCREMENT,
            id_unidade TEXT NOT NULL,
            data TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            vagas INTEGER NOT NULL,
            UNIQUE (id_unidade, data, hora_inicio)
        );
        CREATE TABLE IF NOT EXISTS agendamento (
            id_agendamento INTEGER PRIMARY KEY AUTOINCREMENT,
            id_janela INTEGER NOT NULL REFERENCES janela(id_janela),
            produto TEXT NOT NULL,
            placa TEXT NOT NULL,
            nota_fiscal TEXT NOT NULL,
            nome_motorista TEXT NOT NULL,
            local_descarga TEXT,
            canal TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'agendado',
            teste INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS evento_portaria (
            id_evento INTEGER PRIMARY KEY AUTOINCREMENT,
            id_agendamento INTEGER NOT NULL REFERENCES agendamento(id_agendamento),
            tipo TEXT NOT NULL,
            data_hora TEXT NOT NULL
        );
        """
    )
    un = pd.read_csv(DATA / "unidades_cooperativa.csv")
    un = un[un["tipo"].isin(["Unidade de atendimento", "Indústria de soja"])]
    un.to_sql("unidade", con, if_exists="replace", index=False)

    pam = pd.read_csv(DATA / "ibge_pam_soja_municipios_oestePR_MS_2015_2024.csv")
    longo = pam.melt(id_vars=["uf", "municipio", "variavel"], var_name="ano", value_name="valor")
    longo["ano"] = longo["ano"].astype(int)
    longo = longo.pivot_table(index=["uf", "municipio", "ano"], columns="variavel", values="valor").reset_index()
    longo.columns.name = None
    longo.rename(columns={"area_colhida_ha": "area_ha"}).to_sql("producao_municipal", con, if_exists="replace", index=False)

    pd.read_csv(DATA / "colheita_2025_26_pr_ms.csv").to_sql("colheita", con, if_exists="replace", index=False)
    pd.read_csv(DATA / "carga_caminhao.csv").to_sql("carga", con, if_exists="replace", index=False)
    con.commit()
    return con


def ler(con, sql, params=()):
    return pd.read_sql_query(sql, con, params=params)


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- parte A: demanda ----------

def ritmos(con):
    """Ritmo de pico e médio (% da área por dia) por curva, a partir dos boletins."""
    c = ler(con, "SELECT * FROM colheita")
    c["data"] = pd.to_datetime(c["data_referencia"])
    out = {}
    for (uf, reg), g in c.sort_values("data").groupby(["uf", "regiao"]):
        dias = g["data"].diff().dt.days
        ritmo = g["pct_area_colhida"].diff() / dias
        total_dias = (g["data"].iloc[-1] - g["data"].iloc[0]).days
        out[(uf, reg)] = {
            "pico": ritmo.max(),
            "media": (g["pct_area_colhida"].iloc[-1] - g["pct_area_colhida"].iloc[0]) / total_dias,
            "inicio": g["data"].iloc[0].date(),
            "fim": g["data"].iloc[-1].date(),
        }
    return out


def demanda(con, ano, participacao, carga_t):
    """Caminhões por dia em cada município com unidade, no pico e na média."""
    r = ritmos(con)
    mun = ler(
        con,
        """SELECT u.uf, u.municipio, COUNT(*) AS n_unidades, p.producao_t
           FROM unidade u LEFT JOIN producao_municipal p
             ON p.uf = u.uf AND p.municipio = u.municipio AND p.ano = ?
           GROUP BY u.uf, u.municipio""",
        (ano,),
    )
    mun["pico_pct_dia"] = mun["uf"].map(lambda u: r[CURVA_DA_UF[u]]["pico"])
    mun["media_pct_dia"] = mun["uf"].map(lambda u: r[CURVA_DA_UF[u]]["media"])
    base = mun["producao_t"].fillna(0) * participacao / 100
    mun["t_dia_pico"] = base * mun["pico_pct_dia"] / 100
    mun["caminhoes_dia_pico"] = mun["t_dia_pico"] / carga_t
    mun["caminhoes_dia_media"] = base * mun["media_pct_dia"] / 100 / carga_t
    mun["caminhoes_semana_pico"] = mun["caminhoes_dia_pico"] * 7
    return mun


# ---------- parte B: agendamento e portaria ----------

def criar_janelas(con, id_unidade, datas, hora_ini, hora_fim, minutos, vagas):
    criadas = 0
    for d in datas:
        t = datetime.combine(d, hora_ini)
        fim = datetime.combine(d, hora_fim)
        while t + pd.Timedelta(minutes=minutos) <= fim:
            t2 = t + pd.Timedelta(minutes=minutos)
            cur = con.execute(
                "INSERT OR IGNORE INTO janela (id_unidade, data, hora_inicio, hora_fim, vagas) VALUES (?,?,?,?,?)",
                (id_unidade, d.isoformat(), t.strftime("%H:%M"), t2.strftime("%H:%M"), int(vagas)),
            )
            criadas += cur.rowcount
            t = t2
    con.commit()
    return criadas


def janelas_livres(con, id_unidade, data):
    return ler(
        con,
        """SELECT j.id_janela, j.hora_inicio, j.hora_fim, j.vagas,
                  COUNT(a.id_agendamento) AS ocupadas
           FROM janela j LEFT JOIN agendamento a
             ON a.id_janela = j.id_janela AND a.status <> 'não compareceu'
           WHERE j.id_unidade = ? AND j.data = ?
           GROUP BY j.id_janela ORDER BY j.hora_inicio""",
        (id_unidade, data),
    ).assign(livres=lambda d: d["vagas"] - d["ocupadas"])


def agendar(con, id_janela, produto, placa, nota, motorista, local, canal, teste):
    cur = con.execute(
        """INSERT INTO agendamento (id_janela, produto, placa, nota_fiscal, nome_motorista,
                                    local_descarga, canal, teste, criado_em)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (id_janela, produto, placa, nota, motorista, local, canal, int(teste), agora()),
    )
    con.commit()
    return cur.lastrowid


def mudar_status(con, id_agendamento, novo):
    con.execute("UPDATE agendamento SET status = ? WHERE id_agendamento = ?", (novo, id_agendamento))
    if novo in EVENTO_DO_STATUS:
        con.execute(
            "INSERT INTO evento_portaria (id_agendamento, tipo, data_hora) VALUES (?,?,?)",
            (id_agendamento, EVENTO_DO_STATUS[novo], agora()),
        )
    con.commit()


def marcar_nao_comparecidos(con):
    """Agendamentos sem chegada depois do fim da janela viram 'não compareceu'."""
    con.execute(
        """UPDATE agendamento SET status = 'não compareceu'
           WHERE status = 'agendado' AND id_janela IN (
               SELECT id_janela FROM janela WHERE datetime(data || ' ' || hora_fim) < datetime(?))""",
        (agora(),),
    )
    con.commit()


def painel(con, id_unidade, data):
    """Agendamentos do dia com os horários de cada evento."""
    return ler(
        con,
        """SELECT a.id_agendamento, j.hora_inicio, j.hora_fim, a.placa, a.nome_motorista,
                  a.produto, a.nota_fiscal, a.local_descarga, a.canal, a.status, a.teste,
                  MAX(CASE WHEN e.tipo='chegada' THEN e.data_hora END) AS chegada,
                  MAX(CASE WHEN e.tipo='inicio_descarga' THEN e.data_hora END) AS inicio_descarga,
                  MAX(CASE WHEN e.tipo='saida' THEN e.data_hora END) AS saida
           FROM agendamento a JOIN janela j ON j.id_janela = a.id_janela
           LEFT JOIN evento_portaria e ON e.id_agendamento = a.id_agendamento
           WHERE j.id_unidade = ? AND j.data = ?
           GROUP BY a.id_agendamento ORDER BY j.hora_inicio, a.id_agendamento""",
        (id_unidade, data),
    )


def codigo(id_agendamento):
    return f"A{id_agendamento:05d}"


def id_do_codigo(cod):
    cod = cod.strip().upper().lstrip("A")
    return int(cod) if cod.isdigit() else None


def semear_grade_exemplo(con, dias=7, inicio=time(7, 0), fim=time(19, 0), minutos=60):
    """Versão no navegador: cria uma grade de exemplo quando o banco não tem janelas.

    O horário de 07:00 às 19:00 é só para a demonstração (não tem fonte). As vagas
    por janela saem da demanda no pico com bitrem e participação de 100%.
    """
    if con.execute("SELECT COUNT(*) FROM janela").fetchone()[0]:
        return 0
    carga = float(ler(con, "SELECT carga_t FROM carga WHERE configuracao LIKE 'Bitrem%'")["carga_t"].iloc[0])
    dem = demanda(con, 2024, 100, carga).set_index(["uf", "municipio"])
    un = ler(con, "SELECT * FROM unidade")
    n_por_mun = un.groupby(["uf", "municipio"]).size()
    n_jan = (fim.hour * 60 + fim.minute - inicio.hour * 60 - inicio.minute) // minutos
    datas = [date.today() + timedelta(days=i) for i in range(dias)]
    total = 0
    for u in un.itertuples():
        cam = dem.loc[(u.uf, u.municipio), "caminhoes_dia_pico"] / n_por_mun[(u.uf, u.municipio)]
        total += criar_janelas(con, u.id_unidade, datas, inicio, fim, minutos, max(1, math.ceil(cam / n_jan)))
    return total
