# Análises do artigo

Scripts que reproduzem os números do artigo a partir dos dados em `dados/csv`.

1. `exploratoria.py`: relatório de qualidade (ausências, duplicados, rendimentos fora do padrão pelo intervalo interquartil) e estatísticas descritivas da soja no Oeste Paranaense, 2015 a 2024.
2. `ahp_topsis.py`: pesos AHP, ordenação TOPSIS das quatro alternativas de controle de entrada e 13 cenários de sensibilidade. Os julgamentos par a par e as notas são julgamento declarado das autoras.
3. A demanda de descargas por município é calculada pela função `demanda` em `dashboard/db.py`, a mesma usada pela tela de planejamento; a tabela completa está em `dados/csv/demanda_descargas_teto_municipal.csv`.

```
python analise/exploratoria.py
python analise/ahp_topsis.py
```

Os resultados ficam em `analise/resultados`.
