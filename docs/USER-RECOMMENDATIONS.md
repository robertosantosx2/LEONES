# LEONES — Recomendaciones de usuarios

**Estado:** operativo como flujo de descubrimiento y triage  
**Fecha:** 2026-08-16

## Objetivo

Permitir que cualquier usuario aporte un recurso que pueda mejorar el conocimiento o las capacidades de LEONES: modelos, runtimes, backends, agentes, herramientas, benchmarks, datasets, hardware, proyectos, investigaciones o ideas.

La participación de usuarios se considera una **fuente de prospección**, no una fuente de verdad. Una recomendación nunca entra directamente en Atlas.

## Flujo canónico

```text
USUARIO
  ↓
FORMULARIO
  ↓
DESCUBRIMIENTO EXTERNO
  ↓
IDENTIDAD + PROCEDENCIA
  ↓
TRIAGE
  ↓
EVIDENCIA TÉCNICA
  ↓
VERIFICACIÓN / REPRODUCCIÓN
  ↓
PERFIL
  ↓
DECISIÓN
  ├── integrar en Atlas / componente LEONES
  ├── mantener en observación
  └── descartar con motivo
```

Este flujo complementa la capa de evidencia definida en la fase H10. No se utiliza una puntuación de ajuste como sustituto de la evidencia.

## Qué recoge el formulario

- nombre e identidad del recurso;
- URL principal;
- tipo de recurso;
- pilar LEONES potencialmente relacionado;
- explicación del usuario;
- señales de interés: apertura, local, agentes, rendimiento, hardware y evaluación;
- tipo de evidencia que afirma haber observado;
- contacto opcional.

No se solicitan claves, credenciales ni datos sensibles.

## Triage inicial

El navegador calcula una **señal inicial 0–10** únicamente para ordenar la cola. Tiene en cuenta existencia de URL, calidad mínima de la explicación, tipo de evidencia y señales declaradas.

La señal no determina la aceptación. Una recomendación con 10/10 puede ser descartada y una recomendación con una señal baja puede resultar valiosa después de una investigación.

### Estados

| Estado | Significado |
|---|---|
| `received` | Recibida como descubrimiento externo |
| `triage` | Se comprueba relevancia e identidad |
| `evidence` | Se busca evidencia técnica independiente |
| `verification` | Se reproduce, ejecuta o contrasta |
| `candidate` | Tiene suficiente evidencia para considerar integración |
| `integrated` | Se incorporó al conocimiento o a un componente |
| `watch` | Interesante pero todavía insuficiente |
| `rejected` | No encaja o la evidencia no sostiene la propuesta |

## Criterios de integración

Una recomendación puede alimentar LEONES cuando, según el caso, demuestra uno o varios de estos valores:

1. **Conocimiento nuevo:** añade una entidad, relación, benchmark, licencia, runtime, hardware o evidencia que Atlas no tenía.
2. **Capacidad nueva:** mejora Runtime, Agents, Quant, Fine-Tuning u otra pieza funcional.
3. **Mejor decisión:** aporta información que puede hacer mejor el Router o Task Intelligence.
4. **Mejor medición:** aporta un benchmark reproducible o una metodología útil.
5. **Mejor prospección:** permite descubrir automáticamente más recursos o cambios relevantes.
6. **Mejor experiencia:** reduce coste, latencia, complejidad o fricción con evidencia suficiente.

## Reglas de evidencia

- `measured`: medido por LEONES o por una prueba reproducible claramente identificada.
- `reported`: declarado por el proyecto o proveedor.
- `estimated`: estimado con método explícito.
- `calculated`: derivado matemáticamente de datos conocidos.
- `anecdotal`: experiencia individual sin control suficiente.

Los resultados externos no se convierten automáticamente en mediciones LEONES.

## Qué aprende LEONES

La recomendación puede generar aprendizaje en cuatro niveles:

- **Atlas:** nueva entidad, relación o evidencia.
- **Prospector:** nueva fuente, patrón de descubrimiento o término de búsqueda.
- **Router:** nueva restricción, adaptador, compatibilidad o señal de selección.
- **Benchmark & Evaluation:** nueva prueba, tarea, métrica o caso límite.

También puede provocar una modificación de documentación, una nueva prueba automatizada, un adaptador o una futura tarea de desarrollo.

## Limitación actual del formulario web

La web de LEONES se publica como sitio estático. Por ello, el formulario no escribe directamente en una base de datos ni publica automáticamente una incidencia. Tras el triage local ofrece:

- **Preparar recomendación en GitHub**, que abre una incidencia pre-rellenada para revisión;
- **Guardar JSON**, para conservar el registro estructurado localmente.

Esto evita introducir un backend externo, secretos o un canal de recepción opaco. En una fase posterior puede sustituirse por un endpoint propio manteniendo exactamente el mismo esquema `leones-user-recommendation/v1`.

## Privacidad

No se deben enviar contraseñas, tokens, claves API, datos personales sensibles ni información privada. El contacto es opcional. La recomendación puede evaluarse sin identificar al usuario.

## Relación con la arquitectura

El sistema encaja especialmente con **Prospector → Atlas → Benchmark & Evaluation → Router**. Las recomendaciones son una fuente adicional de descubrimiento humano que complementa la prospección automática y permite detectar recursos que los rastreadores todavía no conocen.
