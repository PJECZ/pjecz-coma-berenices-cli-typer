"""
Command audiencias
"""

import re
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

CATALOGO_IDS_AUTORIDADES = {
    1: {
        "clave": "SLT-J1-MER",
        "descripcion": "Juzgado Primero de Primera instancia en Materia Mercantil del Distrito Judicial de Saltillo",
        "id+materia": 5,
    },
    2: {
        "clave": "SLT-J2-MER",
        "descripcion": "Juzgado Segundo de Primera instancia en Materia Mercantil del Distrito Judicial de Saltillo",
        "id+materia": 5,
    },
    3: {
        "clave": "SLT-TL",
        "descripcion": "Tribunal Laboral del Distrito Judicial de Saltillo",
        "id+materia": 1,
    },
    4: {
        "clave": "SLT-J3-MER",
        "descripcion": "Juzgado Tercero de Primera instancia en Materia Mercantil del Distrito Judicial de Saltillo",
        "id+materia": 5,
    },
    5: {
        "clave": "SLT-J1L-CIV",
        "descripcion": "Juzgado Primero Letrado de Primera instancia en Materia Civil del Distrito Judicial de Saltillo",
        "id+materia": 6,
    },
    6: {
        "clave": "SLT-J2L-CIV",
        "descripcion": "Juzgado Segundo Letrado de Primera instancia en Materia Civil del Distrito Judicial de Saltillo",
        "id+materia": 6,
    },
    7: {
        "clave": "SLT-JU-MER",
        "descripcion": "Juzgado Único de Primera instancia en Materia Mercantil del Distrito Judicial de Saltillo",
        "id+materia": 5,
    },
}

CATALOGO_IDS_MATERIAS = {
    1: "Laboral",
    2: "Familiar Tradiccional",
    3: "Familiar Oral",
    4: "Civil",
    5: "Mercantil",
    6: "Letrado",
    7: "Penal",
}

app = Typer(name="audiencias", help="Comando para vocear audiencias")

settings = get_settings()
local_tz = timezone(settings.TZ)
fecha_hoy = datetime.now(tz=local_tz).strftime("%Y-%m-%d")

engine = create_engine("sqlite:///audiencias.sqlite3")
Session = sessionmaker(bind=engine)


def _descargar(fecha: str, id_autoridad: int, id_materia: int, console: Console) -> None:
    """Descargar las audiencias de la API y persistirlas en la base de datos"""
    console.print(f"[green]Descargando audiencias para la fecha:[/green] {fecha}")

    # Validar que AGENDAMIENTO_AUDIENCIAS_VOCEADOR_API_URL esté definido
    if settings.AGENDAMIENTO_AUDIENCIAS_VOCEADOR_API_URL == "":
        console.print("[red]Falta la variable de entorno AGENDAMIENTO_AUDIENCIAS_VOCEADOR_API_URL[/red]")
        raise Exit(code=1)

    # Validar que fecha sea YYYY-MM-DD
    if bool(re.match(r'^\d{4}-\d{2}-\d{2}$', fecha)) is False:
        console.print("[red]Fecha NO válida[/red]")
        raise Exit(code=1)

    # Definir payload para AGENDAMIENTO_AUDIENCIAS_VOCEADOR_API_URL
    payload = {
        "idAutoridad": id_autoridad,
        "idMateria": id_materia,
        "fecha": fecha,
    }

    # Consultar la API
    try:
        respuesta = requests.post(
            url=settings.AGENDAMIENTO_AUDIENCIAS_VOCEADOR_API_URL,
            headers={"X-Api-Key": settings.AGENDAMIENTO_AUDIENCIAS_API_KEY},
            timeout=settings.AGENDAMIENTO_AUDIENCIAS_TIMEOUT,
            json=payload,
        )
    except requests.exceptions.ConnectionError as error:
        console.print(f"[red]Error de conexión:[/red] {error}")
        raise Exit(code=1) from error
    if respuesta.status_code != 200:
        console.print(f"[red]Error de conexión:[/red] {respuesta.status_code} {respuesta.reason}")
        raise Exit(code=1)

    # Validar la respuesta de la API
    try:
        contenido = respuesta.json()
    except ValueError:
        console.print(f"[red]Respuesta inesperada:[/red] No se pudo decodificar el JSON: {respuesta.content}")
        raise Exit(code=1)
    if "success" not in contenido:
        console.print("[red]Respuesta inesperada:[/red] La respuesta no contiene el campo 'success'")
        raise Exit(code=1)
    if contenido["success"] is False:
        console.print(f"[red]Respuesta inesperada:[/red] Success es falso. {contenido.get('message')}")
        raise Exit(code=1)
    if "audiencias" not in contenido:
        console.print("[red]Respuesta inesperada:[/red] No se encontraron audiencias")
        raise Exit(code=1)

    # Ejemplo de audiencia
    #
    # "numeroExpediente": "263/2026-JLM1",
    # "sala": "Sala 1",
    # "tipoAudiencia": "Audiencia de alegatos",
    # "horaInicio": "09:00",
    # "horaFin": "10:00",
    # "juez": "LUIS ARGENIS LUNA CRUZ",
    # "secretario": "MANUELA LEIJA MENDOZA",
    # "autoridad": "Juzgado Único de Primera instancia en Materia Mercantil del Distrito Judicial de Saltillo",
    # "materia": "Mercantil",
    # "fecha": "2026-08-12T09:00:00"

    # Alimentar el listado
    listado = []
    for item in contenido["audiencias"]:
        try:
            fecha_audiencia = item.get("fecha")[:10]
        except (AttributeError, ValueError):
            fecha_audiencia = ""
        try:
            numero_sala = int(item.get("sala").split(" ")[1])
        except (AttributeError, ValueError):
            numero_sala = 0
        listado.append(
            {
                "fecha": fecha_audiencia,
                "hora_inicio": item.get("horaInicio"),
                "hora_fin": item.get("horaFin"),
                "materia": item.get("materia"),
                "autoridad": item.get("autoridad"),
                "numero_expediente": item.get("numeroExpediente"),
                "sala": item.get("sala"),
                "numero_sala": numero_sala,
                "tipo_audiencia": item.get("tipoAudiencia"),
            }
        )

    # Persistir las audiencias en la base de datos
    actualizados_contador = 0
    insertados_contador = 0
    sin_cambios_contador = 0
    Base.metadata.create_all(engine)
    session = Session()
    try:
        for item in listado:
            fue_actualizado = False
            fue_insertado = False
            # Si hubiera una actualizacion por retraso, se debe de encontrar por fecha, materia, autoridad y numero_expediente
            existente = (
                session.query(Audiencia)
                .filter_by(
                    fecha=item["fecha"],
                    materia=item["materia"],
                    autoridad=item["autoridad"],
                    numero_expediente=item["numero_expediente"],
                )
                .first()
            )
            # Al encontrar coincidencia, se actualiza la hora_inicio, hora_fin, sala y tipo_audiencia
            if existente:
                if existente.hora_inicio != item["hora_inicio"]:
                    existente.hora_inicio = item["hora_inicio"]
                    fue_actualizado = True
                if existente.hora_fin != item["hora_fin"]:
                    existente.hora_fin = item["hora_fin"]
                    fue_actualizado = True
                if existente.sala != item["sala"]:
                    existente.sala = item["sala"]
                    try:
                        existente.numero_sala = int(item.get("sala").strip(" ")[1])
                    except (AttributeError, ValueError):
                        existente.numero_sala = 0
                    fue_actualizado = True
                if existente.tipo_audiencia != item["tipo_audiencia"]:
                    existente.tipo_audiencia = item["tipo_audiencia"]
                    fue_actualizado = True
                if fue_actualizado:
                    actualizados_contador += 1
            else:
                session.add(Audiencia(**item))
                fue_insertado = True
                insertados_contador += 1
            if fue_actualizado is False and fue_insertado is False:
                sin_cambios_contador += 1
        session.commit()
    finally:
        session.close()

    # Mostrar contadores
    if actualizados_contador > 1:
        console.print(f"[yellow]- Se actualizaron:[/yellow] {fue_actualizado}")
    if insertados_contador > 1:
        console.print(f"[green]- Se insertaron:[/green] {insertados_contador}")
    if sin_cambios_contador > 1:
        console.print(f"[cyan]- Sin cambios:[/cyan] {insertados_contador}")


@app.command()
def descargar(fecha: Annotated[str, Option(help="Fecha en formato YYYY-MM-DD")] = fecha_hoy):
    """Descargar las audiencias"""
    id_autoridad = 0  # Todas las autoridades
    id_materia = 0  # Todas las materias
    console = Console()
    try:
        _descargar(fecha, id_autoridad, id_materia, console)
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
        console.print(f"[red]Error de conexión al servicio de voceo:[/red] {error}")
        raise Exit(code=1) from error
    if respuesta.status_code != 200:
        console.print(f"[red]Error de conexión:[/red] {respuesta.status_code} {respuesta.reason}")
        raise Exit(code=1)

    # Validar la respuesta del servicio de voceo
    try:
        contenido = respuesta.json()
    except ValueError:
        console.print(f"[red]Respuesta inesperada:[/red] No se pudo decodificar el JSON: {respuesta.content}")
        raise Exit(code=1)
    if "success" not in contenido:
        console.print("[red]Respuesta inesperada:[/red] La respuesta no contiene el campo 'success'")
        raise Exit(code=1)
    if contenido["success"] is False:
        console.print(f"[red]Respuesta inesperada:[/red] Success es falso. {contenido.get('message')}")
        raise Exit(code=1)


@app.command()
def mantener_ejecutando(
    minutos: Annotated[int, Option(help="Intervalo en minutos (1, 5, 10, 15 o 30) entre revisiones")] = 5,
):
    """Mantener ejecutando el voceo de audiencias"""
    console = Console()

    # Validar el intervalo
    if minutos not in (1, 5, 10, 15, 30):
        console.print("[red]Error:[/red] El intervalo de minutos debe ser 1, 5, 10, 15 o 30")
        raise Exit(code=1)

    # Descargar las audiencias del día de hoy
    id_autoridad = 0  # Todas las autoridades
    id_materia = 0  # Todas las materias
    console = Console()
    try:
        _descargar(fecha_hoy, id_autoridad, id_materia, console)
    except Exit:
        console.print("[red]Error:[/red] Falló la descarga de las audiencias de hoy")
        raise Exit(code=1)

    # Consultar la base de datos para obtener las audiencias de hoy
    Base.metadata.create_all(engine)
    session = Session()
    try:
        audiencias_hoy = (
            session.query(Audiencia)
            .filter_by(fecha=fecha_hoy)
            .order_by(Audiencia.hora_inicio, Audiencia.numero_sala)
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
    siguiente_incremento_minutos = minutos - ahora.minute % minutos

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

        # Consultar audiencias de esta hora que aún NO se hayan voceado
        session = Session()
        try:
            coincidencias = (
                session.query(Audiencia)
                .filter_by(fecha=fecha_hoy, hora_inicio=hora_actual_str)
                .filter(Audiencia.voceos < 1)
                .order_by(Audiencia.hora_inicio, Audiencia.numero_sala)
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
                console.print(f"- [blue]Materia:[/blue] {audiencia.materia}")
                console.print(f"- [blue]Expediente:[/blue] {audiencia.numero_expediente}")
                console.print(f"- [blue]Sala:[/blue] {audiencia.sala}")
                console.print(f"- [blue]Tipo de audiencia:[/blue] {audiencia.tipo_audiencia}")
                mensaje = f"Para la {audiencia.tipo_audiencia} en materia {audiencia.materia} del expediente {audiencia.numero_expediente} pase a la {audiencia.sala}"
                console.print(f"[cyan]Vocear:[/cyan] {mensaje}")
                _enviar_mensaje_voceador(mensaje, voceador_id, console)

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
        siguiente_incremento_minutos = minutos


def _mostrar(fecha: str, audiencias: list[Audiencia], console: Console):
    """Mostrar las audiencias en una tabla"""
    tabla = Table(title=f"Audiencias para la fecha: {fecha}")
    tabla.add_column("Fecha", style="cyan", no_wrap=True)
    tabla.add_column("Hora Inicio", style="green")
    tabla.add_column("Hora Fin", style="green")
    tabla.add_column("Tipo de Audiencia", style="blue")
    tabla.add_column("Materia", style="magenta")
    # tabla.add_column("Autoridad", style="magenta")
    tabla.add_column("Número de Expediente", style="magenta")
    tabla.add_column("Sala", style="yellow")
    for audiencia in audiencias:
        tabla.add_row(
            audiencia.fecha,
            audiencia.hora_inicio,
            audiencia.hora_fin,
            audiencia.tipo_audiencia,
            audiencia.materia,
            # audiencia.autoridad,
            audiencia.numero_expediente,
            audiencia.sala,
        )
    console.print(tabla)

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
            .order_by(Audiencia.hora_inicio, Audiencia.numero_sala)
            .all()
        )
    finally:
        session.close()

    # Si no hay audiencias, mostrar un mensaje
    if not audiencias:
        console.print(f"[yellow]No se encontraron audiencias para la fecha: {fecha}[/yellow]")
        return Exit(code=1)

    # Mostrar las audiencias en una tabla
    _mostrar(fecha, audiencias, console)

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
        audiencias = (
            session.query(Audiencia)
            .filter_by(fecha=fecha)
            .filter_by(hora_inicio=hora_inicio)
            .order_by(Audiencia.hora_inicio, Audiencia.numero_sala)
            .all()
        )  # Ordenado por materia, sala
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
    _enviar_mensaje_voceador(mensaje_inicial, voceador_id, console)

    # Incrementar el ID para la siguiente audiencia
    voceador_id += 1

    # Vocear las audiencias
    materia_actual = ""
    for audiencia in audiencias:
        if materia_actual == "" or materia_actual != audiencia.materia:
            materia_actual = audiencia.materia

        console.print("[green]Voceando audiencia:[/green]")
        console.print(f"- [blue]Materia:[/blue] {audiencia.materia}")
        console.print(f"- [blue]Expediente:[/blue] {audiencia.numero_expediente}")
        console.print(f"- [blue]Sala:[/blue] {audiencia.sala}")
        console.print(f"- [blue]Tipo de audiencia:[/blue] {audiencia.tipo_audiencia}")
        mensaje = f"Para la {audiencia.tipo_audiencia} en materia {audiencia.materia} del expediente {audiencia.numero_expediente} pase a la {audiencia.sala}"
        console.print(f"[cyan]Vocear:[/cyan] {mensaje}")
        _enviar_mensaje_voceador(mensaje, voceador_id, console)

        # Incrementar el ID para la siguiente audiencia
        voceador_id += 1
