# LEONES Rules

> **Documento normativo de trabajo — congelado para RC1**
>
> Este documento fija las reglas operativas, arquitectónicas y documentales que gobiernan LEONES a partir de la reorganización hacia una versión mínima operativa.

## 1. Regla fundacional

LEONES no convierte una afirmación en un hecho por repetición.

**Descubrir → documentar → verificar → medir → conservar procedencia → publicar.**

Toda cifra debe conservar su naturaleza:

- `estimated`: estimación o cálculo;
- `reported`: dato declarado por una fuente externa;
- `observed`: configuración observada;
- `measured`: medición física realizada por LEONES;
- `verified`: dato que ha superado el quality gate correspondiente;
- `unknown`: dato no demostrado.

Nunca se promociona automáticamente una estimación a medición.

## 2. LEONES debe ser pequeño

El objetivo inmediato es una **versión mínima operativa**, no un ecosistema gigantesco.

Cada nueva pieza debe justificar su existencia por una de estas razones:

1. decide;
2. conecta;
3. mide;
4. valida;
5. conserva evidencia;
6. publica conocimiento.

Si una capacidad ya existe de forma suficientemente útil en un proyecto externo, LEONES **no la reimplementa por defecto**.

## 3. Upstream-first

La primera pregunta ante una capacidad nueva es:

> **¿Quién ya lo hace bien y podemos utilizarlo?**

Preferencia:

```text
upstream existente
      ↓
configuración / integración
      ↓
conector fino LEONES
      ↓
contribución upstream
      ↓
implementación propia
```

La implementación propia es el último recurso, no el punto de partida.

## 4. Fronteras de responsabilidad

La arquitectura RC1 queda conceptualmente separada así:

```text
LLMFit
  ↓
fit hardware inicial
  ↓
LEONES
  ├── identidad / evidencia / decisión
  ├── selección
  ├── integración de runtimes
  ├── ejecución controlada
  ├── medición física
  └── evidencia / publicación
       ↓
   ODS / SOHO       Magnitude / personal
       ↓                  ↓
       └──── ejecución ───┘
                ↓
          medición LEONES
                ↓
             MANADA
```

**LLMFit** aporta la primera estimación de encaje hardware/modelo.

**LEONES** decide y mide. No debe convertirse en otro detector de hardware generalista si puede delegarlo.

**ODS** es la vía prioritaria para el escenario SOHO cuando sus capacidades sean adecuadas.

**Magnitude** es la vía prioritaria para el escenario de asistente personal cuando sus capacidades sean adecuadas.

La elección entre ambos ocurre **después de LLMFit → LEONES** y antes de la medición física.

## 5. Hermes

LEONES no incorpora un Hermes paralelo por principio.

Se conserva y aprovecha **el Hermes que aporte ODS** cuando ODS sea la ruta elegida. Si posteriormente otro componente aporta un sistema agentivo mejor definido, se integra mediante contrato en lugar de duplicarlo.

La responsabilidad de LEONES sigue siendo medir y conservar evidencia de la ejecución, no apropiarse del agente.

## 6. AirLLM y FreeToken

**AirLLM y FreeToken se reservan como capacidades que LEONES aportará a ODS/Magnitude cuando llegue el momento.**

La política congelada es:

```text
AirLLM / FreeToken
       ↓
 evaluación de utilidad
       ↓
 contribución al upstream cuando sea posible
       ↓
 si no, conector/adaptador fino
       ↓
 ODS o Magnitude
```

No se incrustan prematuramente en el núcleo de LEONES.

La primera opción es contribuir a sus upstreams. El conector se utilizará cuando sea técnicamente necesario para integrar sin duplicar ni crear un fork innecesario.

## 7. Hardware de consumo es el objetivo principal

LEONES debe priorizar el hardware que realmente está al alcance del usuario final:

- portátiles;
- sobremesas convencionales;
- iGPU;
- GPU de consumo;
- CPU-only;
- configuraciones con RAM limitada;
- configuraciones con VRAM limitada.

Los tiers de hardware deben evolucionar desde una clasificación simple hacia una clasificación que capture las diferencias relevantes para inferencia local.

No se debe asumir que una máquina de consumo se comporta como un servidor solo porque ambos pueden ejecutar el mismo modelo.

## 8. LLMFit no es benchmark

LLMFit responde principalmente:

> **¿Qué podría encajar razonablemente en esta máquina?**

LEONES responde:

> **¿Qué ocurrió realmente cuando lo ejecutamos?**

Por tanto:

```text
LLMFit = hipótesis / fit
LEONES = decisión + ejecución + medición
```

Una recomendación puede empezar con una hipótesis de LLMFit, pero debe conservarse la distinción hasta disponer de medición.

## 9. Medición física pertenece a LEONES

El benchmark final no se delega al proyecto que ejecuta el agente.

LEONES fija y conserva:

- modelo e identidad;
- revisión;
- cuantización;
- runtime y versión;
- hardware;
- contexto;
- prompt/protocolo;
- warm-up;
- número de mediciones;
- límites de generación;
- tiempo;
- TTFT cuando esté disponible;
- tokens/s;
- memoria/VRAM cuando esté disponible;
- consumo cuando esté disponible;
- comando;
- stdout/stderr;
- timestamp;
- `execution_id`;
- hashes y artefactos.

Una medición sin condiciones y procedencia no es evidencia LEONES completa.

## 10. No confundir benchmark con agente

El throughput de inferencia y el rendimiento de una tarea agentiva son dimensiones diferentes.

LEONES conserva separadamente:

```text
runtime benchmark
agent benchmark
hardware measurement
outcome / grading
```

No se reduce la calidad de un agente a tokens/s.

## 11. Evidencia inmutable y trazable

Los artefactos medidos deben ser reproducibles y trazables.

Toda evidencia debe poder responder:

- quién midió;
- qué ejecutó;
- dónde;
- con qué configuración;
- cuándo;
- con qué resultado;
- qué artefacto lo demuestra.

La evidencia histórica no se sobrescribe para hacer que una medición antigua parezca una nueva.

## 12. Documentar antes de complicar

Antes de construir una pieza importante se documentan:

1. propósito;
2. frontera de responsabilidad;
3. entrada;
4. salida;
5. contrato;
6. evidencia;
7. tests;
8. dependencia externa;
9. criterio de cierre.

La documentación forma parte del producto, no es una actividad posterior.

## 13. Máxima documentación, mínima implementación

LEONES debe preferir:

> **mucho contrato y poca magia.**

Un componente pequeño, explícito y bien documentado es preferible a una abstracción grande que haga muchas cosas implícitamente.

## 14. Tests antes de declarar cerrado

Ningún jalón se considera cerrado solo porque una ejecución manual funcionó.

El cierre requiere, según corresponda:

- tests automatizados;
- validación contractual;
- `git diff --check`;
- árbol limpio;
- documentación actualizada;
- sincronización con el remoto;
- evidencia real cuando el objetivo sea físico.

## 15. Ubuntu solo cuando sea imprescindible

Durante el desarrollo se realiza todo lo posible sin tocar el entorno físico.

```text
diseño
→ contratos
→ documentación
→ tests
→ mocks / fixtures
→ integración sintética
→ validación
→ Ubuntu
→ ejecución física
```

Ubuntu se utiliza cuando necesitamos conocer algo que solo puede demostrar la máquina real: hardware efectivo, runtime instalado, comportamiento físico, rendimiento, consumo o compatibilidad real.

No se pide al usuario ejecutar comandos por comodidad del desarrollo.

## 16. Nada de rediseñar en Ubuntu

Cuando llegue Ubuntu, el diseño debe estar congelado.

La sesión física debe ser:

```text
instalar / comprobar
→ ejecutar
→ medir
→ conservar evidencia
→ comparar
→ decidir
```

No debe convertirse en una sesión de arquitectura improvisada.

## 17. Deprecación limpia

Cuando una pieza deje de pertenecer al camino canónico, no se borra automáticamente.

Se evalúa:

```text
¿aporta al RC1?
       │
   ┌───┴───┐
   sí      no
   │        │
 mantener  deprecated
```

Lo deprecated queda fuera del camino operativo y claramente señalado para evitar que vuelva a convertirse accidentalmente en dependencia.

## 18. Git disciplinado

Cada cambio coherente debe producir una historia legible.

Preferencias:

- ramas con propósito explícito;
- commits pequeños y semánticos;
- documentación junto al cambio que documenta;
- tests junto al contrato que protegen;
- ningún trabajo sin commit al declarar una fase cerrada;
- remoto sincronizado antes de congelar un hito.

## 19. No duplicar fuentes de verdad

Cada dato debe tener un dueño claro.

Ejemplos:

- identidad/evidencia de modelos → Atlas;
- fit inicial → LLMFit;
- decisión/orquestación → LEONES;
- ejecución especializada → runtime externo;
- medición física → LEONES;
- conocimiento colectivo publicado → MANADA.

Cuando dos componentes puedan convertirse en fuentes contradictorias, se define explícitamente cuál es canónica.

## 20. MANADA es la salida, no el origen

MANADA consume conocimiento ya validado.

La cadena es:

```text
fuentes
 ↓
prospección
 ↓
Atlas / evidencia
 ↓
LLMFit / fit
 ↓
LEONES / decisión
 ↓
ODS o Magnitude
 ↓
ejecución
 ↓
benchmark
 ↓
medición física
 ↓
evidencia validada
 ↓
MANADA
```

No se publica como hecho un resultado que todavía sea únicamente una hipótesis.

## 21. Criterio RC1

RC1 no significa que LEONES soporte todos los runtimes, todos los modelos ni todos los hardwares.

Significa que existe una **ruta mínima completa y demostrable**:

```text
hardware
  ↓
LLMFit
  ↓
LEONES
  ↓
ODS o Magnitude
  ↓
ejecución real
  ↓
benchmark LEONES
  ↓
evidencia
  ↓
recomendación
  ↓
MANADA
```

Una única ruta completa, limpia, documentada y reproducible vale más que diez integraciones a medias.

## 22. Regla de oro

> **LEONES no necesita hacerlo todo. Necesita hacer muy bien aquello que conecta el ecosistema, decide qué ejecutar, demuestra qué ocurrió y convierte esa evidencia en conocimiento útil.**

---

## Estado de congelación

Estas reglas quedan **congeladas para RC1**.

Cambiar una regla estructural requiere:

1. documentar la razón;
2. identificar qué contratos afecta;
3. actualizar esta especificación;
4. ejecutar los gates correspondientes;
5. registrar el cambio en Git.

La congelación no impide mejoras; impide que el alcance de RC1 cambie silenciosamente.
