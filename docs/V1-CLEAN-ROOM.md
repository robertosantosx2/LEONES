# LEONES V1 — Limpieza, fijación y conservación de evidencia

## Principio

Una versión estable no es un directorio sin archivos temporales. Es un sistema en el que resulta evidente **qué pertenece al producto, qué pertenece a una ejecución local y qué constituye evidencia histórica**.

LEONES adopta para V1 una regla simple:

> **El repositorio contiene contratos, código, pruebas y documentación. El entorno local contiene estados de ejecución. La evidencia publicada debe ser intencionada, identificable y trazable.**

## 1. Qué debe entrar en Git

Debe versionarse:

- código fuente;
- contratos y esquemas;
- tests;
- workflows de CI;
- documentación técnica y metodológica;
- configuraciones reproducibles que no contengan secretos ni estado local;
- fixtures deterministas;
- decisiones arquitectónicas;
- documentación de las mediciones y sus condiciones.

## 2. Qué no debe entrar en Git

No deben versionarse como estado de trabajo:

- `.venv/`;
- `__pycache__/` y bytecode Python;
- `.pytest_cache/`;
- `.leones/`;
- `artifacts/` de ejecuciones locales;
- clones o checkouts temporales bajo `upstream/`;
- logs temporales;
- archivos de IDE o del sistema operativo.

El `.gitignore` del proyecto fija estas fronteras para que una ejecución local no convierta accidentalmente el árbol de trabajo en una colección de artefactos.

## 3. Evidencia local frente a evidencia publicada

Que un archivo sea útil durante una medición no implica que deba convertirse automáticamente en un archivo versionado.

Para una medición real, el patrón recomendado es:

```text
entorno local
   ↓
artefactos de ejecución
   ↓
validación del esquema
   ↓
revisión de procedencia
   ↓
resumen documental estable
   ↓
Git / conocimiento LEONES
```

La documentación estable debe explicar **qué se midió, dónde, con qué versión, cómo y qué no puede concluirse**. No debe limitarse a pegar una salida de terminal.

## 4. Identidad de una medición

Una medición debe poder distinguirse de otra mediante, como mínimo:

- modelo;
- cuantización;
- runtime;
- versión del runtime;
- tarea;
- entorno/hardware cuando esté disponible;
- timestamp;
- identificador de ejecución;
- métrica;
- unidad;
- estado del grader;
- hash del resultado cuando el contrato lo proporcione.

Si alguno de estos datos no se conoce, debe permanecer explícitamente `unknown` o `null`. **Nunca se debe completar por intuición.**

## 5. No sobrescribir historia

Una nueva medición no corrige silenciosamente una medición anterior.

Por ejemplo, si una ejecución produce:

- `52.7164 tok/s`
- después `47.9803 tok/s`

ambas son observaciones válidas de ejecuciones distintas. La segunda puede ser la referencia actual, pero la primera continúa siendo parte del historial.

Esto evita que el sistema fabrique una falsa precisión ocul­tando variabilidad natural de la ejecución.

## 6. Fixture y real runtime

LEONES utiliza dos clases de ejecución complementarias.

### Fixture

Sirve para CI. Debe ser:

- determinista;
- barato;
- independiente de GPU;
- independiente de descargas de modelos;
- adecuado para probar contratos y regresiones.

### Runtime real

Sirve para validar el comportamiento físico de la integración:

- runtime instalado;
- modelo real;
- endpoint real;
- inferencia real;
- métricas reportadas por el runtime;
- artefacto real;
- grading real.

El fixture **no es una simulación de rendimiento** y el runtime real **no sustituye las pruebas deterministas de CI**.

## 7. Qué significa "V1 estable"

Para esta parte de la arquitectura, V1 se considera estable cuando:

1. el selector genera una identidad inequívoca;
2. `runtime-selection.v1` produce un plan autorizado;
3. el adaptador ejecuta el plan sin construir comandos inseguros a partir de salida del modelo;
4. A01 mantiene el orden de herramientas;
5. el artefacto esperado se genera y verifica;
6. el grader valida el comportamiento;
7. el runtime puede proporcionar una medición sin que LEONES la invente;
8. el resultado se serializa conforme al contrato;
9. CI comprueba el camino determinista;
10. existe documentación suficiente para reproducir e interpretar la medición real.

## 8. Regla editorial

La documentación de LEONES debe responder siempre a cinco preguntas:

**Qué es.** Identidad y alcance.

**Para qué sirve.** Lugar dentro del ecosistema.

**Cómo funciona.** Flujo técnico y contratos.

**Qué evidencia existe.** Fuente, observación, estimación, medición y verificación, separadas.

**Qué no sabemos.** Límites, `unknown`, hipótesis pendientes y próximos pasos.

Una documentación que solo describe el código está incompleta. Una documentación que solo describe la intención también. La documentación V1 debe conectar **intención → implementación → prueba → evidencia → límite**.
