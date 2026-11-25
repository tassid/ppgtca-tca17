"""Análise exploratória e relatório de qualidade da base do IBGE (PAM, soja, 2015 a 2024).

Uso: python analise/exploratoria.py   (lê dados/csv e grava em analise/resultados)
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "analise" / "resultados"
SAIDA.mkdir(exist_ok=True)
Y = [str(a) for a in range(2015, 2025)]

pam = pd.read_csv(RAIZ / "dados/csv/ibge_pam_soja_municipios_oestePR_MS_2015_2024.csv")
un = pd.read_csv(RAIZ / "dados/csv/unidades_cooperativa.csv")

# ---------- qualidade ----------
linhas = []
for uf, g in pam.groupby("uf"):
    for var, h in g.groupby("variavel"):
        linhas.append({"uf": uf, "variavel": var, "municipios": h["municipio"].nunique(),
                       "celulas": h[Y].size, "ausentes": int(h[Y].isna().sum().sum()),
                       "duplicados": int(h["municipio"].duplicated().sum())})
qual = pd.DataFrame(linhas)
print(qual.to_string(index=False))

pr = pam[pam["uf"] == "PR"].set_index(["municipio", "variavel"])[Y]
prod = pr.xs("producao_t", level="variavel")
area = pr.xs("area_colhida_ha", level="variavel")
rend = prod / area * 1000

outliers = []
for a in Y:
    s = rend[a].dropna()
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    for m, v in s[(s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)].items():
        outliers.append({"ano": a, "municipio": m, "rendimento_kg_ha": round(v)})
pd.DataFrame(outliers).to_csv(SAIDA / "rendimentos_fora_do_padrao_PR.csv", index=False)
print(f"Rendimentos fora do padrão (IQR), Oeste PR: {len(outliers)} de {rend.size}")

# ---------- estatísticas da mesorregião ----------
serie = pd.DataFrame({"producao_t": prod.sum(), "area_ha": area.sum()})
serie["rendimento_kg_ha"] = serie["producao_t"] / serie["area_ha"] * 1000
desc = pd.DataFrame({c: {"media": s.mean(), "mediana": s.median(), "desvio_padrao": s.std(),
                         "minimo": s.min(), "ano_min": s.idxmin(), "maximo": s.max(), "ano_max": s.idxmax(),
                         "cv_pct": s.std() / s.mean() * 100} for c, s in serie.items()}).T
print(desc.round(1).to_string())
print("Correlação produção x área:", round(np.corrcoef(serie["producao_t"], serie["area_ha"])[0, 1], 2))
print("Correlação produção x rendimento:", round(np.corrcoef(serie["producao_t"], serie["rendimento_kg_ha"])[0, 1], 2))
for a in ["2022", "2024"]:
    s = rend[a].dropna()
    print(f"Rendimento municipal {a}: média {s.mean():.0f}, CV {s.std() / s.mean() * 100:.1f}%, mín {s.min():.0f}, máx {s.max():.0f}")

mun_un = un.loc[un["uf"] == "PR", "municipio"].unique()
mun_un = [m for m in mun_un if m in prod.index and un[(un.municipio == m) & (un.tipo != "Administrativo")].shape[0]]
s_un = prod.loc[mun_un].sum()
print(f"Municípios com unidades: {len(mun_un)}; participação em 2024: {s_un['2024'] / serie.loc['2024', 'producao_t'] * 100:.1f}%;",
      f"queda 2021 para 2022: {(1 - s_un['2022'] / s_un['2021']) * 100:.1f}%")

qual.to_csv(SAIDA / "relatorio_qualidade.csv", index=False)
serie.to_csv(SAIDA / "serie_oeste_pr.csv")
desc.to_csv(SAIDA / "estatisticas_oeste_pr.csv")
