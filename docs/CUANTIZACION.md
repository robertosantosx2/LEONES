# LEONES — Cuantización

## Estado

**🟢 Elemento definido · listo para implementar**

La cuantización es una capacidad técnica independiente de LEONES para transformar/reducir la representación numérica de un modelo con el objetivo de modificar memoria, rendimiento y/o coste de inferencia, conservando trazabilidad entre modelo base y artefacto cuantizado.

## Principio

```text
MODELO BASE
    ↓
IDENTIDAD / LICENCIA
    ↓
CONFIGURACIÓN DE CUANTIZACIÓN
    ↓
PROCESO
    ↓
ARTEFACTO CUANTIZADO
    ↓
VALIDACIÓN
    ↓
EVIDENCIA
    ↓
QUALITY GATE
    ↓
ATLAS
```

Cuantizar no crea automáticamente una nueva entidad de modelo base: genera un artefacto/variante relacionado con un origen identificable.

## Entrada

Como mínimo:

- `base_model_id`;
- versión/commit del modelo base;
- arquitectura;
- tokenizer cuando sea relevante;
- método/formato de cuantización;
- precisión objetivo;
- parámetros del proceso;
- runtime/backend previsto;
- hardware objetivo;
- dataset/calibración si aplica;
- herramientas y versiones.

## Métodos y formatos

El esquema debe permitir registrar sin asumir una única tecnología:

- familia de cuantización;
- bits por peso cuando aplique;
- activaciones cuando aplique;
- esquema estático/dinámico cuando aplique;
- formato de almacenamiento;
- backend/runtime;
- parámetros específicos.

Los valores concretos se registran como datos de la ejecución, no como reglas codificadas en el contrato.

## Salida

El resultado debe conservar:

- `quantization_id`;
- relación con `base_model_id`;
- artefacto o referencia;
- hash/identificador del artefacto cuando exista;
- configuración completa;
- herramientas/versiones;
- hardware utilizado;
- métricas de tamaño/memoria;
- rendimiento medido si se ejecuta;
- calidad/benchmark si se ejecuta;
- limitaciones;
- evidencia.

## Validación

Debe distinguir:

```text
ARTEFACTO GENERADO
≠
ARTEFACTO FUNCIONAL
≠
RENDIMIENTO MEDIDO
≠
CALIDAD PRESERVADA
```

La cuantización solo se considera validada para las propiedades realmente comprobadas.

## Evidencia física

Si se declara rendimiento en un hardware concreto, se exige medición reproducible del artefacto concreto. Una cifra extrapolada desde el modelo base permanece como estimación.

## Compatibilidad

La validación puede cubrir:

- carga del artefacto;
- inferencia;
- tokenizer;
- contexto;
- herramientas/runtime;
- GPU/CPU/VRAM/RAM;
- batching cuando aplique.

La ausencia de una prueba no se convierte en compatibilidad afirmada.

## Quality Gate

```text
base model
   ↓
licencia / OSI
   ↓
cuantización
   ↓
evidencia
   ↓
Quality Gate
   ↓
variante/artefacto aceptado
```

El artefacto no puede usar la cuantización como vía para eludir las condiciones aplicables al modelo base o a sus componentes.

## Router

Router puede tratar una variante cuantizada como opción de ejecución cuando su compatibilidad y evidencia cumplen las restricciones aplicables. Las preferencias del usuario no pueden alterar OSI.

## MANADA / Agentic

La cuantización puede ser utilizada como etapa previa o alternativa de ejecución, pero no cambia por sí misma el estado de un agente/harness respecto a Gate OSI.

## Observabilidad

Cada proceso debe producir `trace_id`/`run_id` y registrar:

- tiempos;
- recursos;
- comandos/proceso lógico;
- versiones;
- errores;
- artefactos generados.

## Estados

```text
DISCOVERED
INPUT_VALIDATED
QUEUED
RUNNING
ARTIFACT_CREATED
VALIDATION_PENDING
VERIFIED
REVIEW
FAILED
SUPERSEDED
```

## No concurrencia

Se permite paralelizar cuantizaciones independientes. La promoción de resultados canónicos utiliza `leones-main-writers` con `cancel-in-progress: false`.

## Seguridad

Los artefactos y scripts externos se consideran no confiables hasta su validación. Las credenciales no forman parte de configuraciones ni artefactos publicados.

## Implementación futura

La primera implementación debe separar claramente:

1. descripción del trabajo;
2. ejecución;
3. validación;
4. evidencia;
5. promoción.

No se certificará ninguna ventaja de rendimiento/calidad sin medición reproducible.
