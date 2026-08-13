# LEONES — Local Ecosystem of Open Neural Expert Systems

> **IA agéntica Libre/Open para hardware de consumo.**
>
> **Linux primero · evidencia real · conocimiento colectivo.**

[🌐 **Web de LEONES y dashboard de la Manada**](https://robertosantosx2.github.io/LEONES/)

[⚙️ **Aplicación LEONES**](https://robertosantosx2.github.io/LEONES/app.html)

[🦁 **Repositorio GitHub**](https://github.com/robertosantosx2/LEONES)

---

## ¿Qué es LEONES?

LEONES investiga, mide y construye un ecosistema de IA agéntica Libre/Open que pueda ejecutarse en **hardware real de consumo**, con especial prioridad al software **Copyleft**.

No pretende ser simplemente otro catálogo de modelos. El proyecto intenta responder una pregunta práctica:

> **¿Qué combinación de hardware, modelo, runtime, herramientas y arquitectura permite convertir un PC de consumo en una máquina agentic realmente útil?**

Y una segunda pregunta es igual de importante:

> **¿Cómo podemos transformar las mediciones de muchos equipos reales en mejores recomendaciones para todos?**

Por eso LEONES combina **prospección, conocimiento estructurado, experimentación local, benchmarks agentivos, evidencia reproducible y conocimiento colectivo**.

---

## La filosofía LEONES

### 1. Empieza por la necesidad, no por el script

LEONES no pretende que el usuario ejecute una colección de herramientas porque existen. La aplicación pregunta primero qué quiere conseguir y conduce al **siguiente paso mínimo** que responde a esa necesidad.

> **No ejecutes un script porque existe: ejecútalo porque responde a tu siguiente pregunta.**

El flujo general es:

```text
NECESIDAD
   ↓
HARDWARE
   ↓
MODELO
   ↓
RUNTIME
   ↓
INFERENCIA
   ↓
EVALUACIÓN / AGENTIC
   ↓
INFORME
   ↓
PRIVACIDAD
   ↓
PUBLICACIÓN
   ↓
ESTADÍSTICAS
   ↓
MEJORES RECOMENDACIONES
```

El usuario puede detenerse en cualquier punto. No todos necesitan llegar a Evaluación, publicar resultados o formar parte de la Manada.

### 2. Herramientas pequeñas y responsabilidades claras

Los scripts son la interfaz local mínima entre una persona y LEONES. Cada herramienta debe responder a **una pregunta concreta** y hacer las menores cosas posibles.

La separación canónica es:

| Herramienta | Pregunta | Responsabilidad |
|---|---|---|
| `leones-hardware.py` | ¿Qué máquina tengo? | Descubrir y explicar el hardware relevante. |
| `leones-model.py` | ¿Qué modelo tengo? | Identificar el modelo y sus metadatos básicos. |
| `leones-runtime.py` | ¿Qué runtime local tengo? | Detectar endpoints/runtimes disponibles. |
| `leones-infer.py` | ¿Cómo rinde una inferencia pequeña? | Medir inferencia básica reproducible. |
| `leones-evaluation.py` | ¿Puede completar tareas agentivas? | Medir tareas agentivas con criterios explícitos. |
| `leones-report.py` | ¿Qué evidencia tengo? | Convertir resultados en un informe legible. |
| `leones-privacy.py` | ¿Qué puede salir de mi máquina? | Revisar posibles datos sensibles. |
| `leones-publish.py` | ¿Quiero compartirlo? | Publicar únicamente mediante acción explícita. |
| `leones-stats.py` | ¿Qué aprende el conjunto? | Agregar resultados sin convertirlos artificialmente en evidencia verificada. |
| `leones-manada-report.py` | ¿Quiero aportar un informe? | Preparar un informe técnico para la Manada. |
| `leones-manada-stats.py` | ¿Qué aprende la Manada? | Agregar los informes compartidos voluntariamente. |

El orquestador puede coordinar el recorrido, pero **no debe absorber la responsabilidad de todos los componentes**.

Los scripts antiguos o especializados se conservan durante la migración hasta que exista una decisión explícita de sustitución, evitando duplicar funciones sin motivo.

### 3. Cada herramienta debe hablar con el usuario

La ejecución no debe ser una caja negra. Cada script debe explicar:

**Antes**
- qué pregunta responde;
- qué va a hacer;
- qué no va a hacer;
- requisitos;
- qué datos producirá;
- qué información no debería salir del equipo.

**Durante**
- qué etapa está ejecutando;
- progreso visible;
- errores accionables;
- ninguna operación oculta.

**Después**
- qué significa el resultado;
- cuáles son sus límites;
- qué no demuestra;
- cuál es el siguiente paso recomendado;
- cómo puede contribuir voluntariamente a la Manada.

Cuando exista información reutilizable, se produce **JSON estructurado** para que los siguientes componentes no tengan que interpretar texto humano.

---

## Libre/Open, no simplemente «gratis»

**Libre** se utiliza deliberadamente frente a «free»: interesa la libertad del software, no su precio.

LEONES prioriza software Open y, dentro de él, especialmente **Copyleft**. La apertura del ecosistema importa porque el objetivo no es depender de una caja negra que solo funcione en un proveedor concreto.

La pila de referencia inicial contempla **Buddy (GPL-3.0), Hermes, LangGraph, llama.cpp y GGUF**, sin considerar esa combinación una arquitectura inmutable: la evidencia puede hacer evolucionar las recomendaciones.

---

## Hardware de consumo como punto de partida

Los perfiles objetivo incluyen **8, 16, 32 y 64 GB de RAM**, con CPU Intel i5/i7 o equivalentes, con o sin GPU.

LEONES presta especial atención a configuraciones que una persona pueda tener realmente en casa o en un portátil/PC convencional. El objetivo no es demostrar que un modelo funciona en un servidor gigantesco, sino saber **qué puede hacerse localmente con recursos razonables**.

**10 tok/s** se utiliza como umbral orientativo de usabilidad LEONES. **100 tok/s** es un techo de comparación, no un requisito universal.

Pero los tokens por segundo nunca son suficientes por sí solos.

---

## Linux primero: Debian, Ubuntu y RHEL

LEONES tiene tres plataformas Linux de referencia explícita:

| Plataforma | Estado |
|---|---|
| **Debian** | 🟢 Referencia |
| **Ubuntu** | 🟢 Referencia |
| **Red Hat Enterprise Linux (RHEL)** | 🟢 Referencia |

**Debian no es una variante secundaria de Ubuntu.** Las tres plataformas tienen el mismo nivel conceptual dentro de la matriz inicial.

Los scripts deben detectar la distribución mediante `/etc/os-release` cuando sea relevante y **no asumir que todo Linux es Ubuntu ni que existe `apt` o `dnf`**. Siempre que sea posible, la lógica de los scripts debe depender únicamente de Python y de la librería estándar; los gestores de paquetes quedan para las instrucciones de preparación.

La compatibilidad se considera demostrada cuando existen **pruebas reproducibles**, no solamente porque la documentación declare soporte.

Véase [`docs/PLATFORMS.md`](docs/PLATFORMS.md) para la matriz y las instrucciones de preparación.

---

## Inferencia y agentic: dos preguntas diferentes

Evaluación separa dos niveles:

1. **Inferencia:** modelo + backend + hardware.
2. **Agentic:** agente + herramientas + tareas.

Que un modelo alcance una determinada velocidad no demuestra que pueda utilizarse como agente útil.

Por eso el pipeline distingue entre medir **tokens/segundo** y medir la capacidad de completar tareas reales.

---

## Evaluación agentiva

La batería inicial contiene cinco tareas:

- **B01 — memoria/localidad**
- **B02 — operación sobre archivos**
- **B03 — tarea multietapa**
- **B04 — recuperación ante fallo**
- **B05 — coding local**

Evaluación no debe confundir «el endpoint respondió» con «la tarea fue realizada correctamente».

Las evaluaciones pueden producir estados como:

- `pass`
- `fail`
- `manual_review`
- `tool_unavailable`
- `not_evaluable`

Esto permite distinguir entre una respuesta textual y una demostración verificable.

El baseline inicial es **Qwen3-8B Q4_K_M GGUF**.

---

## Evidencia y estados de confianza

LEONES distingue explícitamente entre:

- **`reported`** — alguien ha aportado un resultado;
- **`reproducible`** — existe información suficiente para repetirlo;
- **`verified`** — el resultado ha superado los controles correspondientes;
- **`rejected`** — no debe formar parte del conocimiento operativo.

Un resultado medido **no se convierte automáticamente en evidencia verificada**.

Esta distinción es fundamental para evitar que el conocimiento colectivo termine mezclando estimaciones, declaraciones de usuarios y resultados realmente comprobados.

---

## Prospección → Atlas → Router

LEONES mantiene un bucle de conocimiento separado del bucle de ejecución local:

```text
PROSPECTOR
    ↓
external-unvalidated
    ↓
revisión
    ↓
ATLAS
    ↓
ROUTER
```

### Prospector

Busca continuamente modelos, runtimes, benchmarks, harnesses, skills, técnicas de eficiencia y otros elementos relevantes del ecosistema.

**Descubre; no valida.**

### Atlas

Conserva el conocimiento estructurado y su procedencia. Es la memoria del ecosistema.

### Router

Utiliza ese conocimiento para responder a la pregunta práctica:

> **«Con esta máquina y esta necesidad, ¿qué debería probar?»**

El objetivo final es que Router deje de depender de reglas genéricas y pueda utilizar evidencia real acumulada.

---

## 🦁 Manada LEONES: el conocimiento colectivo

La Manada es una parte esencial del proyecto, pero **la participación es voluntaria**.

La idea es sencilla:

```text
TU PC
  ↓
MEDICIÓN LOCAL
  ↓
RESULTADO
  ↓
REVISIÓN DE PRIVACIDAD
  ↓
MANADA
  ↓
DATOS AGREGADOS
  ↓
MEJORES RECOMENDACIONES
```

Una medición aislada puede parecer pequeña. Miles de mediciones sobre hardware real permiten descubrir qué modelos, runtimes y combinaciones funcionan realmente en cada segmento de hardware.

### Qué no se debe publicar

LEONES no debe publicar:

- nombres o identidad personal;
- emails;
- usuarios identificables;
- hostnames identificables;
- números de serie;
- UUID;
- MAC/IP;
- ubicación exacta;
- rutas personales;
- credenciales;
- tokens o secretos;
- contenido privado.

`leones-privacy.py` realiza comprobaciones preventivas, pero **un resultado `clear` no significa que el contenido sea matemáticamente anónimo**.

Ningún script publica por defecto. La publicación siempre requiere una acción explícita.

---

## 📣 Difusión social voluntaria

La aplicación LEONES incorpora una opción específica para quienes quieran ayudar a difundir sus mediciones.

El usuario puede autorizar que LEONES **prepare un tweet con el resultado técnico**, siempre sin datos personales. La aplicación no publica silenciosamente en su nombre: abre un borrador en X para que el usuario lo revise y decida.

Después puede guardar el enlace del tweet publicado y abrirlo nuevamente para **retuitearlo**.

La invitación es deliberada: compartir el resultado ayuda a dar visibilidad a LEONES y puede atraer nuevas contribuciones a la Manada.

El objetivo no es hacer publicidad por sí misma, sino aumentar el número de mediciones reales que alimentan el conocimiento colectivo.

---

## Aplicación web

`web/app.html` es el **centro de operaciones** de LEONES.

No es un simple panel de scripts. Su función es conducir al usuario por el proceso:

1. **Necesidad** — ¿qué quiero conseguir?
2. **Hardware** — ¿qué máquina tengo?
3. **Modelo** — ¿qué quiero probar?
4. **Runtime** — ¿con qué lo voy a ejecutar?
5. **Inferencia** — ¿cómo rinde?
6. **Evaluación** — ¿puede realizar tareas agentivas?
7. **Informe** — ¿qué evidencia tengo?
8. **Privacidad** — ¿qué puedo compartir?
9. **Manada** — ¿quiero contribuir?
10. **Estadísticas** — ¿qué aprende LEONES?

La aplicación genera comandos para la ejecución **local** y explica el siguiente paso. GitHub Pages no ejecuta comandos en el ordenador del usuario.

El progreso del recorrido puede mantenerse localmente en el navegador para que la experiencia funcione como una guía y no como una colección de páginas aisladas.

---

## Privacidad y control del usuario

LEONES sigue una regla sencilla:

> **Local → revisar → publicar → agregar → aprender.**

La persona mantiene el control sobre lo que sale de su máquina. La aplicación puede ayudar a detectar datos sensibles, pero no sustituye la revisión humana.

La publicación social requiere igualmente autorización explícita.

---

## Objetivo final

LEONES quiere cerrar un bucle que hoy todavía está en construcción:

```text
PROSPECCIÓN DIARIA
       ↓
CONOCIMIENTO ESTRUCTURADO
       ↓
RECOMENDACIÓN
       ↓
EJECUCIÓN LOCAL
       ↓
MEDICIÓN
       ↓
EVIDENCIA
       ↓
MANADA
       ↓
NUEVO CONOCIMIENTO
       ↺
```

El valor del proyecto no está únicamente en saber qué modelo es mejor hoy. Está en construir un sistema capaz de **aprender continuamente qué funciona en hardware real y utilizar ese conocimiento para recomendar mejor mañana**.

---

## Documento fundamental

**[Historia, decisiones y fundamentos del proyecto](LEONES_DECISION_LOG.md)** contiene el contexto completo que llevó a estas decisiones y debe ser una de las primeras lecturas para entender LEONES.

Documentación especialmente relevante:

- [`scripts/README.md`](scripts/README.md) — filosofía y contrato de los scripts.
- [`docs/PLATFORMS.md`](docs/PLATFORMS.md) — plataformas Linux de referencia.
- [`docs/PILLARS.md`](docs/PILLARS.md) — pilares del proyecto.
- [`docs/PROSPECTION.md`](docs/PROSPECTION.md) — prospección.
- [`docs/RESULT_SCHEMA.md`](docs/RESULT_SCHEMA.md) — contrato de resultados.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura.
- [`docs/MANADA_AUTO_REPORT.md`](docs/MANADA_AUTO_REPORT.md) — generación de informes de la Manada.
- [`docs/MANADA_STATS.md`](docs/MANADA_STATS.md) — estadísticas de la Manada.

---

## Estado

**Proyecto experimental en desarrollo.** La arquitectura inicial está congelada como referencia, pero la optimización del ecosistema, los benchmarks, los runtimes, los modelos, la prospección y las métricas siguen abiertas a la evidencia.

La regla general continúa siendo:

> **medir antes de afirmar, documentar antes de automatizar y compartir voluntariamente para que el conocimiento colectivo mejore las recomendaciones.**
