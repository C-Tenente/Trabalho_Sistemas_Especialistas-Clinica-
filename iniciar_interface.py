"""Inicia o aplicativo original com o novo template visual."""

from pathlib import Path

from flask import send_from_directory

import app as clinica

PASTA_INTERFACE = Path(__file__).resolve().parent / "interface"
clinica.HTML_BASE = (PASTA_INTERFACE / "pagina.html").read_text(encoding="utf-8")


@clinica.app.get("/interface/<path:arquivo>")
def arquivo_interface(arquivo):
    return send_from_directory(PASTA_INTERFACE / "estaticos", arquivo)


if __name__ == "__main__":
    clinica.app.run()
