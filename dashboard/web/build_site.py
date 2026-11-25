"""Monta a versão estática do dashboard (stlite) para o GitHub Pages.

Uso:  python dashboard/web/build_site.py _site

Copia o código, os dados e os ícones para a pasta de saída e gera um
index.html que carrega o Streamlit no navegador (Pyodide) com esses arquivos.
"""
import json
import shutil
import sys
from pathlib import Path

STLITE = "1.12.1"  # @stlite/browser, traz o Streamlit 1.65
APP = Path(__file__).resolve().parent.parent
SAIDA = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()

INCLUIR = ["app.py", "db.py", "ui.py", "telas/*.py", "data/*.csv", "assets/*.svg", ".streamlit/config.toml"]

if SAIDA.exists():
    shutil.rmtree(SAIDA)
arquivos = sorted({p for padrao in INCLUIR for p in APP.glob(padrao)})
for p in arquivos:
    destino = SAIDA / "app" / p.relative_to(APP)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, destino)

files = {str(p.relative_to(APP)): {"url": f"./app/{p.relative_to(APP).as_posix()}"} for p in arquivos}
opcoes = {
    "entrypoint": "app.py",
    "requirements": ["plotly"],
    # pacotes que já vêm compilados no Pyodide (não estão no PyPI como wheel pura)
    "prebuiltPackageNames": ["pandas", "sqlite3"],
    "files": files,
    # o banco fica no IndexedDB do navegador: sobrevive a recarregar a página
    "idbfsMountpoints": ["/mnt"],
    "env": {"DB_PATH": "/mnt/recebimento.db"},
    # abas abertas no mesmo navegador (totem e monitoramento) usam o mesmo Python e o mesmo banco
    "sharedWorker": True,
}

html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
  <title>Gestão de descargas</title>
  <link rel="icon" href="./app/assets/icone.svg" type="image/svg+xml">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/browser@{STLITE}/build/stlite.css">
  <style>body{{margin:0;background:#F5F5F5}}</style>
</head>
<body>
  <div id="root"></div>
  <script type="module">
    import {{ mount }} from "https://cdn.jsdelivr.net/npm/@stlite/browser@{STLITE}/build/stlite.js";
    mount({json.dumps(opcoes, ensure_ascii=False, indent=2)}, document.getElementById("root"));
  </script>
</body>
</html>
"""
(SAIDA / "index.html").write_text(html, encoding="utf-8")
(SAIDA / ".nojekyll").write_text("")
print(f"{len(arquivos)} arquivos em {SAIDA}")
