# LEONES V1 — Criterio de preparación para usuario final

**Estado:** 🟠 PREPARADA LA ARQUITECTURA · FALTA CERRAR LA SUPERFICIE DE USUARIO
**Rama:** `rc1-minimal-script-cleanup`
**Ámbito:** consolidación del trabajo realizado desde el 27 de agosto de 2026.

## 1. Qué significa «V1 ejecutable»

LEONES será V1 cuando una persona que no conozca los JALONES pueda utilizar una única entrada documentada para obtener una recomendación reproducible y trazable.

La persona usuaria no debe tener que conocer ni ejecutar manualmente los contratos internos de JALÓN 3–11.

La arquitectura interna seguirá siendo la que ya está fijada:

```text
selección
  ↓
runtime autorizado
  ↓
ejecución
  ↓
medición
  ↓
evidencia
  ↓
decisión ODS/Magnitude → LEONES
  ↓
recomendación
  ↓
publicación
  ↓
salida fiel
  ↓
traza E2E
```

No se crea una segunda cadena de benchmark, scoring, medición o evidencia.

## 2. Lo que ya está cerrado

- Contratos de ejecución y evidencia real.
- Protocolo de medición real.
- Taxonomía y adapters de runtime.
- Decisión ODS/Magnitude → LEONES.
- Frontera entre señales externas y evidencia física.
- Contrato de recomendación.
- Validación → promoción → publicación.
- Salida fiel de recomendación.
- Trazabilidad E2E.
- Disciplina `-strict-`.
- Tests y gates de los jalones construidos.

La consolidación STRICT alcanzó una suite de 285 tests en la comprobación local del 29 de agosto de 2026. Ese dato demuestra consistencia del código probado, no una garantía de ejecución física universal.

## 3. Lo que falta para V1

### A. Entrada única de usuario

Debe existir un punto de entrada sencillo y documentado que oculte la maquinaria interna.

Debe permitir como mínimo:

1. indicar qué quiere hacer la persona;
2. proporcionar o seleccionar el modelo;
3. detectar o declarar el hardware disponible;
4. recorrer la cadena canónica;
5. producir una salida comprensible;
6. conservar las referencias de trazabilidad.

### B. Preflight de máquina

Antes de una ejecución física, LEONES debe explicar de forma sencilla:

- sistema operativo;
- CPU;
- GPU/NPU cuando exista;
- memoria disponible;
- runtimes detectados;
- modelos/artefactos disponibles;
- qué parte es detectada y qué parte necesita ejecución real.

El preflight no debe convertir una estimación en una medición.

### C. Contrato de resultado para usuario

La salida V1 debe distinguir claramente:

- recomendado;
- por qué se recomienda;
- qué evidencia respalda la recomendación;
- qué información procede de fuentes externas;
- qué se ha medido realmente en la máquina;
- qué todavía no se ha ejecutado o verificado.

### D. Instalación y documentación

Una instalación limpia debe poder seguir una guía `.md` sin conocer la estructura interna del repositorio.

La documentación externa debe contener ejemplos completos y una sección de problemas frecuentes.

Los scripts internos deben explicar con comentarios sencillos:

- qué reciben;
- qué producen;
- qué validan;
- qué no hacen.

### E. Operación E2E real

La cadena declarativa ya está definida. Para cerrar V1 habrá que ejecutar una operación real sobre la plataforma física canónica cuando esa operación necesite evidencia física.

La evidencia física existente se reutiliza; no se reescribe ni se sustituye por valores estimados.

## 4. Criterio de no regresión

Una implementación V1 no puede:

- crear otro motor de scoring;
- crear otro benchmark de rendimiento;
- calcular TPS estimados dentro de la capa de recomendación;
- convertir LLMFit u ODS/Magnitude en evidencia física local;
- ocultar la procedencia de un dato;
- inventar una medición que no haya ocurrido;
- romper la trazabilidad E2E;
- obligar al usuario a conocer los JALONES internos.

## 5. Orden de construcción restante

El orden recomendado es deliberadamente corto:

```text
contrato de entrada V1
  ↓
preflight de usuario
  ↓
orquestación de la cadena ya existente
  ↓
resultado V1 legible
  ↓
guía de instalación/uso
  ↓
tests de flujo de usuario
  ↓
auditoría STRICT
  ↓
ejecución física final cuando sea imprescindible
  ↓
V1
```

## 6. Regla STRICT aplicada a V1

Cada nueva pieza debe responder antes de incorporarse:

- ¿reutiliza un contrato existente?
- ¿introduce una frontera nueva real?
- ¿tiene una fuente de verdad única?
- ¿distingue externo, estimado, observado, medido y verificado?
- ¿está documentada para una persona con pocos conocimientos de programación?
- ¿tiene tests negativos?
- ¿puede auditarse sin hardware cuando la comprobación no necesita hardware?

Si la respuesta es no, la pieza no se considera terminada.

## 7. Definición de terminado

V1 no significa que todos los modelos ni todos los runtimes hayan sido medidos físicamente.

V1 significa que **el producto sabe ejecutar correctamente su cadena canónica para un caso soportado, conserva evidencia y procedencia, explica al usuario qué sabe y qué no sabe, y no requiere que el usuario conozca la arquitectura interna para utilizarlo**.

**Frase de recuperación:**

> V1 = una entrada de usuario sencilla que recorre la arquitectura canónica existente, conserva procedencia y evidencia, y nunca inventa lo que no se ha medido.
