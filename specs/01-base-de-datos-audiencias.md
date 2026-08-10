# SPEC 01 — Base de datos SQLite para audiencias

> **Status:** Draft
> **Depends on:** None
> **Date:** 2026-08-10
> **Objective:** Crear una base de datos SQLite con SQLAlchemy para persistir las audiencias descargadas, incluyendo un contador de voceos inicializado en cero.

## Scope

**In:**

- Agregar SQLAlchemy como dependencia del proyecto en `pyproject.toml`.
- Crear el directorio `pjecz_coma_berenices_cli_typer/models/`.
- Definir el modelo ORM `Audiencia` en `pjecz_coma_berenices_cli_typer/models/audiencias.py`.
- Crear la tabla `audiencias` con las columnas `fecha`, `hora_inicio`, `hora_fin`, `numero_expediente`, `sala`, `tipo_audiencia` (todas `String`) y `voceos` (`Integer`, valor por defecto `0`).
- Usar clave primaria autoincremental `id` y restricción única en (`fecha`, `hora_inicio`, `sala`).
- Persistir automáticamente las audiencias en la base de datos al ejecutar el comando `audiencias descargar`.
- Ubicar el archivo de la base de datos como `audiencias.sqlite3` en el directorio de trabajo actual.

**Out of scope (for future specs):**

- Comandos separados para consultar, editar o eliminar audiencias de la base de datos.
- Migraciones de esquema versionadas.
- Encriptación u otra medida de seguridad sobre el archivo SQLite.
- Cambios al comportamiento de los comandos `mostrar` o `vocear`.

## Data model

```python
# pjecz_coma_berenices_cli_typer/models/audiencias.py

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

Base = declarative_base()


class Audiencia(Base):
    __tablename__ = "audiencias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha: Mapped[str] = mapped_column(String)
    hora_inicio: Mapped[str] = mapped_column(String)
    hora_fin: Mapped[str] = mapped_column(String)
    numero_expediente: Mapped[str] = mapped_column(String)
    sala: Mapped[str] = mapped_column(String)
    tipo_audiencia: Mapped[str] = mapped_column(String)
    voceos: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint(
            "fecha",
            "hora_inicio",
            "sala",
            name="uix_audiencia",
        ),
    )
```

## Implementation plan

1. Agregar `sqlalchemy` a `pyproject.toml` en la sección `project.dependencies` y sincronizar el entorno con `uv sync`.
2. Crear el directorio `pjecz_coma_berenices_cli_typer/models/` con su archivo `__init__.py` vacío.
3. Crear `pjecz_coma_berenices_cli_typer/models/audiencias.py` con la clase ORM `Audiencia`, la tabla `audiencias` y la restricción de unicidad sobre (`fecha`, `hora_inicio`, `sala`).
4. Modificar `pjecz_coma_berenices_cli_typer/commands/audiencias.py` para crear el engine/session contra `sqlite:///audiencias.sqlite3` y persistir o actualizar los registros al finalizar `descargar`, usando la restricción de unicidad para evitar duplicados.
5. Verificar que el archivo `audiencias.sqlite3` se crea en el directorio de trabajo y contiene los registros después de ejecutar `audiencias descargar`.

## Acceptance criteria

- [ ] `pyproject.toml` incluye SQLAlchemy en `project.dependencies`.
- [ ] Existe `pjecz_coma_berenices_cli_typer/models/audiencias.py` con la clase `Audiencia`.
- [ ] La tabla `audiencias` tiene las columnas `fecha`, `hora_inicio`, `hora_fin`, `numero_expediente`, `sala`, `tipo_audiencia` y `voceos`.
- [ ] La columna `voceos` tiene valor por defecto `0`.
- [ ] Existe una restricción única sobre (`fecha`, `hora_inicio`, `sala`).
- [ ] Ejecutar `audiencias descargar` crea el archivo `audiencias.sqlite3` y guarda las audiencias descargadas.
- [ ] Volver a ejecutar `audiencias descargar` con la misma fecha no crea registros duplicados.

## Decisions

- **Yes:** SQLite como motor de base de datos. Es suficiente para datos locales y no requiere servidor.
- **No:** Tipos de fecha y hora nativos. Se usan `String` para simplificar la integración con los valores que ya devuelve la API.
- **Yes:** Archivo `audiencias.sqlite3` en el directorio de trabajo actual. Fácil de encontrar y acorde a la respuesta del usuario.
- **No:** Ruta configurable por variable de entorno en este spec. Se deja para una especificación futura si es necesario.
- **Yes:** Columna `voceos` como `Integer` con valor por defecto `0`.
- **Yes:** Clave primaria autoincremental `id` más restricción única compuesta. Permite identificadores internos simples sin perder la unicidad funcional.

## Risks

| Risk | Mitigation |
| --- | --- |
| Duplicados si cambia el criterio de unicidad | Documentar en el spec que la unicidad es sobre (`fecha`, `hora_inicio`, `numero_expediente`, `sala`). |
| El comando `descargar` puede fallar antes de persistir | Mantener la validación actual antes de tocar la base de datos; persistir solo si la respuesta de la API es válida. |

## What is **not** in this spec

- Comandos para administrar el contenido de la base de datos.
- Migraciones de esquema versionadas.
- Cambios a los comandos `mostrar` o `vocear`.

Cada uno de estos, si llega, tendrá su propio spec.
