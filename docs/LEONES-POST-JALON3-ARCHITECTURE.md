# LEONES después de JALÓN 3 — arquitectura mínima

> **Estado: ORIENTACIÓN NORMATIVA RC1**
>
> JALÓN 3 está cerrado. Este documento redefine qué debe ser LEONES a partir de ahora.

## 1. Decisión arquitectónica

LEONES no debe reconstruir herramientas que ya resuelven partes del problema.

La arquitectura post-JALÓN 3 es una **capa de decisión, evidencia, comparación y recomendación** que coordina herramientas especializadas.

```text
Magnitude / hardware tools
          │
          ▼
       hardware
          │
          ▼
        LEONES
          │
    ┌─────┴─────┐
    ▼           ▼
 LLMFit       Atlas
    │           │
    └─────┬─────┘
          ▼
   candidate + fit
          │
          ▼
     runtime gate
          │
     ┌────┴────┐
     ▼         ▼
 llama.cpp   ODS
     │         │
     │      stack/runtime
     │         │
     └────┬────┘
          ▼
       execution
          │
       Hermes
          │
        A01
          │
          ▼
     measurement
          │
       evidence
          │
       validation
          │
    recommendation
          │
          ▼
        MANADA
```

## 2. Responsabilidad de cada pieza

| Pieza | Responsabilidad | LEONES no debe duplicarla |
|---|---|---|
| Magnitude | caracterización/medición de hardware cuando sea útil y verificable | sensores y perfilado especializado |
| LLMFit | estimación de encaje de modelos con hardware | motor de fit completo |
| Atlas | conocimiento/catálogo y procedencia de modelos | catálogo paralelo innecesario |
| llama.cpp | primera ruta de inferencia física canónica | implementar otro runtime |
| ODS | stack/appliance local y automatización de despliegue | construir otro instalador generalista |
| Hermes | harness/tareas agentivas | construir otro harness agentivo |
| LEONES | **contratos, gates, orquestación, procedencia, evidencia, comparación y recomendación** | — |
| MANADA | publicación del conocimiento resultante | sistema paralelo de publicación |

## 3. Regla de minimalismo

Una capacidad externa se integra antes de ser reimplementada.

Una capacidad sólo se implementa en LEONES si cumple al menos una de estas condiciones:

1. es parte de la decisión que LEONES debe tomar;
2. es necesaria para conservar procedencia/evidencia;
3. es un contrato que las herramientas externas no comparten;
4. es necesaria para comparar resultados de fuentes diferentes;
5. es necesaria para generar una recomendación reproducible.

Si una herramienta externa ya hace bien una tarea y puede exponerse mediante un adapter estable, **se reutiliza**.

## 4. Evidencia como frontera

La autoridad de LEONES no es el resultado que una herramienta declara. Es el resultado que puede clasificarse y conservarse.

Se mantienen las categorías:

- `estimated` — cálculo/estimación;
- `reported` — declaración externa;
- `observed` — configuración observada;
- `measured` — medición física ejecutada;
- `verified` — medición/evidencia que supera un quality gate;
- `unknown` — no demostrado.

Una herramienta puede producir una estimación excelente y seguir siendo `estimated`. LEONES no la convierte en `measured` por confianza.

## 5. ODS no sustituye a LEONES

ODS puede cubrir instalación, detección, selección y ejecución de un stack local. LEONES lo trata como **stack/appliance externo**.

ODS puede decir cómo ejecutar.
LEONES debe poder decir qué se observó, bajo qué condiciones, qué evidencia existe y qué puede recomendarse.

La instalación de ODS será opcional para el MVP hasta que una ejecución real supere el gate físico.

## 6. Magnitude no sustituye a LEONES

Magnitude es una fuente/instrumento de caracterización. Sus resultados alimentan el perfil hardware cuando sean identificables, reproducibles y pertinentes.

LEONES no debe asumir que una estimación de capacidad equivale a un benchmark de modelo.

## 7. Hermes tampoco es LEONES

Hermes es el primer harness agentivo de referencia.

LEONES define:

- cuándo está autorizado;
- qué runtime/modelo lo soporta;
- qué tarea se ejecuta;
- qué evidencia se conserva;
- cómo se relaciona la trayectoria con la medición del runtime.

## 8. Camino canónico RC1

El producto mínimo debe demostrar sólo un recorrido completo:

```text
perfil hardware
 → candidatos
 → fit
 → runtime autorizado
 → Hermes/A01
 → ejecución real
 → medición
 → evidence bundle
 → validation
 → recommendation
 → MANADA
```

Todo lo demás es extensión.

## 9. Criterio para incorporar ODS y Magnitude

No se incorporan porque sean conocidos o interesantes.

Se incorporan si una prueba concreta demuestra que aportan información/capacidad útil al camino canónico.

Cada integración tendrá:

```text
identity
 → version/commit
 → license
 → adapter
 → contract tests
 → physical gate
 → evidence
```

## 10. Qué queda fuera de RC1

No son objetivos de RC1:

- soportar todos los runtimes;
- construir un catálogo perfecto;
- replicar ODS;
- replicar LLMFit;
- crear un benchmark universal;
- soportar todas las GPU;
- automatizar todos los sistemas operativos;
- resolver todos los casos agentivos.

RC1 demuestra **una ruta completa y honesta**, no amplitud artificial.

## 11. Definition of Done arquitectónica

RC1 sólo se considera arquitectónicamente válida cuando:

- existe un único camino canónico;
- las dependencias externas están delimitadas;
- las responsabilidades no se duplican;
- la evidencia conserva procedencia;
- las estimaciones no se presentan como mediciones;
- Hermes está desacoplado del runtime;
- Magnitude puede alimentar hardware sin convertirse en autoridad absoluta;
- ODS puede actuar como stack sin convertirse en autoridad de rendimiento;
- los resultados pueden llegar estructurados a MANADA.
