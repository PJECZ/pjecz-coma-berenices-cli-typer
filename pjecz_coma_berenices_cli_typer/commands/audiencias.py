"""
Command audiencias
"""

from datetime import datetime
from typing import Annotated

import requests
from pytz import timezone
from rich.console import Console
from typer import Option, Typer

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
        respuesta = requests.get(
            url=settings.SAJI_API_BUSCAR_AGENDA_URL,
            headers={"X-Api-Key": settings.SAJI_API_KEY},
            timeout=60,
        )
    except requests.exceptions.ConnectionError as error:
        return {
            "success": False,
            "message": f"Error de conexión: {error}",
            "data": [],
        }
    if respuesta.status_code != 200:
        return {
            "success": False,
            "message": f"Error al consultar: Código de estado {respuesta.status_code}",
            "data": [],
        }

    # Validar la respuesta de la API
    try:
        contenido = respuesta.json()
    except ValueError:
        return {
            "success": False,
            "message": "Respuesta inesperada: No se pudo decodificar el JSON",
            "data": [],
        }
    if "success" not in contenido:
        return {
            "success": False,
            "message": "Respuesta inesperada",
            "data": [],
        }
    if contenido["success"] is False:
        return {
            "success": False,
            "message": contenido["message"],
            "data": [],
        }
    if "audiencias" not in contenido:
        return {
            "success": False,
            "message": "Respuesta inesperada: No se encontraron audiencias",
            "data": [],
        }

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
