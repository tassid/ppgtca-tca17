# Agendamento e monitoramento de descargas de grãos

Protótipo da demanda 0121 (sistema integrado de acesso, agendamento e monitoramento de descargas)
para uma cooperativa do oeste do Paraná. Trabalho da disciplina Sistemas Agroindustriais (PPGTCA/UTFPR).

## Como rodar

```
pip install -r requirements.txt
streamlit run app.py
```

Abre em http://localhost:8501. O banco SQLite (`data/recebimento.db`) é criado na primeira execução.

Totem: abrir `http://localhost:8501/?modo=totem` em tela cheia (Chrome com `--kiosk`). Mostra só o agendamento e o registro de chegada, com letra maior.

## Telas

1. **Planejamento** (dados reais): caminhões por dia no pico e na média em cada município com unidade, a partir da produção do IBGE PAM, do ritmo da colheita 2025/26 (Deral e Aprosoja MS) e da carga por caminhão (Stamm Junior e Pereira, 2009). Cria a grade de janelas de uma unidade.
2. **Agendamento**: o motorista escolhe unidade, dia e janela e informa produto, placa, nota, nome e local de descarga. Recebe um código. No local, registra a chegada com o código.
3. **Monitoramento**: contagem por status, fila, tempo de fila, permanência, pontualidade, não comparecimento e ocupação das janelas. Atualiza a cada 10 segundos. A portaria avança o status pelo código.

## Fluxo de status

agendado → chegou → em descarga → concluído. Agendamento sem chegada até o fim da janela vira "não compareceu".

## Dados

Os CSVs em `data/` são públicos e anonimizados (a cooperativa não é identificada).
Registros feitos em demonstração ficam marcados como teste e não entram nos resultados do artigo.

## Arquivos

1. `app.py`: navegação e modo totem
2. `db.py`: banco, cálculo da demanda e regras de agendamento
3. `telas/`: uma página por tela
