# LEONES Web — referencia pública

La web pública refleja el estado real del repositorio y mantiene una frontera estricta entre **declarado**, **estimado**, **observado** y **medido**.

## Estado actual · 7 septiembre 2026

- **JALÓN 1:** 🟢 cerrado.
- **JALÓN 2:** 🟢 cerrado e inmutable; ejecución física y evidencia reproducible.
- **JALÓN 3:** 🟢 cerrado.
- **JALÓN 4:** 🟢 cerrado.
- **RC1:** 🟢 validado.
- **RC2:** 🟡 histórica / compatibilidad explícita.
- **RC3:** 🟢 cerrada.
- **RC4:** 🟡 en validación física.
- **TUI RC4:** 🟢 validada como capa de presentación.
- **Recomendador RC4:** 🟢 endurecido.
- **MEASURED RC4 E2E:** 🟡 abierto; requiere validación física en Ubuntu.

La página pública de referencia es [`estado.html`](estado.html).

## Flujo canónico RC4

```text
IDIOMA
   ↓
ESTADO DE LA MÁQUINA
   ↓
USER_INTENT[] · obligatorio · selección múltiple
   ↓
HARDWARE + RESOURCE PREFLIGHT
   ↓
HUGGING FACE + ARTIFICIAL ANALYSIS → feed LEONES ≤100
   ↓
LLMFit / FitLLM opcional → catálogo propio ≤100
   ↓
INTERSECCIÓN POR IDENTIDAD
   ↓
hasta 3 ESTIMATED | insufficient · sin padding
   ↓
ELECCIÓN HUMANA
   ↓
STACK / RUNTIME
   ↓
VALIDACIÓN FÍSICA UBUNTU
   ↓
MEDICIÓN → MEASURED
```

La TUI presenta este recorrido, pero no cambia su semántica ni ejecuta por el hecho de recomendar.

## Reglas de autoridad

- `ESTIMATED` **no** es `MEASURED`.
- Una recomendación **no** autoriza instalación, ejecución ni medición.
- `user_intent[]` debe existir y no puede estar vacío antes de recomendar.
- HF y Artificial Analysis aportan evidencia externa; no autorizan ejecución.
- LLMFit es un preselector opcional y conserva su catálogo independiente.
- Menos de tres coincidencias significa `insufficient`; nunca se rellenan candidatos.
- RAM física y VRAM permanecen separadas; el swap no cuenta como RAM física.
- Solo una ejecución física protocolizada puede producir evidencia `MEASURED`.

## TUI RC4

La interfaz operativa actual es retro/TUI y comienza por idioma. Después muestra el **Estado de la máquina**, incluyendo hardware, RAM/CPU/disco y el inventario de componentes IA detectados: modelos locales, agentes, runtimes, harnesses y herramientas cuando están disponibles.

La navegación usa foco visible, `TAB`, `↑/↓`, `ESPACIO` y `ENTER`. La selección de propósito es múltiple y precede a la recomendación.

Cobertura de idioma de la TUI actual: **ES / EN / ZH**. `ja` pertenece a la norma general de interfaz, pero queda fuera de esta fase.

## Instalación

RC4 **no debe presentarse como una instalación automática de toda la pila**. El proyecto separa diagnóstico, recomendación, elección, consentimiento, instalación, verificación, autorización de ejecución y medición.

FitLLM/LLMFit es opcional para la ruta de recomendación. El usuario elige qué componentes quiere instalar y cualquier operación instalable debe ser explícita y desinstalable por la vía correspondiente.

Consulta [`INSTALL.md`](INSTALL.md) para el procedimiento vigente de preparación y diagnóstico.

## JALÓN 2

La evidencia física de JALÓN 2 permanece cerrada e inmutable. La web no reutiliza sus cifras como benchmark universal: una medición pertenece siempre a su hardware, modelo, runtime, configuración y protocolo concretos.

## Arquitectura web

```text
HTML semántico
    ↓
CSS compartido
    ↓
JavaScript solo cuando aporta comportamiento
```

La web documenta y presenta LEONES. La infraestructura local ejecuta. La evidencia física conserva procedencia.

## Principio de producto

Cuando una capacidad no está validada, se muestra como abierta, pendiente o desconocida. La web nunca convierte una estimación externa, una preflight o una ejecución histórica en una medición nueva.