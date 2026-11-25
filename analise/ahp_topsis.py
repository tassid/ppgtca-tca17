"""AHP (pesos) e TOPSIS (ordenação) das alternativas de controle de entrada.

Os julgamentos par a par e as notas das alternativas são julgamento declarado
das autoras (escala de Saaty, 1 a 9), apoiado na literatura citada no artigo.
"""
import numpy as np
import pandas as pd

CRIT = ["Custo", "Eficiência", "Qualidade dos dados", "Facilidade de implantação", "Inclusão digital", "Ambiental"]
# matriz de comparação par a par (linha em relação à coluna)
M = np.array([
    [1,   1/3, 1/2, 2,   2,   3],
    [3,   1,   2,   3,   3,   4],
    [2,   1/2, 1,   2,   3,   3],
    [1/2, 1/3, 1/2, 1,   1,   2],
    [1/2, 1/3, 1/3, 1,   1,   2],
    [1/3, 1/4, 1/3, 1/2, 1/2, 1],
])
ALT = ["A. Controle manual", "B. Agendamento por aplicativo", "C. Aplicativo e totem", "D. Leitura automática integrada"]
# notas 1 a 9, todas no sentido "maior é melhor" (custo: 9 = mais barato)
X = np.array([
    [9, 2, 2, 9, 8, 2],
    [7, 6, 6, 6, 4, 6],
    [6, 7, 7, 6, 7, 7],
    [2, 9, 9, 2, 6, 8],
], dtype=float)

RI = {3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32}


def ahp(m):
    val, vec = np.linalg.eig(m)
    k = np.argmax(val.real)
    w = np.abs(vec[:, k].real)
    w = w / w.sum()
    n = len(m)
    ci = (val[k].real - n) / (n - 1)
    return w, val[k].real, ci, ci / RI[n]


def topsis(x, w):
    r = x / np.sqrt((x ** 2).sum(axis=0))
    v = r * w
    ideal, anti = v.max(axis=0), v.min(axis=0)
    dp = np.sqrt(((v - ideal) ** 2).sum(axis=1))
    dn = np.sqrt(((v - anti) ** 2).sum(axis=1))
    return dn / (dp + dn)


w, lmax, ci, cr = ahp(M)
print("Pesos AHP:", dict(zip(CRIT, w.round(3))), f"lambda_max={lmax:.3f} CI={ci:.3f} CR={cr:.3f}")
c = topsis(X, w)
base = pd.DataFrame({"alternativa": ALT, "Ci": c.round(3)}).sort_values("Ci", ascending=False)
base["posicao"] = range(1, len(ALT) + 1)
print(base.to_string(index=False))

# sensibilidade: cada peso multiplicado por 0,5 e 1,5 (renormalizado) e pesos iguais
linhas = []
for j, nome in enumerate(CRIT):
    for f in (0.5, 1.5):
        w2 = w.copy(); w2[j] *= f; w2 /= w2.sum()
        c2 = topsis(X, w2)
        linhas.append({"cenario": f"{nome} x{str(f).replace('.', ',')}", **dict(zip(ALT, c2.round(3))), "melhor": ALT[int(np.argmax(c2))]})
ceq = topsis(X, np.ones(6) / 6)
linhas.append({"cenario": "Pesos iguais", **dict(zip(ALT, ceq.round(3))), "melhor": ALT[int(np.argmax(ceq))]})
sens = pd.DataFrame(linhas)
print(sens.to_string(index=False))
print("Vezes em 1º lugar:", sens["melhor"].value_counts().to_dict())
# peso de eficiência a partir do qual D passa C
for p in np.arange(0.05, 0.95, 0.01):
    w3 = w.copy(); resto = 1 - w[1]; w3 = w3 * (1 - p) / resto; w3[1] = p
    c3 = topsis(X, w3)
    if c3[3] > c3[2]:
        print(f"D supera C quando o peso da eficiência passa de {p:.2f}"); break
from pathlib import Path
SAIDA = Path(__file__).resolve().parent / "resultados"; SAIDA.mkdir(exist_ok=True)
pd.DataFrame({"criterio": CRIT, "peso": w.round(4)}).to_csv(SAIDA / "pesos_ahp.csv", index=False)
base.to_csv(SAIDA / "ranking_topsis.csv", index=False)
sens.to_csv(SAIDA / "sensibilidade.csv", index=False)
