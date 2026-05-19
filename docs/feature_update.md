# Ejecucion Multiple sin Solapamiento de Datos

## Estado Actual

**Arquitectura de Deduplicacion:**
- CheckpointManager.get_scraped_urls() lee el CSV y retorna URLs **filtradas por category_url**
- CheckpointManager.save_record() automaticamente etiqueta cada registro con el category_url actual
- El pipeline ya deduplica via set en memoria: if full_link in scraped_urls: continue
- Al reanudar, lee el checkpoint y continua desde la ultima URL guardada

**Escritura en CSV:**
- save_record() abre el archivo en modo append con csv.DictWriter estandar
- No existe mecanismo de file locking
- Cada escritura es sincrona pero escrituras concurrentes podrian entrelazarse

## Areas Afectadas
- pipelines/schema.py - CheckpointManager maneja lecturas/escrituras
- pipelines/components.py - PipelineOrchestrator usa checkpoint para filtrar URLs
- config/settings.py - OUTPUT_PATH y CATEGORY_URL definen ubicacion del CSV
- main.py - Punto de entrada y carga de configuracion

## Opciones

### 1. Misma Categoria Secuencial (Ya Funciona)
Ejecuta el scraper dos veces en la misma categoria -> checkpoint filtra duplicados por category_url.
Segunda ejecucion lee CSV existente, carga URLs de la misma categoria, las salta.

- Pros: Cero cambios de codigo, soporte inmediato, sin problemas de concurrencia
- Contras: Lento (secuencial), cada ejecucion re-scrrapea paginas de categoria
- Esfuerzo: Ninguno (ya implementado)

### 2. Diferentes Categorias en Mismo CSV (Ya Funciona)
Ejecuta scraper en categoria=arte, luego categoria=ficcion -> CSV contiene ambas.
CheckpointManager filtra por category_url, asi que sin solapamiento.

- Pros: Maxima densidad de datos, un solo CSV para todas las categorias, aislamiento por categoria
- Contras: Requiere cambiar CATEGORY_URL entre ejecuciones (o multiples configs)
- Esfuerzo: Ninguno (ya implementado via filtrado por category_url)

### 3. Ejecucion Paralela (Segura con Condiciones)
Ejecuta dos instancias simultaneamente en categorias diferentes.
Cada una escribe en el mismo CSV con diferente category_url -> CheckpointManager filtra independientemente.

- Pros: Verdadera paralelizacion, sin cambios de codigo necesarios, datos separados por categoria
- Contras: Buffer de I/O podria perder datos en escrituras simultaneas; sin garantias transaccionales
- Esfuerzo: Bajo (solo testing)

### 4. Ejecucion Paralela con File Locking (Mas Robusta)
Envuelve CheckpointManager.save_record() con fcntl.flock() (Unix) o msvcrt.locking() (Windows).
Solo un escritor a la vez; lectores tambien deben adquirir lock compartido.

- Pros: A prueba de race conditions, soporta cualquier cantidad de instancias paralelas
- Contras: Pequena penalidad de performance (contension de locks), complejidad anadida
- Esfuerzo: Medio

### 5. CSV Separado Por Categoria (Alternativa Mas Simple)
Almacena CSV en subdirectorio nombrado por categoria: storage/outputs/{categoria}/books.csv.
Auto-genera via regex (ya hecho en arte_pipeline.py).

- Pros: Cero problemas de concurrencia, sin solapamiento posible, logica simple
- Contras: Cambia estructura de salida, requiere logica de migracion, divide datos en multiples archivos
- Esfuerzo: Bajo (1 linea de cambio en logica de nombres)

## Recomendacion

**Para uso tipico (secuencial o categorias diferentes): Usa opciones 1 o 2 — ya funcionan.**

- Si ejecutas el scraper dos veces en la misma categoria secuencialmente: Ya deduplica automaticamente
- Si quieres scrapear multiples categorias: Ponlas todas en un CSV cambiando CATEGORY_URL y re-ejecutando
- Si quieres scraping paralelo de categorias diferentes: Pruebalo — deberia funcionar si das a cada proceso una config diferente

**Solo si necesitas ejecucion concurrente en LA MISMA categoria:** Implementa Opcion 4 (file locking).

## Riesgos

- Race conditions: Multiples escrituras en mismo CSV sin locking pueden entrelazer filas
- Logica duplicada de category_url: Si scrapeás la misma categoria dos veces concurrentemente sin locking, las escrituras podrian no saltar duplicados atomicamente
- Performance: File locking añade overhead (1-5ms por escritura); concurrencia pesada degrada throughput

## Proximos Pasos

1. Corto plazo: Validar que opciones 1-2 funcionan con pruebas simples
2. Mediano plazo: Si se necesita paralelismo, implementar opcion 3 (diferentes categorias) y testear
3. Largo plazo: Si se necesita mismo-categoria concurrente, implementar opcion 4 (file locking)