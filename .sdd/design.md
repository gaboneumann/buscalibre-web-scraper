# Design: Color-coded logging output con detección TTY

## Decisiones de diseño

### D1: ColoredFormatter en lugar de librería externa
- **Elegido**: `ColoredFormatter(logging.Formatter)` custom en `config/logging_config.py`
- **Rechazado**: colorlog, colorama, rich
- **Razón**: Sin nuevas dependencias, control total sobre los códigos ANSI, compatible con stdlib pura

### D2: Detección TTY via sys.stdout.isatty()
- **Elegido**: `sys.stdout.isatty()` con fallback a no-color si excepción
- **Rechazado**: Detectar variable de entorno (TERM, NO_COLOR, etc.)
- **Razón**: isatty() es el estándar de facto, maneja automáticamente pipes, redirecciones, y ejecutables sin interfaz

### D3: Códigos ANSI estándar (no 256-color, no RGB)
- **Elegido**: 8 colores básicos (gris, verde, amarillo, rojo, magenta)
- **Rechazado**: 256-color ANSI, RGB true-color
- **Razón**: Máxima compatibilidad con terminales viejos y remotas (SSH, tmux, screen)

### D4: Formato: solo hora + level + mensaje
- **Elegido**: `%(asctime)s %(levelname)s  %(message)s` con datefmt `%H:%M:%S`
- **Rechazado**: ISO 8601 completo con fecha, nombre de módulo, archivo:línea
- **Razón**: En operación, la fecha es obvia (misma ejecución). El nombre del módulo es ruido — los mensajes son suficientemente descriptivos

### D5: ColoredFormatter añade los `[]`
- **Implementado**: `record.levelname = f"{color}[{record.levelname}]{reset}"`
- **Efecto**: El fmt string no tiene `[]`, ColoredFormatter los añade alrededor del nivel coloreado
- **Razón**: Evita coloreado de los corchetes, solo el nivel obtiene color

## Cambios de archivo

| Archivo | Cambio | Líneas |
|---|---|---|
| `config/logging_config.py` | Agregar `ColoredFormatter`, cambiar `setup_logging()` | +40 líneas, -15 líneas |

## Compatibilidad

- **Python**: 3.8+ (stdlib pura, ningún .syntax moderno)
- **Terminales**: Todas las que soportan ANSI escapes (99%+)
- **Pipes/redirección**: Automáticamente desactiva color (isatty=False)
- **Tests**: No afectados (no capturan stdout)

## Validación

- Formato correcto: `HH:MM:SS [LEVEL]  message`
- Colores en terminal: \033[32m para INFO, \033[33m para WARNING, \033[31m para ERROR
- Sin colores en no-TTY: texto plano limpio
- Env var `SCRAPER_LOG_LEVEL` sigue funcionando (ej. DEBUG)
