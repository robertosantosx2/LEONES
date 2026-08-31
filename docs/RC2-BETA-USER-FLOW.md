# RC2 — LEONES Beta User Flow

**Estado:** RC2-A implementado · RC2-B/H en preparación  
**Fecha:** 31 de agosto de 2026  
**Predecesor:** RC1 — ejecución efectiva validada  

## 1. Objetivo

RC2 convierte la cadena técnica validada en RC1 en un recorrido completo para un usuario beta tester que no necesita conocer la arquitectura interna de LEONES.

El usuario debe poder:

1. instalar LEONES;
2. declarar o detectar su hardware;
3. obtener un perfil de capacidad;
4. elegir el objetivo de evaluación;
5. comparar y seleccionar un modelo entre los candidatos propuestos;
6. elegir entre ODS y Magnitude después de conocer **todas las funcionalidades relevantes de cada opción**;
7. instalar/preparar el stack seleccionado con consentimiento para descargas y cambios;
8. decidir si quiere ejecutar un benchmark real;
9. recibir el resultado y conservar la evidencia reproducible;
10. opcionalmente compartir una evidencia anonimizada/consentida con el conocimiento colectivo.

RC2 no crea un sistema paralelo de selección, perfilado, benchmark ni ejecución. Orquesta los contratos y componentes ya fijados.

## 2. Experiencia canónica

```text
INSTALAR LEONES
      ↓
PREFLIGHT
      ↓
HARDWARE OBSERVADO / DECLARADO
      ↓
PERFILADO ODS / MAGNITUDE
      ↓
CANDIDATOS DE MODELO
      ↓
ELECCIÓN DEL USUARIO
      ↓
COMPARADOR ODS / MAGNITUDE
      ↓
ELECCIÓN DE STACK
      ↓
PREPARACIÓN / INSTALACIÓN
      ↓
¿BENCHMARK REAL?
   ┌───┴────┐
  NO       SÍ
   ↓        ↓
 FIN     RUNNER
            ↓
       MEDICIÓN
            ↓
         EVIDENCIA
            ↓
        RESULTADO
            ↓
   COMPARTIR (OPT-IN)
```

## 3. Principios de producto

### 3.1 LEONES recomienda; el usuario decide

La selección puede ordenar candidatos, pero no sustituye la decisión del usuario.

### 3.2 No esconder la naturaleza de ODS y Magnitude

La pantalla de elección debe presentar una ficha funcional de cada opción antes de pedir la elección.

No basta con mostrar los nombres «ODS» y «Magnitude».

### 3.3 No inventar capacidades

La ficha funcional debe construirse a partir de las capacidades verificadas en las integraciones y, cuando corresponda, de la versión/ref concreta instalada. Lo no comprobado debe permanecer explícitamente como desconocido.

### 3.4 Consentimiento antes de instalar

Las descargas grandes, cambios del sistema, servicios, contenedores, modelos y componentes auxiliares deben explicarse antes de ejecutarse.

### 3.5 Medición separada de estimación

`observed`, `configured`, `estimated`, `reported` y `measured` conservan significados distintos. RC2 nunca convierte una predicción de ODS/Magnitude en una medición LEONES.

### 3.6 Privacidad por defecto

No se deben enviar prompts, archivos, conversaciones, código, secretos ni API keys. Compartir evidencia con el colectivo será siempre opt-in.

## 4. Pantallas / etapas

### RC2-01 — Instalación

Entrada: sistema Linux compatible.

Salida: entorno LEONES operativo y versión/ref registrada.

Criterios:
- instalación reproducible;
- comprobación de dependencias;
- instrucciones de rollback/uninstall;
- versión de LEONES conservada.

### RC2-02 — Hardware

LEONES debe permitir detección y, cuando sea necesario, declaración/corrección por el usuario.

Campos objetivo:
- OS/distribución;
- arquitectura;
- CPU;
- RAM;
- GPU;
- VRAM;
- drivers;
- almacenamiento;
- aceleración disponible;
- información adicional exigida por ODS o Magnitude.

Toda información no disponible se conserva como `unknown`/`null`.

### RC2-03 — Perfilado

El sistema ejecuta el mecanismo correspondiente de ODS o Magnitude sin crear un tercer perfilador paralelo.

Resultado:
- capacidades observadas;
- restricciones;
- modelos candidatos;
- estimaciones, claramente marcadas como tales.

### RC2-04 — Selección de modelo

Presentar candidatos con suficiente contexto para que el usuario pueda decidir:

- modelo;
- variante/cuanti cuando esté disponible;
- memoria/requisitos;
- runtime;
- fundamento de la recomendación;
- evidencia existente, diferenciando estimada de medida.

El usuario confirma el modelo.

### RC2-05 — Elección ODS / Magnitude

Antes de elegir, mostrar las capacidades de cada alternativa.

**ODS — capacidades a exponer cuando estén disponibles en la versión/ref seleccionada:**
- inferencia local;
- Open WebUI;
- gateway;
- RAG/search;
- voz;
- agentes/workflows;
- generación de imágenes;
- privacidad;
- observabilidad;
- componentes/servicios instalables como llama-server, LiteLLM, TEI, Qdrant, SearXNG/Perplexica, Whisper/Kokoro, Hermes Agent, n8n, APE, OpenCode, ComfyUI, Dashboard, Privacy Shield, Token Spy y Langfuse.

**Magnitude — capacidades a exponer cuando estén disponibles en la versión/ref seleccionada:**
- agente local;
- modelos locales;
- perfilado de hardware;
- recomendación de modelos;
- descarga/configuración;
- ejecución local;
- skills;
- endpoints OpenAI-compatible.

Para ambos:
- versión/ref;
- requisitos;
- componentes que se instalarán;
- consumo de almacenamiento cuando pueda determinarse;
- requisitos de red;
- permisos;
- riesgos/limitaciones;
- qué parte aporta LEONES y qué parte aporta la integración.

La lista funcional es informativa y versionada: no debe presentarse como garantía de que todos los componentes están activos en cualquier instalación.

### RC2-06 — Instalación/preparación

Generar el plan concreto a partir de la elección confirmada.

Antes de ejecutar:
- mostrar componentes;
- mostrar descargas aproximadas si se conocen;
- solicitar consentimiento;
- registrar versión/ref;
- registrar configuración sin secretos.

Después:
- health check;
- servicios/runtime;
- modelo;
- configuración relevante.

### RC2-07 — Decisión de benchmark

Pregunta explícita:

> ¿Quieres medir el rendimiento real de esta combinación en tu equipo?

Opciones:
- **No:** terminar con instalación/configuración confirmada.
- **Sí:** ejecutar el benchmark canónico LEONES.

### RC2-08 — Benchmark real

Usar el runner canónico existente y el protocolo de medición fijado.

No crear un runner RC2 paralelo.

Registrar como mínimo:
- execution_id;
- modelo/variante;
- runtime/version/ref;
- hardware;
- protocolo;
- timestamps;
- métricas;
- outcome;
- artefactos;
- procedencia;
- SHA-256 cuando corresponda.

### RC2-09 — Resultado

Mostrar al usuario un resultado legible, por ejemplo:

```text
Modelo:             ...
Runtime:            ...
Hardware:           ...
Benchmark:          ...
Resultado:          ...
Medición:           REAL
Evidencia:          CONSERVADA
execution_id:       ...
```

Las métricas de velocidad son sólo una parte del resultado; la evaluación de tareas completadas tendrá prioridad cuando el benchmark correspondiente esté disponible.

### RC2-10 — Compartición opcional

Preguntar si el usuario desea contribuir la evidencia al conocimiento colectivo.

Nunca compartir automáticamente.

## 5. Contratos que RC2 reutiliza

RC2 debe consumir, no duplicar:

- selección de modelo/runtime;
- gate de autorización;
- decisión LEONES → ODS/Magnitude;
- contratos de integración ODS y Magnitude;
- protocolo de medición real;
- runner canónico;
- evidencia reproducible;
- benchmark de tareas completadas.

## 6. Fases de implementación

### RC2-A — Orquestación · 🟢 Implementado

`python3 scripts/rc2_beta.py` proporciona el primer punto de entrada CLI y conduce el recorrido mínimo sin obligar al usuario a conocer los scripts internos. Permite cargar una selección validada, mostrar las capacidades de ODS/Magnitude y registrar la decisión de benchmark.

**Límite:** no instala, descarga ni ejecuta runtimes. Las operaciones con efectos laterales quedan para las fases posteriores.

**Documento de implementación:** [`docs/RC2-A-IMPLEMENTATION.md`](RC2-A-IMPLEMENTATION.md).

### RC2-B — Hardware y perfilado

Conectar preflight con ODS/Magnitude y normalizar `observed`/`estimated`.

### RC2-C — Selección humana

Presentar candidatos y registrar la elección explícita.

### RC2-D — Comparador funcional ODS/Magnitude

Presentar las capacidades completas y versionadas de ambas opciones antes de la elección.

### RC2-E — Instalación controlada

Preparar el stack elegido con consentimiento, health check y rollback/uninstall documentados.

### RC2-F — Benchmark opcional

Conectar la decisión Sí/No con el runner canónico y la evidencia real.

### RC2-G — Resultado y contribución

Mostrar resultado y ofrecer compartición opt-in.

### RC2-H — Piloto beta

Probar el recorrido con máquinas externas y registrar problemas de instalación, selección, runtime, benchmark y evidencia.

## 7. Definition of Done de RC2

RC2 sólo se considera validado cuando un beta tester externo puede completar el flujo completo sin intervención del desarrollador:

- [ ] instalar LEONES;
- [ ] detectar/declarar hardware;
- [ ] obtener perfil;
- [ ] recibir candidatos;
- [ ] seleccionar modelo;
- [ ] ver las funcionalidades de ODS y Magnitude antes de elegir;
- [ ] elegir ODS o Magnitude;
- [ ] instalar/preparar el stack con consentimiento;
- [ ] pasar health checks;
- [ ] elegir benchmark Sí/No;
- [ ] si elige Sí, producir una medición real con el runner canónico;
- [ ] conservar evidencia reproducible;
- [ ] mostrar resultado comprensible;
- [ ] no filtrar datos privados;
- [ ] poder repetir o desinstalar el flujo;
- [ ] documentar cualquier limitación real encontrada.

## 8. Fuera de alcance inicial

- GUI compleja;
- aplicación móvil;
- sistema de scoring alternativo;
- benchmark sintético que sustituya al benchmark LEONES;
- telemetría obligatoria;
- subida automática de datos;
- soporte universal de hardware sin evidencia.

## 9. Relación con RC1

RC1 validó el tramo:

```text
selección → gate → runtime real → A01 → medición → evidencia
```

RC2 convierte ese tramo en una experiencia de usuario completa y reproducible:

```text
usuario → hardware → perfilado → candidatos → elección
        → ODS/Magnitude → instalación → benchmark opcional
        → ejecución real → evidencia → resultado
```

**RC1 demuestra que la máquina funciona. RC2 demuestra que una persona puede utilizarla.**
