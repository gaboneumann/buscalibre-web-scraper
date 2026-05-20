# Spec: Color-coded logging output con detección TTY

## Requisitos funcionales

### RF1: ColoredFormatter
- Existe una clase `ColoredFormatter(logging.Formatter)` en `config/logging_config.py`
- Sobreescribe el método `format()` para añadir códigos ANSI al levelname
- Colores por nivel:
  - DEBUG → gris (`\033[90m`)
  - INFO → verde (`\033[32m`)
  - WARNING → amarillo (`\033[33m`)
  - ERROR → rojo (`\033[31m`)
  - CRITICAL → magenta (`\033[35m`)
- Añade `RESET` (`\033[0m`) después del levelname para no colorear el mensaje

### RF2: Detección TTY
- `setup_logging()` usa `ColoredFormatter` si `sys.stdout.isatty()` es `True`
- `setup_logging()` usa `logging.Formatter` estándar (sin color) si no es TTY
- Garantiza que `python main.py > log.txt` no incluya códigos ANSI en el archivo

### RF3: Formato simplificado
- El formato es `%(asctime)s [%(levelname)s]  %(message)s`
- El `datefmt` es `%H:%M:%S` (solo hora, sin fecha)
- El nombre del módulo (`%(name)s`) no aparece en la salida

### RF4: Retrocompatibilidad
- `setup_logging()` mantiene su firma: `def setup_logging() -> None`
- Env var `SCRAPER_LOG_LEVEL` sigue funcionando igual
- Supresión de `playwright` y `urllib3` se mantiene
- Guard contra duplicate handlers se mantiene

## Requisitos no funcionales

- **Sin dependencias nuevas**: Solo stdlib de Python (`logging`, `os`, `sys`)
- **Un solo archivo modificado**: Solo `config/logging_config.py`
- **Tests existentes sin cambios**: Los tests no capturan stdout, no se ven afectados

## Escenarios de uso

### Escenario A: Ejecución en terminal (TTY)
```bash
python main.py
# Salida con colores:
# 14:56:45 [INFO]    Starting book extraction process...
# 14:56:50 [INFO]    [100/100] Extracting: https://...
# 14:57:07 [WARNING] BATCH SUMMARY: 4 success, 0 blocks
# 14:57:15 [ERROR]   AUTO-STOP: Too many blocks.
```

### Escenario B: Redirección a archivo (no TTY)
```bash
python main.py > log.txt
# Salida sin códigos ANSI (texto plano limpio)
```

### Escenario C: Debug mode
```bash
SCRAPER_LOG_LEVEL=DEBUG python main.py
# [DEBUG] en gris, [INFO] en verde, etc.
```

## Criterios de aceptación

1. `[INFO]` se ve en verde en terminal
2. `[WARNING]` se ve en amarillo en terminal
3. `[ERROR]` se ve en rojo en terminal
4. El nombre del módulo NO aparece en los logs
5. El timestamp muestra solo hora (`14:56:45`)
6. `python main.py > archivo.txt` no genera caracteres ANSI en el archivo
7. `setup_logging()` sigue funcionando sin argumentos
8. `SCRAPER_LOG_LEVEL=DEBUG` sigue activando modo verbose
9. Todos los tests existentes siguen pasando

## Casos límite

- Si `sys.stdout.isatty()` lanza excepción (entornos exóticos): fallback a formatter sin color
- Si el nivel de la env var es inválido: fallback a INFO (ya implementado)
