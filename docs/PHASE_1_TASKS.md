# Phase 1: Smart Retry — Task Breakdown
**Status**: Implementation Complete  
**Date Created**: 2026-05-14  
**Entorno**: Ubuntu 24.04 LTS

---

## Context

Part of the ETL Pipeline Architecture Refactor. See:
- **[MIGRATION.md](MIGRATION.md)** for overview of all phases
- **[TECHNICAL.md](TECHNICAL.md)** for anti-detection architecture
- **[README.md](README.md)** for documentation index

---

## Overview

Implementar **exponential backoff + PRODUCT_PER_PAGE adaptativo** para mejorar resiliencia ante bloques WAF.

**Fórmula HTTP**: `6s → 12s → 24s` (base=6, máx 3 intentos)  
**Fórmula Policy**: `45s → 90s → 180s` (base=45, máx 3 intentos)  
**Adaptación**: -15% en bloques, +10% sin bloques  
**Backward Compatible**: Sin parámetros = comportamiento original  
**Testing**: Solo validación manual (sin tests unitarios)

---

## Task 1.1: core/client.py — Exponential Backoff HTTP

**Ubicación**: Líneas 128-131 (WAF retry logic)

**Cambios**:
1. Reemplazar el retry único con un loop exponencial (máx 3 intentos)
2. Calcular delay con: `base_delay × (2^attempt) + jitter(±20%)`
3. Base por defecto: 6 segundos
4. Logging: `"RETRY attempt {n}/3 on {url} with {wait:.1f}s wait..."`

**Pseudocódigo**:
```python
backoff_base_http = 6
attempt = 1
while attempt <= 3:
    if attempt > 1:
        delay = backoff_base_http * (2 ** (attempt - 1))
        jitter = random.uniform(0.8, 1.2)
        wait = delay * jitter
        print(f"RETRY attempt {attempt}/3 on {url} with {wait:.1f}s wait...")
        time.sleep(wait)
    
    response = self._page.goto(url, ...)
    if response.status == 200:
        return html
    elif response.status in (202, 405):
        attempt += 1
    else:
        break
```

**Acceptance**: 
- ✅ Código compila sin errores
- ✅ Logging visible: "RETRY attempt X/3..."
- ✅ Backoff exponencial observable (6s → 12s → 24s)
- ✅ Retorna HTML en intento 2-3 si servidor se recupera
- ✅ Backward compatible: funciona sin parámetros nuevos

---

## Task 1.2: pipelines/components.py — BlockDetectionPolicy con Exponential Backoff

**Ubicación**: Líneas 59-98 (BlockDetectionPolicy clase)

**Cambios**:
1. Agregar parámetro `backoff_base: float = 45` en `__init__`
2. Cambiar `on_failure()` para retornar backoff exponencial
3. Agregar método `get_backoff_wait(consecutive_count: int) -> float`
4. Fórmula: `backoff_base × (2^(consecutive_count-1)) + jitter(±20%)`
5. Logging: `"BACKOFF POLICY: attempt {n} waiting {wait:.1f}s"`

**Cambios en `__init__`**:
```python
def __init__(
    self,
    threshold: int = 3,
    block_wait_min: float = 45,
    block_wait_max: float = 70,
    backoff_base: float = 45,  # NEW
):
    self._threshold = threshold
    self._consecutive_failures = 0
    self._block_wait_min = block_wait_min
    self._block_wait_max = block_wait_max
    self._backoff_base = backoff_base  # NEW
```

**Nuevo método**:
```python
def get_backoff_wait(self, consecutive_count: int) -> float:
    """Calculate exponential backoff with jitter."""
    delay = self._backoff_base * (2 ** (consecutive_count - 1))
    jitter = random.uniform(0.8, 1.2)
    wait = delay * jitter
    return wait
```

**Cambios en `on_failure()`**:
```python
def on_failure(self) -> Tuple[bool, float]:
    self._consecutive_failures += 1
    should_abort = self._consecutive_failures >= self._threshold
    wait_time = self.get_backoff_wait(self._consecutive_failures)
    print(f"BACKOFF POLICY: attempt {self._consecutive_failures} waiting {wait_time:.1f}s")
    return (should_abort, wait_time)
```

**Acceptance**:
- ✅ `get_backoff_wait()` retorna 45s → 90s → 180s para intentos 1-3
- ✅ Logging visible: "BACKOFF POLICY: attempt X waiting Ys"
- ✅ Backward compatible: `backoff_base=45` por defecto
- ✅ Intento 4+ aborta (should_abort=True)

---

## Task 1.3: pipelines/components.py — PipelineOrchestrator Block Tracking

**Ubicación**: Líneas 150-298 (PipelineOrchestrator.run())

**Cambios**:
1. Agregar `self.blocks_in_batch = 0` en constructor
2. Incrementar en cada `block_policy.on_failure()`
3. Loguear: `"BLOCKS THIS BATCH: {blocks_in_batch}/5 products — ADAPT?"`
4. Resetear contador al cambiar de página

**En `__init__`**:
```python
def __init__(self, ...):
    # ...
    self.blocks_in_batch = 0  # NEW
```

**En `run()` — cuando se detecta bloque**:
```python
# Dentro del loop de productos, después de on_failure()
if block_policy.on_failure() triggers:
    self.blocks_in_batch += 1
    print(f"BLOCKS THIS BATCH: {self.blocks_in_batch}/5 products — ADAPT?")
```

**Al cambiar página**:
```python
# Reset al iniciar nueva página
self.blocks_in_batch = 0
```

**Acceptance**:
- ✅ Logging visible: "BLOCKS THIS BATCH: 1/5..."
- ✅ Contador se incrementa en cada intento fallido
- ✅ Contador resetea al cambiar página

---

## Task 1.4: pipelines/config.py — PRODUCT_PER_PAGE Mutable

**Ubicación**: Líneas 11-54 (PipelineConfig.__init__)

**Cambios**:
1. Agregar atributo `_original_product_per_page` (guardar valor original)
2. Agregar método `adapt_product_per_page(factor: float) -> int`
3. Retornar nuevo valor clipped: `max(5, min(original, int(original * factor)))`
4. Logging: `"ADAPT PRODUCT_PER_PAGE: {old} → {new} (factor={factor})"`

**En `__init__`**:
```python
def __init__(self, ...):
    # ...
    self.product_per_page = product_per_page
    self._original_product_per_page = product_per_page  # NEW
```

**Nuevo método**:
```python
def adapt_product_per_page(self, factor: float) -> int:
    """Adapt PRODUCT_PER_PAGE by a factor, clipped to [5, original].
    
    Args:
        factor: Multiplication factor (0.85 = -15%, 1.10 = +10%)
    
    Returns:
        New PRODUCT_PER_PAGE value
    """
    old_value = self.product_per_page
    new_value = int(old_value * factor)
    new_value = max(5, min(self._original_product_per_page, new_value))
    self.product_per_page = new_value
    print(f"ADAPT PRODUCT_PER_PAGE: {old_value} → {new_value} (factor={factor})")
    return new_value
```

**Acceptance**:
- ✅ `adapt_product_per_page(0.85)` reduce 50 → 42
- ✅ `adapt_product_per_page(1.10)` aumenta 42 → 46
- ✅ No baja de 5, no sube del original
- ✅ Logging visible: "ADAPT PRODUCT_PER_PAGE..."
- ✅ Backward compatible: atributo privado `_original_product_per_page`

---

## Task 1.5: pipelines/components.py — PipelineOrchestrator Llamadas a adapt()

**Ubicación**: Líneas 293-298 (final de batch, antes de espera)

**Cambios**:
1. Después de procesar una página completa
2. Si `blocks_in_batch >= 2`: `config.adapt_product_per_page(0.85)` (-15%)
3. Si `blocks_in_batch == 0 and successful > 10`: `config.adapt_product_per_page(1.10)` (+10%)
4. Recalcular `pages_needed` dinámicamente si cambió `PRODUCT_PER_PAGE`
5. Logging: `"ADAPT TRIGGERED: {reason}, new PRODUCT_PER_PAGE={value}"`

**Pseudocódigo**:
```python
# Al final de cada página procesada
if self.blocks_in_batch >= 2:
    config.adapt_product_per_page(0.85)
    print(f"ADAPT TRIGGERED: {self.blocks_in_batch} blocks detected, reduce page size")
elif self.blocks_in_batch == 0 and successful_in_page > 10:
    config.adapt_product_per_page(1.10)
    print(f"ADAPT TRIGGERED: smooth run ({successful_in_page} successful), increase page size")

# Recalcular páginas si PRODUCT_PER_PAGE cambió
if config.product_per_page != original_product_per_page:
    pages_needed = (config.product_target + config.product_per_page - 1) // config.product_per_page
```

**Acceptance**:
- ✅ Logging visible: "ADAPT TRIGGERED..."
- ✅ PRODUCT_PER_PAGE reduce visible en logs
- ✅ PRODUCT_PER_PAGE aumenta en runs limpios
- ✅ pages_needed recalculado dinámicamente

---

## Task 1.6: pipelines/arte_pipeline.py — Pasar backoff_base a Policies

**Ubicación**: Líneas 97-116 (_create_orchestrator método)

**Cambios**:
1. Si BlockDetectionPolicy es creada aquí, pasar `backoff_base=45` (o parámetro configurable)
2. Confirmación: default 45s se mantiene
3. Permitir override vía `PipelineConfig.block_policy` si es pasado

**Pseudocódigo**:
```python
def _create_orchestrator(self, client, config):
    # ...
    if not config.block_policy:
        config.block_policy = BlockDetectionPolicy(
            threshold=3,
            block_wait_min=45,
            block_wait_max=70,
            backoff_base=45  # NUEVO
        )
    # ...
```

**Acceptance**:
- ✅ BlockDetectionPolicy recibe `backoff_base=45`
- ✅ Backward compatible: no break de pipelines existentes
- ✅ Permite override vía config injection

---

## Task 1.7: core/client.py — HTTPClient backoff_base Parámetro

**Ubicación**: `__init__` (línea 23-29)

**Cambios**:
1. Agregar parámetro opcional `backoff_base_http: float = 6`
2. Almacenar como `self._backoff_base_http`
3. Usar en loop de reintentos WAF (línea 128)
4. Logging: usar para mensajes de retry

**En `__init__`**:
```python
def __init__(
    self,
    timeout: int = REQUEST_TIMEOUT,
    download_strategy=None,
    domain_url: str | None = None,
    category_url: str | None = None,
    backoff_base_http: float = 6,  # NEW
):
    # ...
    self._backoff_base_http = backoff_base_http
```

**En loop de retry** (Task 1.1):
```python
delay = self._backoff_base_http * (2 ** (attempt - 1))
```

**Acceptance**:
- ✅ `backoff_base_http=6` por defecto
- ✅ Parámetro aceptado en constructor
- ✅ Usado en cálculo de delays

---

## Task 1.8: config/settings.py — Constantes Backoff

**Ubicación**: Final del archivo (línea ~34)

**Cambios**:
1. Agregar `BACKOFF_BASE_HTTP = 6`
2. Agregar `BACKOFF_BASE_POLICY = 45`
3. Comentario: "Para futuras configuraciones"

**Código**:
```python
# Exponential backoff bases (Phase 1) - Smart Retry
BACKOFF_BASE_HTTP = 6        # HTTP client retry: 6s → 12s → 24s
BACKOFF_BASE_POLICY = 45     # Block policy wait: 45s → 90s → 180s
```

**Acceptance**:
- ✅ Constantes definidas
- ✅ Valores documentados
- ✅ Disponibles para imports futuras

---

## Task 1.9: Validación Manual (Sin Tests Unitarios)

**Checklist de validación**:

### Setup
- [ ] `git checkout` rama limpia con Task 1.1-1.8 implementadas
- [ ] `pip install -r requirements.txt`
- [ ] Verificar que `core/client.py`, `components.py`, `config.py` compilan sin errores

### Test 1: HTTP Exponential Backoff
1. Modificar `client.py` línea 125 para simular 202 en intento 1
2. Ejecutar: `python main.py --target 5`
3. Observar logs:
   - [ ] `"RETRY attempt 1/3 on {url} with 6.Xs wait..."`
   - [ ] `"RETRY attempt 2/3 on {url} with 12.Xs wait..."`
   - [ ] Si intento 3 falla: `"WAF BLOCKED (202) on {url}. Aborting."`

### Test 2: Block Detection Policy Backoff
1. Simular 3 bloques consecutivos en BlockDetectionPolicy
2. Observar logs:
   - [ ] `"BACKOFF POLICY: attempt 1 waiting 45.Xs"`
   - [ ] `"BACKOFF POLICY: attempt 2 waiting 90.Xs"`
   - [ ] `"BACKOFF POLICY: attempt 3 waiting 180.Xs"`
   - [ ] Intento 4: `should_abort=True`

### Test 3: Block Tracking
1. Ejecutar scraper normal
2. Cuando se detecte bloque (202), observar:
   - [ ] `"BLOCKS THIS BATCH: 1/5 products — ADAPT?"`
   - [ ] Contador incrementa con cada bloque en página
   - [ ] Contador resetea en nueva página

### Test 4: PRODUCT_PER_PAGE Adaptación
1. Ejecutar con `PRODUCT_TARGET=50`, observar logs:
   - [ ] Página 1: `PRODUCT_PER_PAGE=50` (original)
   - [ ] Cuando `blocks_in_batch >= 2`: `"ADAPT PRODUCT_PER_PAGE: 50 → 42 (factor=0.85)"`
   - [ ] Página 2 usa nuevo valor 42
   - [ ] Si página 2 limpia: `"ADAPT PRODUCT_PER_PAGE: 42 → 46 (factor=1.10)"`

### Test 5: Backward Compatibility
1. Código sin cambios en línea de comandos debe funcionar idéntico
2. Ejecutar: `python main.py` (sin `--config`)
3. Verificar:
   - [ ] Backoff exponencial activo (base 6 y 45)
   - [ ] Adaptación activa automáticamente
   - [ ] Logs normales sin errores

### Test 6: End-to-End
1. Ejecutar: `python main.py --target 100`
2. Observar durante 5-10 minutos:
   - [ ] Scraper no aborta en primer bloque
   - [ ] Esperas exponenciales visibles en logs
   - [ ] PRODUCT_PER_PAGE adapta dinámicamente
   - [ ] CSV se genera con productos válidos
   - [ ] No hay crashes o excepciones no capturadas

---

## Dependencies Between Tasks

```
1.1 (HTTP backoff) — independent
1.2 (Policy backoff) — independent
1.3 (Block tracking) — requires 1.2
1.4 (Config adapt) — independent
1.5 (Orchestrator adapt) — requires 1.3, 1.4
1.6 (arte_pipeline) — requires 1.2
1.7 (HTTPClient param) — requires 1.1
1.8 (settings) — independent
1.9 (Validación) — requires 1.1-1.8
```

**Orden recomendado**: 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7 → 1.8 → 1.9

---

## Acceptance Criteria — Fase Completa

- ✅ Código compila sin errores
- ✅ Logging exponencial visible en stdout (6s → 12s → 24s, 45s → 90s → 180s)
- ✅ Backward compatible: defaults sin parámetros nuevos = original behavior
- ✅ Scraper NO aborta en primer bloque; reintenta con esperas exponenciales
- ✅ PRODUCT_PER_PAGE reduce visible en logs cuando se detectan bloques
- ✅ PRODUCT_PER_PAGE aumenta visible en logs cuando run es limpio
- ✅ CSV generado con datos válidos (sin corrupciones)
- ✅ Sin tests unitarios (solo validación manual)

---

## Implementation Notes

1. **Jitter**: Multiplicar por `random.uniform(0.8, 1.2)` para evitar sincronización
2. **Clipping**: PRODUCT_PER_PAGE nunca baja de 5, nunca sube del valor original
3. **Logging**: Usar print() directo (compatible con Pipeline logging)
4. **Backward Compatibility**: Todos los parámetros nuevos tienen defaults
5. **No Unit Tests**: Solo validación manual observando logs

---

## Files Modified Summary

| File | Lines | Change |
|------|-------|--------|
| `core/client.py` | 128-131 | Replace single retry with exponential backoff loop |
| `pipelines/components.py` | 62-98 | Add backoff_base param, get_backoff_wait() method |
| `pipelines/components.py` | 150-298 | Add blocks_in_batch tracking |
| `pipelines/config.py` | 11-54 | Add _original_product_per_page, adapt_product_per_page() |
| `pipelines/components.py` | 293-298 | Call adapt_product_per_page() at batch end |
| `pipelines/arte_pipeline.py` | 97-116 | Pass backoff_base to BlockDetectionPolicy |
| `core/client.py` | 23-29 | Add backoff_base_http parameter |
| `config/settings.py` | ~34 | Add BACKOFF_BASE_* constants |

---

**Ready for implementation. No further requirements.**
