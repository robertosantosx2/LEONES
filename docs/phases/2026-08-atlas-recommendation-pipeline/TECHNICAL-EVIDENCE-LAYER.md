# H10 — Capa de evidencia técnica de modelos

**Estado: 🟡 En desarrollo**

## 1. Motivo

El Run #8 demostró que el pipeline extremo a extremo puede ejecutarse correctamente y fallar de forma explícita cuando la matriz hardware queda vacía. El problema no estaba en la publicación ni en la matriz, sino aguas arriba: los descubrimientos ingeridos no aportaban todavía suficiente evidencia técnica para construir perfiles de ejecución y recomendaciones.

La capa de evidencia técnica se incorpora por tanto entre la identidad del modelo y la generación de candidatos hardware.

## 2. Flujo objetivo

```text
DESCUBRIMIENTO
     ↓
IDENTIDAD / REPOSITORIO
     ↓
EVIDENCIA TÉCNICA
     ↓
VERIFICACIÓN
     ↓
PERFIL DEL MODELO
     ↓
CABE
     ↓
MATRIZ HARDWARE
     ↓
RECOMENDACIÓN
```

## 3. Principio fundamental

La capa **no debe inventar datos** para hacer crecer el número de recomendaciones.

Si un dato no tiene evidencia suficiente, debe conservarse como desconocido y su estado debe indicar la situación.

```text
valor conocido + evidencia → usable
valor conocido + evidencia débil → usable con incertidumbre
valor desconocido → unknown
valor inferido → estimated, nunca silencioso
```

## 4. Datos que debe intentar obtener

### Identidad

- nombre del modelo;
- organización;
- repositorio canónico;
- familia;
- variantes;
- licencia/apertura cuando exista evidencia.

### Arquitectura y tamaño

- parámetros totales;
- parámetros activos, si aplica;
- arquitectura;
- número de capas cuando exista;
- dimensiones relevantes cuando estén publicadas.

### Ejecución

- runtime compatible;
- versión del runtime cuando exista;
- backend;
- formato;
- cuantización;
- contexto máximo.

### Memoria

- memoria de pesos;
- KV cache cuando pueda calcularse a partir de datos técnicos suficientes;
- overhead de runtime cuando exista una base explícita;
- memoria total estimada;
- margen de memoria.

### Rendimiento

- tokens/s;
- latencia;
- throughput;
- benchmark;
- hardware utilizado;
- runtime utilizado.

El rendimiento externo no se convierte automáticamente en medición LEONES.

## 5. Estados de evidencia

Los estados deben distinguir descubrimiento de conocimiento técnico:

```text
unknown
   ↓
discovered
   ↓
reported
   ↓
estimated
   ↓
reproducible
   ↓
verified
```

No son una escala obligatoria ni lineal para todos los campos. Un campo puede permanecer en `unknown` aunque otros campos del mismo modelo estén `verified`.

## 6. Reglas

### R1 — No rellenar por defecto

La ausencia de información no se sustituye por un valor conveniente.

### R2 — Procedencia por campo

Cuando sea posible, conservar fuente y fecha de comprobación asociadas al dato.

### R3 — Rendimiento reproducible

Un valor de tokens/s necesita contexto de hardware, runtime y configuración para poder interpretarse.

### R4 — Memoria estimada explícita

Una estimación puede utilizarse para planificación si su método está documentado y el campo queda marcado como `estimated`.

### R5 — CABE independiente

CABE no se deduce simplemente de `fit_score`. Necesita evidencia suficiente para la configuración hardware considerada.

### R6 — JGB independiente

La clasificación de apertura/libertad no se deriva del rendimiento ni de la viabilidad hardware.

## 7. Relación con la matriz

La matriz hardware no debe ser una tabla de combinaciones sintácticas. Una fila debe representar una configuración para la que exista información suficiente para responder, al menos, a la pregunta de viabilidad.

```text
modelo
 + perfil hardware
 + memoria/contexto suficientes
 + ruta de ejecución conocida
          ↓
       candidato
```

Si no se puede justificar esa relación, no se fabrica una recomendación.

## 8. Criterio de salida

La capa se considera funcional cuando puede transformar una parte significativa del feed de descubrimientos en perfiles técnicos trazables y el pipeline puede explicar por qué cada modelo llega o no llega a la matriz.

No se exige que todos los modelos sean recomendables.

Sí se exige que un resultado vacío sea explicable mediante estados de evidencia y métricas de descarte.

## 9. Próxima implementación

1. identificar las fuentes técnicas ya disponibles en el repositorio;
2. mapearlas a los campos Atlas;
3. crear el extractor/enriquecedor de evidencia;
4. registrar procedencia y estado;
5. generar perfiles técnicos;
6. conectar perfiles con CABE;
7. volver a ejecutar la matriz;
8. documentar resultados y descartes.

## 10. Criterio de cierre de H10

H10 no se acepta porque haya filas en la matriz. Se acepta cuando el flujo completo sea reproducible, trazable y explique tanto las recomendaciones como los descartes.
