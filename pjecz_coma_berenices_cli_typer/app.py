"""
PJECZ Coma Berenices CLI Typer
"""

from typer import Typer

from pjecz_coma_berenices_cli_typer.commands.audiencias import app as audiencias_app

app = Typer(help="Interfaz de Linea de Comandos (CLI) para vocear audiencias")
app.add_typer(audiencias_app, name="audiencias")

if __name__ == "__main__":
    app()
