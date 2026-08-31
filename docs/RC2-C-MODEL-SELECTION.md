# RC2-C — Human Model Selection

**Estado:** 🟡 En preparación

## Objetivo

Convertir la salida de la capa de inteligencia hardware en una elección de modelo comprensible, explícita y reproducible por el usuario beta.

RC2-C no crea un algoritmo paralelo de recomendación. Consume candidatos producidos por LLMFit y los presenta mediante el contrato canónico de LEONES.

## Flujo

```text
LLMFit system/recommend
        ↓
normalización LEONES
        ↓
candidatos elegibles
        ↓
presentación explicable
        ↓
usuario elige modelo
        ↓
selección persistida
        ↓
ODS / Magnitude
```

## Datos que debe ver el usuario

Cada candidato debe exponer, cuando estén disponibles:

- nombre e identificador del modelo;
- proveedor/origen;
- caso de uso;
- nivel de ajuste (`perfect`, `good`, `marginal`);
- cuantización óptima propuesta;
- memoria/RAM/VRAM relevante;
- rendimiento **estimado**, claramente etiquetado como estimación;
- contexto considerado;
- runtime compatible cuando esté disponible;
- capacidades relevantes (por ejemplo vision, tool use, audio o TTS);
- base/procedencia de la recomendación;
- advertencias y datos desconocidos.

LLMFit ofrece recomendaciones JSON, filtros por caso de uso y nivel de ajuste, y planificación por modelo/contexto. LEONES debe conservar esa procedencia y no convertir una estimación en medición. citeturn0search0turn0search1

## Reglas de decisión

1. `TooTight` no se presenta como candidato elegible.
2. La estimación de tok/s se muestra como **estimada**, nunca como medida LEONES.
3. Los campos desconocidos permanecen `null`/`unknown`.
4. LEONES no recalcula silenciosamente el score de LLMFit.
5. El usuario puede elegir un candidato distinto del primero recomendado si sigue siendo elegible.
6. La elección debe registrar modelo, variante/cuantización, procedencia y timestamp.
7. La elección no autoriza todavía la ejecución: el gate y el contrato de runtime siguen siendo obligatorios.

## Interfaz mínima

La primera implementación puede ser CLI/local UI. No se exige todavía una GUI completa.

Ejemplo conceptual:

```text
Modelos adecuados para tu equipo

1. Qwen ...
   Ajuste: PERFECT
   Cuantización: Q4_K_M
   Rendimiento estimado: 53 tok/s
   Contexto: 8K
   Caso de uso: general

2. Llama ...
   Ajuste: GOOD
   ...

Elige un modelo [1-2]:
```

Antes de continuar se debe mostrar una confirmación inequívoca:

```text
Has elegido:
  modelo: ...
  variante: ...
  cuantización: ...

¿Continuar? [s/N]
```

## Salida canónica

RC2-C debe producir una selección compatible con el contrato existente de selección/runtime. La selección debe diferenciar:

- `estimated` — procedente del fit/recomendación;
- `measured` — sólo cuando exista evidencia de ejecución real;
- `unknown` — cuando no haya dato.

La selección por sí sola nunca crea evidencia medida.

## No incluido en RC2-C

- instalación del modelo;
- instalación/configuración de ODS o Magnitude;
- ejecución del runtime;
- benchmark A01 u otros benchmarks;
- promoción de estimaciones a mediciones;
- envío automático de resultados a terceros.

Esas responsabilidades pertenecen a las fases siguientes.

## Criterio de aceptación

RC2-C estará cerrado cuando un usuario beta pueda:

1. recibir candidatos derivados de LLMFit;
2. entender por qué cada candidato aparece;
3. distinguir claramente estimación de medición;
4. elegir explícitamente un modelo;
5. persistir una selección reproducible;
6. pasar esa selección al siguiente paso sin ejecutar todavía el modelo.

## Referencias externas

LLMFit documenta `recommend --json`, filtros por caso de uso y ajuste, `system --json` y `plan ... --json` como interfaces para scripts/agentes. citeturn0search0turn0search2
