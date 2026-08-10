# pjecz-coma-berenices-cli-typer

Interfaz de Linea de Comandos (CLI) para vocear audiencias.

## Objetivos

- Obtener los datos de las audiencias desde las APIs de los sistemas de gestión de información.
- A partir de los tiempos de inicio de las audiencias, generar un plan de voceo diario.
- Ejecutar el voceo de las audiencias en el tiempo programado.
- Marcar como voceadas las audiencias que ya fueron voceadas.
- Reportar el estado de las audiencias voceadas.

## Instalación

Crear el entorno virtual Python 3.14

```bash
python3 -m venv .venv
```

Activar entorno virtual

```bashbash
source .venv/bin/activate
```

Instalar dependencias con `uv`

```bash
uv sync
```

## Configuración

Copiar el archivo de ejemplo `.env.example` a `.env` y configurar las variables de entorno necesarias.

```bash
cp .env.example .env
```

Crear un archivo `.bashrc` en el directorio raíz del proyecto

```bash
# pjecz-coma-berenice-cli-typer

if [ -f ~/.bashrc ]
then
    . ~/.bashrc
fi

if command -v figlet &> /dev/null
then
    figlet Coma Berenice CLI Typer
else
    echo "== Coma Berenice CLI Typer"
fi
echo

if [ -f .env ]
then
    export $(grep -v '^#' .env | xargs)
    echo "-- Variables de entorno"
    echo "   AGENDAMIENTO_AUDIENCIAS_FECHA_API_URL: ${AGENDAMIENTO_AUDIENCIAS_FECHA_API_URL}"
    echo "   AGENDAMIENTO_AUDIENCIAS_PANTALLA_API_URL: ${AGENDAMIENTO_AUDIENCIAS_PANTALLA_API_URL}"
    echo "   AGENDAMIENTO_AUDIENCIAS_API_KEY: ${AGENDAMIENTO_AUDIENCIAS_API_KEY}"
    echo "   TZ: ${TZ}"
    echo "   VOCEADOR_URL: ${VOCEADOR_URL}"
    echo "   VOCEADOR_VOZ: ${VOCEADOR_VOZ}"
    echo "   VOCEADOR_VOZ_VELOCIDAD: ${VOCEADOR_VOZ_VELOCIDAD}"
    echo
fi

if [ -d .venv ]
then
    echo "-- Python Virtual Environment"
    source .venv/bin/activate
    echo "   $(python3 --version)"
    export PYTHONPATH=$(pwd)
    echo "   PYTHONPATH: ${PYTHONPATH}"
    echo
    alias cli="uv run ${PWD}/pjecz_coma_berenices_cli_typer/app.py"
    echo "-- Ejecutar el CLI"
    echo "   cli --help"
    echo
fi
```

## Uso

Cargar las variables de entorno y activar el entorno virtual:

```bash
source .bashrc
```

Ejecutar el CLI:

```bash
cli --help
```
