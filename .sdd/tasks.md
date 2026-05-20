# Tasks: Color-coded logging output con detección TTY

## Phase 1: Implementation

- [x] 1.1 Agregar `_RESET` y `_LEVEL_COLORS` dict con códigos ANSI a `config/logging_config.py`
- [x] 1.2 Crear `ColoredFormatter(logging.Formatter)` que añade color al levelname
- [x] 1.3 Modificar `setup_logging()` para detectar TTY y usar ColoredFormatter si aplica
- [x] 1.4 Cambiar formato a `%(asctime)s %(levelname)s  %(message)s` con datefmt `%H:%M:%S`

## Phase 2: Verification

- [x] 2.1 Ejecutar tests: `pytest tests/ -m "not network" -v` → todos pasan
- [x] 2.2 Verificar colores en TTY: simular `isatty()=True` y comprobar códigos ANSI presentes
- [x] 2.3 Verificar sin colores en no-TTY: simular `isatty()=False` y comprobar texto plano
- [x] 2.4 Verificar formato: solo hora, sin nombre de módulo

## Phase 3: Closure

- [x] 3.1 Crear `.sdd/design.md`
- [x] 3.2 Crear `.sdd/verify-report.md`
