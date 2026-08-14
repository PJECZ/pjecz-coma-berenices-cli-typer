"""
Command audiencias
"""

import time
from datetime import datetime
from typing import Annotated

import requests
from pytz import timezone
from rich.console import Console
from rich.table import Table
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typer import Exit, Option, Typer

from pjecz_coma_berenices_cli_typer.config.settings import get_settings
from pjecz_coma_berenices_cli_typer.models.audiencias import Audiencia, Base

app = Typer(name="audiencias", help="Comando para vocear audiencias")

settings = get_settings()
local_tz = timezone(settings.TZ)
fecha_hoy = datetime.now(tz=local_tz).strftime("%Y-%m-%d")

engine = create_engine("sqlite:///audiencias.sqlite3")
Session = sessionmaker(bind=engine)


def _descargar(fecha: str, console: Console) -> list[dict]:
    """Descargar las audiencias de la API y persistirlas en la base de datos"""
    console.print(f"[green]Descargando audiencias para la fecha:[/green] {fecha}")

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
                params={"fecha": fecha},
            )
    except requests.exceptions.ConnectionError as error:
        console.print(f"[yellow]Error de conexión:[/yellow] {error}")
        raise Exit(code=1) from error
    if respuesta.status_code != 200:
        console.print(f"[yellow]Error de conexión:[/yellow] {respuesta.status_code} {respuesta.reason}")
        raise Exit(code=1)

    # Validar la respuesta de la API
    try:
        contenido = respuesta.json()
    except ValueError:
        console.print(f"[yellow]Respuesta inesperada:[/yellow] No se pudo decodificar el JSON: {respuesta.content}")
        raise Exit(code=1)
    if "success" not in contenido:
        console.print("[yellow]Respuesta inesperada:[/yellow] La respuesta no contiene el campo 'success'")
        raise Exit(code=1)
    if contenido["success"] is False:
        console.print(f"[yellow]Error:[/yellow] {contenido['message']}")
        raise Exit(code=1)
    if "audiencias" not in contenido:
        console.print("[yellow]Respuesta inesperada:[/yellow] No se encontraron audiencias")
        raise Exit(code=1)

    # Inicializar listado de audiencias
    audiencias = []

    # Alimentar el listado
    for audiencia in contenido["audiencias"]:
        try:
            fecha_audiencia = audiencia.get("fecha")[:10]
        except (AttributeError, ValueError):
            fecha_audiencia = ""
        audiencias.append(
            {
                "fecha": fecha_audiencia,
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

    # Persistir las audiencias en la base de datos
    Base.metadata.create_all(engine)
    session = Session()
    try:
        for audiencia in audiencias:
            existente = (
                session.query(Audiencia)
                .filter_by(
                    fecha=audiencia["fecha"],
                    hora_inicio=audiencia["hora_inicio"],
                    sala=audiencia["sala"],
                )
                .first()
            )
            if existente:
                existente.hora_fin = audiencia["hora_fin"]
                existente.numero_expediente = audiencia["numero_expediente"]
                existente.tipo_audiencia = audiencia["tipo_audiencia"]
            else:
                session.add(Audiencia(**audiencia))
        session.commit()
    finally:
        session.close()

    return audiencias


@app.command()
def descargar(fecha: Annotated[str, Option(help="Fecha en formato YYYY-MM-DD")] = fecha_hoy):
    """Descargar las audiencias"""
    console = Console()
    try:
        _descargar(fecha, console)
    except Exit:
        pass


def _enviar_mensaje_voceador(mensaje: str, voceador_id: int, console: Console) -> None:
    """Enviar un mensaje al servicio de voceo"""
    payload = {
        "id": voceador_id,
        "mensaje": mensaje,
        "tiempo": datetime.now(tz=local_tz).isoformat(),
        "ttl_segundos": 60,
    }
    try:
        respuesta = requests.post(settings.VOCEADOR_URL, json=payload)
    except requests.exceptions.ConnectionError as error:
        console.print(f"[yellow]Error de conexión al servicio de voceo:[/yellow] {error}")
        raise Exit(code=1) from error
    if respuesta.status_code != 200:
        console.print(f"[yellow]Error de conexión:[/yellow] {respuesta.status_code} {respuesta.reason}")
        raise Exit(code=1)

    # Validar la respuesta del servicio de voceo
    try:
        contenido = respuesta.json()
    except ValueError:
        console.print(f"[yellow]Respuesta inesperada:[/yellow] No se pudo decodificar el JSON: {respuesta.content}")
        raise Exit(code=1)
    if "success" not in contenido:
        console.print("[yellow]Respuesta inesperada:[/yellow] La respuesta no contiene el campo 'success'")
        raise Exit(code=1)
    if contenido["success"] is False:
        console.print(f"[yellow]Error:[/yellow] {contenido['message']}")
        raise Exit(code=1)


@app.command()
def mantener_ejecutando(
    minutos: Annotated[int, Option(help="Intervalo en minutos (5, 10, 15 o 30) entre revisiones")] = 5,
):
    """Mantener ejecutando el voceo de audiencias"""
    console = Console()

    # Validar que el intervalo sea positivo
    if minutos <= 0:
        console.print("[yellow]Error:[/yellow] El intervalo de minutos debe ser mayor a cero")
        raise Exit(code=1)

    # Validar que el intervalo sea 5, 10, 15 o 30
    if minutos not in (5, 10, 15, 30):
        console.print("[yellow]Error:[/yellow] El intervalo de minutos debe ser 5, 10, 15 o 30")
        raise Exit(code=1)

    # Descargar las audiencias del día de hoy
    try:
        _descargar(fecha_hoy, console)
    except Exit as error:
        raise error

    # Consultar la base de datos para obtener las audiencias de hoy
    Base.metadata.create_all(engine)
    session = Session()
    try:
        audiencias_hoy = (
            session.query(Audiencia)
            .filter_by(fecha=fecha_hoy)
            .order_by(Audiencia.hora_inicio)
            .all()
        )
    finally:
        session.close()

    # Si no hay audiencias, mostrar un mensaje y salir
    if not audiencias_hoy:
        console.print(f"[yellow]No se encontraron audiencias para la fecha: {fecha_hoy}[/yellow]")
        raise Exit(code=1)

    # Calcular la hora de inicio mínima y máxima del día
    hora_inicio_minima_str = audiencias_hoy[0].hora_inicio
    hora_inicio_maxima_str = audiencias_hoy[-1].hora_inicio
    hora_inicio_minima = datetime.strptime(hora_inicio_minima_str, "%H:%M").time()
    hora_inicio_maxima = datetime.strptime(hora_inicio_maxima_str, "%H:%M").time()

    # Definir la hora truncada
    ahora = datetime.now(tz=local_tz)
    minuto_truncado = (ahora.minute // minutos) * minutos
    hora_actual_truncada = ahora.replace(minute=minuto_truncado , second=0, microsecond=0).time()

    # Definir el siguiente incremento
    siguiente_incremento_minutos = ahora.minute % minutos
    if siguiente_incremento_minutos == 0:
        siguiente_incremento_minutos = minutos - (ahora.minute % minutos)

    # Si la hora actual es posterior a la máxima, no hay nada que hacer
    if hora_actual_truncada > hora_inicio_maxima:
        console.print("[yellow]No hay nada que hacer, la última hora de inicio ya pasó.[/yellow]")
        raise Exit(code=0)

    # Si la hora actual es anterior a la mínima, esperar hasta esa hora
    if hora_actual_truncada < hora_inicio_minima:
        hora_inicio_minima_dt = local_tz.localize(datetime.combine(ahora.date(), hora_inicio_minima))
        segundos_hasta_inicio = (hora_inicio_minima_dt - ahora).total_seconds()
        if segundos_hasta_inicio > 0:
            console.print(f"[green]Esperando hasta la primera hora de inicio:[/green] {hora_inicio_minima_str}")
            time.sleep(segundos_hasta_inicio)

    # Bucle de revisiones
    while True:
        ahora = datetime.now(tz=local_tz)
        hora_actual_str = ahora.strftime("%H:%M")
        hora_actual_truncada = ahora.replace(second=0, microsecond=0).time()

        # Terminar si la hora actual supera la última hora de inicio
        if hora_actual_truncada > hora_inicio_maxima:
            console.print("[green]Terminó la jornada de audiencias.[/green]")
            break

        # Consultar audiencias de esta hora que aún no se hayan voceado
        session = Session()
        try:
            coincidencias = (
                session.query(Audiencia)
                .filter_by(fecha=fecha_hoy, hora_inicio=hora_actual_str)
                .filter(Audiencia.voceos < 1)
                .order_by(Audiencia.hora_inicio)
                .all()
            )
        finally:
            session.close()

        if coincidencias:
            # Vocear el mensaje inicial
            mensaje_inicial = f"Inicia la jornada de audiencias de las {hora_actual_str}"
            console.print(f"[cyan]Voceando:[/cyan] {mensaje_inicial}")
            _enviar_mensaje_voceador(mensaje_inicial, 1000, console)

            # Vocear cada audiencia encontrada
            voceador_id = 1001
            for audiencia in coincidencias:
                console.print("[green]Voceando audiencia:[/green]")
                console.print(f"- [blue]Fecha:[/blue] {audiencia.fecha}")
                console.print(f"- [blue]Hora inicio-fin:[/blue] {audiencia.hora_inicio} - {audiencia.hora_fin}")
                console.print(f"- [blue]Expediente:[/blue] {audiencia.numero_expediente}")
                console.print(f"- [blue]Sala:[/blue] {audiencia.sala}")
                console.print(f"- [blue]Tipo de audiencia:[/blue] {audiencia.tipo_audiencia}")
                voceo = f"Para la {audiencia.tipo_audiencia} del expediente {audiencia.numero_expediente} pase a la {audiencia.sala}"
                console.print(f"[cyan]Vocear:[/cyan] {voceo}")
                _enviar_mensaje_voceador(voceo, voceador_id, console)

                # Incrementar el contador de voceos
                session_actualizar = Session()
                try:
                    audiencia_actualizada = session_actualizar.query(Audiencia).filter_by(id=audiencia.id).first()
                    if audiencia_actualizada:
                        audiencia_actualizada.voceos += 1
                        session_actualizar.commit()
                finally:
                    session_actualizar.close()
                voceador_id += 1

        # Dormir hasta la siguiente revisión
        console.print(f"[green]Bloque[/green] [white]{hora_actual_str}[/white], [green]esperando {siguiente_incremento_minutos} minutos...[/green]")
        time.sleep(siguiente_incremento_minutos * 60)
        siguiente_incremento_minutos = max(siguiente_incremento_minutos, minutos)


@app.command()
def mostrar(fecha: Annotated[str, Option(help="Fecha en formato YYYY-MM-DD")] = fecha_hoy):
    """Mostrar las audiencias en la terminal"""
    console = Console()
    console.print(f"[green]Mostrando audiencias para la fecha:[/green] {fecha}")

    # Consultar la base de datos para obtener las audiencias
    Base.metadata.create_all(engine)
    session = Session()
    try:
        audiencias = (
            session.query(Audiencia)
            .filter_by(fecha=fecha)
            .order_by(Audiencia.hora_inicio)
            .all()
        )
    finally:
        session.close()

    # Si no hay audiencias, mostrar un mensaje
    if not audiencias:
        console.print(f"[yellow]No se encontraron audiencias para la fecha: {fecha}[/yellow]")
        return Exit(code=1)

    # Mostrar las audiencias en una tabla
    tabla = Table(title=f"Audiencias para la fecha: {fecha}")
    tabla.add_column("Fecha", style="cyan", no_wrap=True)
    tabla.add_column("Hora Inicio", style="green")
    tabla.add_column("Hora Fin", style="green")
    tabla.add_column("Número de Expediente", style="magenta")
    tabla.add_column("Sala", style="yellow")
    tabla.add_column("Tipo de Audiencia", style="blue")
    for audiencia in audiencias:
        tabla.add_row(
            audiencia.fecha,
            audiencia.hora_inicio,
            audiencia.hora_fin,
            audiencia.numero_expediente,
            audiencia.sala,
            audiencia.tipo_audiencia,
        )
    console.print(tabla)


@app.command()
def vocear(
    fecha: Annotated[str, Option(help="Fecha en formato YYYY-MM-DD")] = fecha_hoy,
    hora_inicio: Annotated[str, Option(help="Hora de inicio en formato HH:MM")] = "",
):
    """Vocear las audiencias"""
    console = Console()
    console.print(f"[green]Voceando audiencias para la fecha:[/green] {fecha}")

    # Si hora_inicio no es proporcionada, determinar la hora_inicio a partir del tiempo del sistema hacia atrás en bloques de 15 miniutos
    if not hora_inicio:
        ahora = datetime.now(tz=local_tz)
        minuto = (ahora.minute // 15) * 15
        hora_inicio = ahora.replace(minute=minuto, second=0, microsecond=0).strftime("%H:%M")
        console.print(f"[green]Se usará la hora de inicio más cercana hacia atrás:[/green] {hora_inicio}")

    # Consultar la base de datos para obtener las audiencias
    Base.metadata.create_all(engine)
    session = Session()
    try:
        audiencias = session.query(Audiencia).filter_by(fecha=fecha)
        if hora_inicio:
            audiencias = audiencias.filter_by(hora_inicio=hora_inicio)
        audiencias = audiencias.order_by(Audiencia.hora_inicio).all()
    finally:
        session.close()

    # Si no hay audiencias, mostrar un mensaje
    if not audiencias:
        if hora_inicio:
            console.print(f"[yellow]No se encontraron audiencias para la fecha: {fecha} y hora: {hora_inicio}[/yellow]")
        else:
            console.print(f"[yellow]No se encontraron audiencias para la fecha: {fecha}[/yellow]")
        return Exit(code=1)

    # Inicializar el ID que requiere el servicio de voceo
    voceador_id = 1000

    # Vocear la hora de inicio de la primera audiencia
    primera_audiencia = audiencias[0]
    mensaje_inicial = f"Inicia la jornada de audiencias de las {primera_audiencia.hora_inicio}"
    console.print(f"[cyan]Voceando:[/cyan] {mensaje_inicial}")

    # Enviar al servicio de voceo
    payload = {
        "id": voceador_id,
        "mensaje": mensaje_inicial,
        "tiempo": datetime.now(tz=local_tz).isoformat(),
        "ttl_segundos": 60,
    }
    try:
        respuesta = requests.post(settings.VOCEADOR_URL, json=payload)
    except requests.exceptions.ConnectionError as error:
        console.print(f"[yellow]Error de conexión al servicio de voceo:[/yellow] {error}")
        return Exit(code=1)
    if respuesta.status_code != 200:
        console.print(f"[yellow]Error de conexión:[/yellow] {respuesta.status_code} {respuesta.reason}")
        return Exit(code=1)

    # Validar la respuesta del servicio de voceo
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

    # Incrementar el ID para la siguiente audiencia
    voceador_id += 1

    # Vocear las audiencias
    for audiencia in audiencias:
        console.print("[green]Voceando audiencia:[/green]")
        console.print(f"- [blue]Fecha:[/blue] {audiencia.fecha}")
        console.print(f"- [blue]Hora inicio-fin:[/blue] {audiencia.hora_inicio} - {audiencia.hora_fin}")
        console.print(f"- [blue]Expediente:[/blue] {audiencia.numero_expediente}")
        console.print(f"- [blue]Sala:[/blue] {audiencia.sala}")
        console.print(f"- [blue]Tipo de audiencia:[/blue] {audiencia.tipo_audiencia}")
        voceo = f"Para la {audiencia.tipo_audiencia} del expediente {audiencia.numero_expediente} pase a la {audiencia.sala}"
        console.print(f"[cyan]Vocear:[/cyan] {voceo}")

        # Enviar al servicio de voceo
        payload = {
            "id": voceador_id,
            "mensaje": voceo,
            "tiempo": datetime.now(tz=local_tz).isoformat(),
            "ttl_segundos": 60,
        }
        try:
            respuesta = requests.post(settings.VOCEADOR_URL, json=payload)
        except requests.exceptions.ConnectionError as error:
            console.print(f"[yellow]Error de conexión al servicio de voceo:[/yellow] {error}")
            return Exit(code=1)
        if respuesta.status_code != 200:
            console.print(f"[yellow]Error de conexión:[/yellow] {respuesta.status_code} {respuesta.reason}")
            return Exit(code=1)

        # Validar la respuesta del servicio de voceo
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

        # Incrementar el ID para la siguiente audiencia
        voceador_id += 1
