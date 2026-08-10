# SPEC 02 — Comando mantener_ejecutando para voceo periódico

> **Status:** Draft
> **Depends on:** SPEC 01
> **Date:** 2026-08-10
> **Objective:** Agregar el comando `mantener_ejecutando` en `commands/audiencias.py` que descargue las audiencias del día, se active entre la primera y la última hora de inicio del día, revise cada `n` minutos y vocee las audiencias cuya hora de inicio coincida con la hora actual, evitando duplicados mediante la columna `voceos`.

## Scope

**In:**

- Agregar el subcomando `mantener_ejecutando` en `pjecz_coma_berenices_cli_typer/commands/audiencias.py`.
- Al iniciar, ejecutar automáticamente la misma lógica de descarga que el comando `descargar` para la fecha de hoy.
- Si no existen audiencias para hoy después de descargar, mostrar un mensaje y salir.
- Determinar la `hora_inicio` más temprana y la más tardía entre las audiencias del día.
- Si el comando se invoca antes de la primera hora de inicio, esperar en silencio hasta esa hora.
- Si el comando se invoca después de la última hora de inicio, mostrar un mensaje indicando que no hay nada que hacer y salir.
- Durante el rango activo, revisar cada `n` minutos si hay audiencias con `hora_inicio` igual a la hora y minuto actuales (`HH:MM`).
- Parámetro opcional `--minutos` (entero positivo) para definir el intervalo entre revisiones; valor por defecto `5`.
- En cada revisión con coincidencias, enviar al voceador el mensaje inicial seguido de un mensaje por cada audiencia encontrada, usando la misma estructura de payloads que el comando `vocear`.
- Incrementar en uno la columna `voceos` de cada audiencia individual voceada y omitir aquellas cuyo `voceos` sea mayor o igual a `1`.
- Terminar automáticamente una vez que la hora actual supere la última `hora_inicio` del día.

**Out of scope (for future specs):**

- Permitir especificar una fecha distinta a hoy.
- Descargar audiencias periódicamente durante la ejecución (solo se descarga al inicio).
- Vocear audiencias cuya hora de inicio ya haya pasado tras una interrupción.
- Notificaciones, logs persistentes o métricas del proceso.
- Ejecución como servicio en segundo plano o demonio del sistema operativo.

## Data model

This feature introduces no new data structures. It reuses the `Audiencia` model from SPEC 01 and starts using the existing `voceos` column to prevent duplicate announcements.

## Implementation plan

1. Refactorizar `pjecz_coma_berenices_cli_typer/commands/audiencias.py` para extraer la lógica de descarga de la función `descargar` a una función interna reutilizable (por ejemplo, `_descargar(fecha)`) sin cambiar el comportamiento del comando `descargar`.
2. Agregar la función `mantener_ejecutando` como un nuevo subcomando con el parámetro `--minutos` (entero, valor por defecto `5`).
3. Implementar la validación de entrada: si `--minutos` es menor o igual a cero, mostrar error y salir.
4. Dentro de `mantener_ejecutando`, invocar la función de descarga para la fecha de hoy.
5. Consultar la base de datos para obtener las audiencias de hoy ordenadas por `hora_inicio`.
6. Si no hay registros, mostrar mensaje y salir.
7. Calcular la `hora_inicio` mínima y máxima del día.
8. Si la hora actual es posterior a la máxima, mostrar mensaje de que no hay nada que hacer y salir.
9. Si la hora actual es anterior a la mínima, mostrar mensaje indicando la hora de inicio y dormir hasta ese momento.
10. Entrar en el bucle de revisiones:
    - Calcular la hora actual `HH:MM`.
    - Consultar las audiencias de hoy con `hora_inicio == HH:MM` y `voceos < 1`.
    - Si hay coincidencias, enviar el mensaje inicial y luego un mensaje por cada audiencia, incrementando `voceos` en uno por cada mensaje individual enviado exitosamente.
    - Si el envío al voceador falla, mostrar error y salir.
    - Si la hora actual supera la máxima `hora_inicio`, mostrar mensaje de cierre y salir.
    - Dormir hasta la siguiente revisión según `--minutos`.

## Acceptance criteria

- [ ] El comando `mantener_ejecutando` aparece en la ayuda del grupo `audiencias`.
- [ ] El comando acepta `--minutos N` y usa `5` como valor por defecto.
- [ ] Al iniciar, el comando descarga las audiencias del día de hoy.
- [ ] Si después de descargar no hay audiencias para hoy, muestra un mensaje y termina con código de salida distinto de cero.
- [ ] Si se invoca después de la última hora de inicio del día, muestra un mensaje indicando que no hay nada que hacer y termina.
- [ ] Si se invoca antes de la primera hora de inicio, espera hasta esa hora sin vocear.
- [ ] Durante el rango activo, revisa cada `n` minutos.
- [ ] Vocea el mensaje inicial y un mensaje por cada audiencia cuya `hora_inicio` coincida con la hora actual.
- [ ] No vocea la misma audiencia más de una vez (la columna `voceos` pasa de `0` a `1` y se omite en revisiones posteriores).
- [ ] Termina automáticamente cuando la hora actual supera la última `hora_inicio` del día.

## Decisions

- **Yes:** Descargar automáticamente al inicio dentro de `mantener_ejecutando`. El flujo esperado es ejecutar este comando temprano en el día y así garantiza datos frescos sin depender de que el usuario haya corrido `descargar` antes.
- **No:** No descargar periódicamente durante la ejecución. La descarga al inicio es suficiente para el caso de uso actual.
- **Yes:** Rango de ejecución entre la `hora_inicio` más temprana y la más tardía del día. Evita revisiones innecesarias fuera del horario con audiencias.
- **No:** No vocear audiencias cuya hora ya haya pasado tras una interrupción. La coincidencia exacta `HH:MM` es el criterio simple y predecible.
- **Yes:** Parámetro `--minutos` con valor por defecto `5`. Coincide con la descripción original de revisiones cada cinco minutos.
- **Yes:** Incrementar la columna `voceos` y omitir registros con `voceos >= 1`. Reutiliza el campo añadido en SPEC 01 y evita duplicados sin estado adicional en memoria.
- **Yes:** Mensaje inicial en cada revisión donde haya coincidencias. Alineado con la respuesta del usuario, aunque el mensaje varíe según la primera audiencia de esa revisión.
- **No:** No soportar fechas distintas a hoy. El comando está diseñado para operar sobre el día actual.
- **Yes:** Si el voceador responde con error, el comando termina inmediatamente. Mantiene el mismo comportamiento de fallo rápido del comando `vocear`.

## Risks

| Risk | Mitigation |
| --- | --- |
| Falla de la descarga inicial | Terminar con error; el usuario debe corregir la conexión o la API antes de reintentar. |
| Falla del servicio de voceo durante una revisión | Terminar con error; no se marcan audiencias como voceadas si el envío no fue exitoso. |
| Cambio de la hora del sistema durante la ejecución | El comando depende de `datetime.now(tz=local_tz)`; un cambio brusco puede provocar saltos en el rango o revisiones. |

## What is **not** in this spec

- Soporte para fechas distintas a hoy.
- Descargas periódicas durante la ejecución.
- Voceo de audiencias cuya hora de inicio ya haya pasado.
- Ejecución como servicio o demonio del sistema operativo.
- Logs persistentes, métricas o notificaciones externas.

Cada uno de estos, si llega, tendrá su propio spec.
