# TCA17 Sistemas Agroindustriais (PPGTCA/UTFPR)

Trabalho final da disciplina: cadeia da soja no oeste do Paraná e recebimento de grãos em uma cooperativa da região.
Foco na demanda 0121: sistema integrado de acesso, agendamento e monitoramento de descargas.

## Conteúdo

1. `dashboard/`: protótipo em Streamlit com três telas (planejamento, agendamento e monitoramento) e modo totem. Instruções em `dashboard/README.md`.
2. `dados/`: planilha `dados_publicos_soja_oeste_pr.xlsx` (com fórmulas) e os mesmos dados em CSV.

## Fontes dos dados

Todos os dados são públicos e reais: IBGE (Produção Agrícola Municipal, tabela 5457, e Pesquisa de Estoques), Deral/SEAB PR, Aprosoja MS (SIGA-MS), Famasul, MAPA (IN 11/2007) e Stamm Junior e Pereira (2009) para a carga por caminhão.
A cooperativa não é identificada.

## Rodar o dashboard

```
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

No Streamlit Community Cloud, usar `dashboard/app.py` como arquivo principal.

Versão no navegador, sem servidor: https://tassid.github.io/ppgtca-tca17/ (publicada pelo GitHub Actions; detalhes em `dashboard/README.md`).
