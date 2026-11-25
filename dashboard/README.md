# Agendamento e monitoramento de descargas de grãos

Protótipo da demanda 0121 (sistema integrado de acesso, agendamento e monitoramento de descargas)
para uma cooperativa do oeste do Paraná. Trabalho da disciplina Sistemas Agroindustriais (PPGTCA/UTFPR).

## Como rodar

```
pip install -r requirements.txt
streamlit run app.py
```

Abre em http://localhost:8501. O banco SQLite (`data/recebimento.db`) é criado na primeira execução.

## Versão no navegador (GitHub Pages)

O workflow `.github/workflows/pages.yml` monta uma versão estática com o stlite (Streamlit rodando no navegador via Pyodide) e publica em `https://tassid.github.io/ppgtca-tca17/` a cada push na `main`. Em pull requests ele só monta o site e testa no navegador, sem publicar; as capturas de tela ficam nos artefatos da execução.

1. Não precisa de servidor nem de conta no Streamlit Cloud.
2. O banco fica no navegador de quem abriu (IndexedDB) e sobrevive a recarregar a página. Abas no mesmo navegador compartilham o banco, então o totem numa aba e o monitoramento em outra funcionam juntos. Aparelhos diferentes não compartilham dados.
3. Cada unidade começa com uma grade de exemplo (07:00 às 19:00, próximos 7 dias), com vagas calculadas pela demanda no pico.
4. A primeira abertura demora de 10 a 30 segundos enquanto o navegador baixa o Python.

Para montar localmente: `python dashboard/web/build_site.py _site` e servir a pasta `_site` com qualquer servidor estático.

## Totem

Abrir `http://localhost:8501/?modo=totem&unidade=U20` em tela cheia (Chrome com `--kiosk`), trocando `U20` pela unidade onde o totem fica.

1. Tela inicial com dois botões grandes: "Tenho agendamento" (registra a chegada pelo código ou pela placa) e "Não tenho agendamento" (agenda no local).
2. Dia e horário escolhidos por toque; botões e campos com pelo menos 64 px de altura.
3. Depois de concluir, a tela volta sozinha ao início em 20 segundos, para o próximo motorista.
4. Sem `unidade` na URL, o totem pede a unidade uma vez.
5. Registros do totem saem marcados como teste. Para uso real, acrescentar `&teste=0` à URL.

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
3. `ui.py`: aparência (tema inspirado no Fluent 2 da Microsoft, gráficos e modo totem)
4. `telas/`: uma página por tela
5. `.streamlit/config.toml`: cores, fonte e cantos do tema
