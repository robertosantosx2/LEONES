# LEONES Web — referencia obligatoria

## Objetivo

La web de LEONES prioriza, en este orden:

1. simplicidad técnica;
2. legibilidad;
3. funcionalidad;
4. accesibilidad básica;
5. mantenimiento sencillo.

La estética no debe introducir complejidad que no aporte una función clara.

## Estado visible · 4 septiembre 2026

La web debe reflejar el estado canónico real del repositorio:

- **JALÓN 1:** 🟢 cerrado.
- **JALÓN 2:** 🟢 cerrado, con ejecución física y evidencia reproducible.
- **JALÓN 3:** 🟢 cerrado, con contrato `runtime-benchmark-evidence.v1.1`.
- **JALÓN 4:** 🟢 cerrado, con decisión ODS/Magnitude y metodología de evaluación consolidada.
- **RC1:** 🟢 validado mediante ejecución efectiva end-to-end.
- **ODS / Magnitude:** 🟢 contrato de decisión fijado, sin scoring paralelo.
- **RC2:** 🟡 preparado para beta, con operador único, elección de idioma, instalación, verificación física, consentimiento A01 y handoff al camino canónico de RC1.

La página pública de referencia para este estado es [`estado.html`](estado.html).

## RC2 · recorrido canónico

El único punto de entrada del beta tester es `./leones`, implementado por `scripts/rc2_wizard.py`.

```text
IDIOMA (una elección por sesión)
   ↓
HARDWARE + LLMFIT → CANDIDATOS (ESTIMATED)
   ↓
ELECCIÓN DE MODELO
   ↓
ODS / MAGNITUDE → ELECCIÓN DE STACK
   ↓
CONSENTIMIENTO INSTALAR
   ↓
INSTALAR → VERIFICACIÓN FÍSICA DEL STACK
   ↓
RESOLUCIÓN MODELO → RUNTIME (declarativa)
   ↓
PREFLIGHT RUNTIME / ARTEFACTO
   ↓
EXPLICACIÓN A01 → CONSENTIMIENTO
   ├─ NO → FIN (instalación intacta)
   └─ SÍ → EXECUTION_AUTHORIZED → RC1 A01
                                      ↓
                              MEDICIÓN / EVIDENCIA
```

La instalación no autoriza un benchmark. Solo una verificación física satisfactoria (`real_installation: true`) permite llegar a `READY_FOR_BENCHMARK`. Sin consentimiento A01 no hay ejecución.

## Benchmark canónico

RC2 no crea un segundo runner. Reutiliza el pipeline validado de RC1:

| Campo | Valor |
|---|---|
| id | `LEONES-Agentic` |
| task | `A01` |
| prompt | `Execute A01. Return only JSONL tool calls.` |
| métricas | `wall_seconds`, `measured_tps`, `grader_pass` |
| runner | `scripts/a01_runtime_benchmark.py` |
| puentes | `scripts/ollama_a01_runtime.py`, `scripts/llama_cpp_a01_runtime.py` |
| resolución | `runtime_selection/model_runtime_resolver.py` |

GGUF/HF no se convierte silenciosamente en un modelo Ollama. Sin runtime o artefacto disponible, A01 queda `benchmark_blocked`; la web y el producto no deben inventar una medición.

## LLMFit, ODS y Magnitude

LLMFit es la fuente especializada de hardware/model-fit para perfilar el host y presentar candidatos. Sus resultados son **ESTIMATED**, no mediciones físicas de LEONES.

ODS y Magnitude se presentan antes de la elección de stack con descripciones legibles y capacidades respaldadas por contrato o evidencia. LEONES no crea un scoring paralelo para sustituir esas fuentes.

## RC1

La web no debe presentar RC1 como una simple validación de código. El hito demostrado es físico:

```text
selección → gate → execution autorizado
         → runtime real → modelo real → benchmark
         → medición → evidencia reproducible
```

Las cifras históricas de ejecuciones concretas deben conservarse en su documentación/evidencia correspondiente y no reutilizarse como mediciones de otro equipo, runtime, modelo o configuración. La web no debe convertir una ejecución histórica en un benchmark universal.

## Evidencia y lenguaje

- **ESTIMATED** no equivale a **MEASURED**.
- Una recomendación no equivale a evidencia.
- Una preflight no equivale a una instalación verificada.
- Una instalación verificada no equivale a un benchmark ejecutado.
- Un benchmark ejecutado debe conservar su procedencia y configuración.
- Un fallo no se publica como medición válida.
- Los valores desconocidos permanecen desconocidos.

## Arquitectura web

```text
HTML semántico
    ↓
CSS compartido
    ↓
JavaScript solo cuando aporta comportamiento
```

La navegación es transversal. El contenido de cada página debe permanecer separado de la infraestructura interna.

`site.css` contiene el sistema visual común. `navigation.css` contiene exclusivamente la navegación. No duplicar reglas entre páginas.

JavaScript resuelve comportamiento, no problemas que HTML o CSS puedan resolver de forma más simple. Los scripts deben ser externos y cargarse con `defer` cuando sea posible.

## Separación de infraestructura

La web documenta, explica y presenta LEONES. No debe convertirse en un paquete que el usuario tenga que descargar para ejecutar la infraestructura.

Los scripts locales son herramientas autónomas. El usuario descarga solo las herramientas necesarias para realizar pruebas en su propio equipo.

## Criterio de terminado

Una página está terminada cuando una persona puede abrirla, entender para qué sirve, navegar al siguiente paso y revisar su contenido sin conocer la arquitectura interna.

## Regla de producto

La web debe reflejar el repositorio real. No anunciar capacidades como cerradas si no existe evidencia correspondiente en el proyecto. Cuando haya una medición física nueva, debe enlazarse a su evidencia y conservar su carácter local y reproducible.
