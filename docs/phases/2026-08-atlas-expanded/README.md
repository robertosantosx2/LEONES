# H06 — Open LLM Atlas ampliado

**Estado: 🔵 SIGUIENTE / EN INICIO**

## Objetivo

Ampliar y depurar el Open LLM Atlas como capa estructurada de conocimiento de LEONES, aumentando cobertura, procedencia, calidad y trazabilidad de modelos, familias, organizaciones, variantes, runtimes, benchmarks y evidencia.

H06 se apoya en la infraestructura diaria H10, que ya está aceptada, pero su aceptación será independiente.

## Principio rector

```text
DESCUBRIR
   ↓
IDENTIFICAR
   ↓
NORMALIZAR
   ↓
RELACIONAR
   ↓
DOCUMENTAR PROCEDENCIA
   ↓
CLASIFICAR EVIDENCIA
   ↓
VALIDAR
   ↓
PUBLICAR
```

El Atlas no será simplemente un catálogo de nombres: cada dato relevante debe poder distinguir entre información reportada, reproducible, verificada o desconocida.

## Alcance inicial

1. Modelos y variantes.
2. Familias y organizaciones.
3. Repositorios y procedencia.
4. Arquitectura, parámetros, contexto, pesos y formatos cuando exista evidencia.
5. Runtimes, backends y formatos de ejecución.
6. Benchmarks y resultados con fuente y fecha.
7. Estados de evidencia.
8. Integración con JGB sin sustituir la clasificación de apertura por un score de rendimiento.
9. Contratos de datos para alimentar hardware y recomendación.

## Fuera de alcance de H06

- Declarar que un modelo está benchmarkeado si solo existe información externa.
- Convertir automáticamente datos externos en `verified`.
- Sustituir la clasificación de apertura por una puntuación económica o de rendimiento.
- Cerrar CABE/RULA empíricamente: eso pertenece a H09 y a benchmarks posteriores.

## Arquitectura prevista

```text
                 FUENTES
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
     MODELOS      SOFTWARE     BENCHMARKS
       │            │            │
       └────────────┼────────────┘
                    ▼
             NORMALIZACIÓN
                    │
                    ▼
               OPEN LLM ATLAS
          ┌─────────┼─────────┐
          ▼         ▼         ▼
      entidades  evidencia  relaciones
          │         │         │
          └─────────┼─────────┘
                    ▼
              VALIDACIÓN QA
                    │
                    ▼
              H10 / JGB / HW
```

## Reglas de datos

- No inventar valores.
- Mantener `unknown` cuando no exista evidencia.
- Conservar procedencia y fecha siempre que estén disponibles.
- Separar identidad de modelo, variante, familia y organización.
- Separar evidencia externa de medición LEONES.
- No confundir parámetros totales con parámetros activos.
- No confundir tamaño de pesos con memoria total de ejecución.
- No confundir contexto máximo declarado con contexto efectivamente probado.
- No convertir una ausencia de dato en cero.

## Primera tarea de H06

Auditar el esquema y el inventario actual contra el contrato documental del Atlas y producir una matriz de cobertura:

```text
campo / entidad
      ↓
¿existe?
      ↓
¿está normalizado?
      ↓
¿tiene procedencia?
      ↓
¿tiene estado de evidencia?
      ↓
¿puede alimentar JGB/hardware/recomendador?
```

La auditoría será la base para priorizar las siguientes incorporaciones y no se cerrará H06 hasta que las mejoras estén validadas.

## Relación con H10

H10 proporciona la automatización diaria que consume y publica el conocimiento. H06 mejora el conocimiento que esa infraestructura transporta.

```text
H06 Atlas ampliado
        │
        ▼
conocimiento estructurado
        │
        ▼
H10 pipeline diario 🟢
        │
        ├── hardware
        ├── recomendador
        └── publicación
```

## Documentación obligatoria de cierre

Al aceptar H06 deberán existir, como mínimo:

- `README.md`
- `ARCHITECTURE.md`
- `DECISIONS.md`
- `VALIDATION.md`
- diagramas cuando sean útiles
- enlaces desde `docs/phases/README.md`, `atlas/README.md` y el README raíz
- evidencia concreta de la validación final

## Estado

**H06 está activado como siguiente hito.** La primera actividad es la auditoría de cobertura y contrato del Atlas; no se considera todavía aceptado.
