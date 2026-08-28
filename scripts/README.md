# Scripts LEONES — RC1

> **Principio:** mínimo código necesario, máxima documentación útil y ninguna duplicación funcional.

Los scripts son la interfaz local entre una persona y LEONES. En RC1 no se pretende tener un script para cada idea del proyecto: se conservan únicamente las piezas que hacen avanzar un recorrido operativo claro.

**Contrato completo:** [`../docs/SCRIPT_STYLE_CONTRACT.md`](../docs/SCRIPT_STYLE_CONTRACT.md)  
**Plan de migración RC1:** [`../docs/RC1-SCRIPT-MIGRATION.md`](../docs/RC1-SCRIPT-MIGRATION.md)

---

## 1. Camino mínimo de RC1

```text
hardware observado
       ↓
fit inicial (LLMFit / fuentes)
       ↓
selection_pipeline
       ↓
plan de runtime
       ↓
runtime externo (ODS / Magnitude / fallback llama.cpp)
       ↓
medición LEONES
       ↓
evidencia
       ↓
MANADA
```

La investigación, Atlas y el conocimiento siguen siendo parte esencial de LEONES. Los scripts de esas capas no desaparecen por no formar parte del recorrido mínimo: simplemente no deben confundirse con el núcleo operativo.

---

## 2. Scripts del núcleo

| Script | Pregunta concreta | Produce | No hace |
|---|---|---|---|
| `hardware_profile.py` | ¿Qué hardware observa Linux en esta máquina? | perfil JSON de hechos observados | no estima fit ni ejecuta modelos |
| `selection_pipeline.py` | ¿Qué candidato/configuración debemos probar? | selección + plan de runtime | no declara rendimiento medido |
| `runtimes/llama_cpp_adapter.py` | ¿Cómo se expresa un plan autorizado para llama.cpp? | argv seguro y metadatos | no selecciona modelos ni mide |
| `runtimes/run_llama_cpp_selected.py` | ¿Qué ocurre al ejecutar un plan autorizado con llama.cpp? | resultado observado | no autoriza planes ni publica |
| `runtime_benchmark_evidence.py` | ¿La medición tiene evidencia aceptable? | evidencia normalizada/validada | no inventa ejecuciones |
| `check_script_quality.py` | ¿Los scripts respetan la norma mínima? | avisos de calidad | no modifica archivos |

**Nota:** ODS y Magnitude no se implementan dentro de estos scripts. LEONES los integra cuando proceda y conserva su frontera de responsabilidad.

---

## 3. Qué debe tener cada script reutilizado

### Dentro del `.py`

El docstring inicial debe permitir contestar rápidamente:

- para qué sirve;
- qué recibe;
- qué produce;
- qué no hace;
- cuáles son sus límites importantes.

Los comentarios deben explicar **por qué** existe una decisión no evidente. No deben narrar línea por línea lo que ya expresa el código.

### En esta documentación

Cada pieza del núcleo debe tener:

- un lugar inequívoco dentro del pipeline;
- un ejemplo mínimo cuando sea ejecutable directamente;
- sus entradas y salidas;
- sus límites;
- el contrato que consume y el que entrega;
- la relación con evidencia y publicación.

---

## 4. Datos y procedencia

Los scripts deben mantener separadas estas categorías:

- `estimated`: cálculo o estimación;
- `reported`: dato declarado por una fuente externa;
- `observed`: hecho observado en el entorno;
- `measured`: resultado obtenido mediante una ejecución real de LEONES;
- `verified`: resultado que ha superado el gate correspondiente;
- `unknown`: dato no demostrado.

Un script nunca debe mejorar artificialmente la categoría de un dato.

---

## 5. Privacidad y seguridad operacional

Los scripts locales no publican por defecto.

No deben introducir en un artefacto destinado a compartir:

- nombres o correos personales;
- rutas privadas innecesarias;
- UUID, MAC/IP o números de serie;
- credenciales, tokens o secretos;
- contenido privado.

Un benchmark físico debe conservar suficiente contexto para ser reproducible, pero no convertir el artefacto en una ficha personal del usuario.

---

## 6. Qué NO hacer

No crear:

- otro selector si ya existe `selection_pipeline.py`;
- otro perfilador de hardware si `hardware_profile.py` responde a la necesidad;
- otro runner para el mismo runtime sin una diferencia contractual demostrable;
- un benchmark paralelo que redefina lo que significa `measured`;
- una capa de abstracción "por si algún día";
- un script que mezcle selección, ejecución, medición y publicación sin una razón contractual explícita.

Cuando una necesidad nueva no cabe en el camino mínimo, primero se documenta la necesidad y después se decide si merece una nueva pieza.

---

## 7. Mantenimiento

Antes de modificar un script:

```text
identificar consumidores
       ↓
leer sus pruebas
       ↓
leer su documentación
       ↓
cambiar lo mínimo
       ↓
probar
       ↓
actualizar documentación
```

Los scripts históricos que ya no tengan consumidor RC1 no se borran precipitadamente. Se clasifican y, cuando corresponda, se trasladan de forma trazable a la zona `deprecated` siguiendo [`../docs/RC1-SCRIPT-MIGRATION.md`](../docs/RC1-SCRIPT-MIGRATION.md).

---

## 8. Auditoría rápida

```bash
python scripts/check_script_quality.py
```

La auditoría es deliberadamente sencilla. Durante la migración puede informar sobre deuda histórica sin bloquearla. Una familia ya limpiada puede someterse a `--strict`.

---

## 9. Regla de oro

> **Si un script no tiene una pregunta concreta que responder dentro del recorrido de LEONES, no necesita estar en el núcleo RC1.**
