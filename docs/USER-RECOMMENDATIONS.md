# LEONES — Recomendaciones de usuarios

**Estado:** operativo como flujo de descubrimiento, triage y validación por responsable  
**Fecha:** 2026-08-16

## Objetivo

Permitir que cualquier usuario aporte un recurso que pueda mejorar el conocimiento o las capacidades de LEONES: modelos, runtimes, backends, agentes, herramientas, benchmarks, datasets, hardware, proyectos, investigaciones o ideas.

La participación de usuarios es una **fuente de prospección**, no una fuente de verdad. Una recomendación nunca entra directamente en Atlas.

## Flujo canónico

```text
USUARIO
  ↓
FORMULARIO WEB
  ↓
ISSUE DE GITHUB
  ↓
ASIGNACIÓN AL RESPONSABLE
  ↓
NOTIFICACIÓN POR GITHUB / EMAIL
  ↓
"OK LEONES"
  ↓
DESCUBRIMIENTO AUTORIZADO
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

## Validación por email

La web es estática y no necesita un servidor de correo propio. Al crear la incidencia, GitHub Actions la asigna a `robertosantosx2`. GitHub puede enviar al responsable la notificación correspondiente según sus preferencias de notificación.

La respuesta de autorización es deliberadamente mínima: **`OK LEONES`**.

El workflow `.github/workflows/validate-user-recommendation.yml` reconoce esa respuesta cuando procede del responsable `robertosantosx2`, elimina `needs-review`, añade `validated-by-owner` y deja constancia de que la investigación ha sido autorizada.

La autorización **no significa integración**. Solo permite que LEONES dedique trabajo de investigación a esa recomendación.

> Importante: el envío real del correo depende de la configuración de notificaciones de GitHub de la cuenta responsable. No se almacenan contraseñas, SMTP ni claves API en LEONES.

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

## Estados

| Estado | Significado |
|---|---|
| `received` | Recibida como descubrimiento externo |
| `needs-review` | Pendiente de validación del responsable |
| `validated-by-owner` | El responsable autorizó investigar |
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

## Arquitectura y seguridad

La página no recibe directamente credenciales ni publica contenido con permisos propios. El usuario prepara una incidencia de GitHub y el workflow del repositorio aplica el ciclo de revisión. El token de GitHub Actions se limita a `issues: write`.

La respuesta `OK LEONES` se acepta solo del usuario de GitHub `robertosantosx2`, evitando que una recomendación pueda autoautorizarse desde otra cuenta.

## Privacidad

No se deben enviar contraseñas, tokens, claves API, datos personales sensibles ni información privada. El contacto es opcional. La recomendación puede evaluarse sin identificar al usuario.

## Relación con la arquitectura

El sistema encaja especialmente con **Prospector → Atlas → Benchmark & Evaluation → Router**. Las recomendaciones son una fuente adicional de descubrimiento humano que complementa la prospección automática y permite detectar recursos que los rastreadores todavía no conocen.

## Criterio de cierre

Una recomendación se considera realmente aprovechada cuando existe una decisión documentada: **integrada, observada o rechazada**, junto con la evidencia y el motivo. De esta forma LEONES aprende tanto de lo que incorpora como de lo que decide no incorporar.
