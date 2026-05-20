# Proposal: Color-coded logging output con detección TTY

## Problema

El logging estándar actual produce salida en texto plano sin diferenciación visual entre niveles. Al monitorear extracciones en tiempo real, los warnings y errores no destacan del flujo INFO, dificultando la detección rápida de problemas. Adicionalmente el nombre del módulo (`pipelines.components`) es redundante y genera ruido visual.

Salida actual:
```
2026-05-20T14:56:45 [INFO] pipelines.components — Saved: Érase una vez...
2026-05-20T14:57:07 [WARNING] pipelines.components — BATCH SUMMARY: ...
2026-05-20T14:57:15 [ERROR] pipelines.components — AUTO-STOP: Too many blocks.
```

## Objetivo

Mejorar la legibilidad visual del log durante el scraping:
- Colores ANSI por nivel: INFO=verde, WARNING=amarillo, ERROR=rojo, DEBUG=gris
- Formato más compacto: solo hora (HH:MM:SS) sin nombre de módulo
- Detección TTY: colores solo cuando stdout es terminal (no en pipes/archivos)
- Sin nuevas dependencias (stdlib pura)

Salida objetivo:
```
14:56:45 [INFO]     Saved: Érase una vez...
14:57:07 [WARNING]  BATCH SUMMARY: 4 success, 0 blocks
14:57:15 [ERROR]    AUTO-STOP: Too many blocks.
```
(donde [INFO] es verde, [WARNING] es amarillo, [ERROR] es rojo)

## Alcance incluido

- Agregar `ColoredFormatter(logging.Formatter)` a `config/logging_config.py`
- Detectar TTY via `sys.stdout.isatty()` — colores solo en terminal
- Cambiar formato: eliminar nombre de módulo, usar solo hora como timestamp
- Sin nuevas dependencias

## Alcance excluido

- Colores en ficheros de log (solo terminal)
- Cambios en los mensajes de log (solo formato visual)
- Cambios en los niveles de cada logger
- Tests unitarios para el formatter

## Enfoque

1. Crear `ColoredFormatter` en `config/logging_config.py` con códigos ANSI
2. Modificar `setup_logging()` para usar el formatter con color (si TTY) o sin color (si no TTY)
3. Cambiar el formato: eliminar `%(name)s`, usar datefmt `%H:%M:%S`

## Riesgos

- **Ninguno**: Cambio puramente cosmético en `config/logging_config.py`
- El formatter solo agrega códigos ANSI al levelname — el resto del record no se modifica
- La detección TTY asegura compatibilidad con redirección de stdout a archivos

## Preguntas resueltas

- ¿Mantener nombre de módulo? → No, eliminarlo (usuario confirmó)
- ¿Agregar dependencias? → No, stdlib pura
- ¿Colores en archivo/pipe? → No, solo en terminal (detección TTY)
