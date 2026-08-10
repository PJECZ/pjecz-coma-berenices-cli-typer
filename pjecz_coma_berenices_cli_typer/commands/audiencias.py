"""
Command audiencias
"""

from datetime import datetime
from typing import Annotated

import requests
from pytz import timezone
from rich.console import Console
from rich.table import Table
from typer import Exit, Option, Typer

from pjecz_coma_berenices_cli_typer.config.settings import get_settings

app = Typer(name="audiencias", help="Comando para vocear audiencias")

settings = get_settings()
local_tz = timezone(settings.TZ)
fecha_hoy = datetime.now(tz=local_tz).strftime("%Y-%m-%d")


@app.command()
def descargar(fecha: Annotated[str, Option(help="Fecha en formato YYYY-MM-DD")] = fecha_hoy):
    """Descargar las audiencias"""
    console = Console()
    console.print(f"Descargando audiencias para la fecha: {fecha}")

    # Consultar la API para obtener las audiencias
    try:
        if fecha == fecha_hoy:
            respuesta = requests.get(
                url=settings.AGENDAMIENTO_AUDIENCIAS_PANTALLA_API_URL,
                headers={"X-Api-Key": settings.AGENDAMIENTO_AUDIENCIAS_API_KEY},
                timeout=60,
            )
        else:
            respuesta = requests.get(
                url=settings.AGENDAMIENTO_AUDIENCIAS_FECHA_API_URL,
                headers={"X-Api-Key": settings.AGENDAMIENTO_AUDIENCIAS_API_KEY},
                timeout=60,
                params={"fecha": fecha}
            )
    except requests.exceptions.ConnectionError as error:
        console.print(f"[yellow]Error de conexión:[/yellow] {error}")
        return Exit(code=1)
    if respuesta.status_code != 200:
        console.print(f"[yellow]Error de conexión:[/yellow] {respuesta.status_code} {respuesta.reason}")
        return Exit(code=1)

    # Validar la respuesta de la API
    try:
        contenido = respuesta.json()
    except ValueError:
        console.print(f"[yellow]Respuesta inesperada:[/yellow] No se pudo decodificar el JSON: {respuesta.content}")
        return Exit(code=1)
    if "success" not in contenido:
        console.print("[yellow]Respuesta inesperada:[/yellow] La respuesta no contiene el campo 'success'")
        return Exit(code=1)
    if contenido["success"] is False:
        console.print(f"[yellow]Error:[/yellow] {contenido['message']}")
        return Exit(code=1)
    if "audiencias" not in contenido:
        console.print("[yellow]Respuesta inesperada:[/yellow] No se encontraron audiencias")
        return Exit(code=1)

    # Inicializar listado de audiencias
    audiencias = []

    # Alimentar el listado
    for audiencia in contenido["audiencias"]:
        try:
            fecha = audiencia.get("fecha")[:10]
        except AttributeError, ValueError:
            fecha = ""
        audiencias.append(
            {
                "fecha": fecha,
                "hora_inicio": audiencia.get("horaInicio"),
                "hora_fin": audiencia.get("horaFin"),
                "numero_expediente": audiencia.get("numeroExpediente"),
                "sala": audiencia.get("sala"),
                "tipo_audiencia": audiencia.get("tipoAudiencia"),
            }
        )

    # Crear una tabla para mostrar las audiencias
    tabla = Table(title=f"Audiencias para la fecha: {fecha}")
    tabla.add_column("Fecha", style="cyan", no_wrap=True)
    tabla.add_column("Hora Inicio", style="green")
    tabla.add_column("Hora Fin", style="green")
    tabla.add_column("Número de Expediente", style="magenta")
    tabla.add_column("Sala", style="yellow")
    tabla.add_column("Tipo de Audiencia", style="blue")
    for audiencia in audiencias:
        tabla.add_row(
            audiencia["fecha"],
            audiencia["hora_inicio"],
            audiencia["hora_fin"],
            audiencia["numero_expediente"],
            audiencia["sala"],
            audiencia["tipo_audiencia"],
        )
    console.print(tabla)


@app.command()
def mostrar(fecha: Annotated[str, Option(help="Fecha en formato YYYY-MM-DD")] = fecha_hoy):
    """Mostrar las audiencias en la terminal"""
    console = Console()
    console.print(f"Mostrando audiencias para la fecha: {fecha}")


@app.command()
def vocear(fecha: Annotated[str, Option(help="Fecha en formato YYYY-MM-DD")] = fecha_hoy):
    """Vocear las audiencias en la terminal"""
    console = Console()
    console.print(f"Voceando audiencias para la fecha: {fecha}")
