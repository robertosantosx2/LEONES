# Validación física de benchmarks — protocolo LEONES

## Estado

**🟡 PROTOCOLO LISTO / COBERTURA FÍSICA PENDIENTE**

La infraestructura de medición está terminada, pero una medición simulada o una prueba de integración no constituye evidencia de rendimiento físico. El circuito existente lo establece expresamente. fileciteturn130file0L2-L2

## Objetivo

Obtener datos reales de `tokens_per_second` ejecutando modelos en hardware físico y conservarlos como evidencia reproducible.

El objetivo no es fabricar una tabla completa de una vez. Se comienza por un conjunto pequeño de equipos representativos y se amplía progresivamente.

## Principio fundamental

```text
ESTIMACIÓN ≠ MEDICIÓN REAL ≠ CLASIFICACIÓN
```

El valor observado de `tokens_per_second` es el dato primario. CABE/RULA se calcula después y nunca sustituye la medición.

## Protocolo de una medición

### 1. Identificar el hardware

Registrar como mínimo:

- CPU y modelo exacto;
- RAM instalada y disponible;
- GPU, si existe;
- VRAM, si existe;
- sistema operativo;
- runtime;
- versión del runtime;
- versión del driver cuando sea relevante.

No registrar identificadores personales, MAC/IP, números de serie, rutas privadas ni otra información sensible.

### 2. Identificar el modelo

Registrar:

- `model_id` canónico;
- variante;
- cuantización;
- formato;
- tamaño aproximado;
- fuente del modelo.

### 3. Fijar las condiciones

Registrar:

- contexto;
- número de hilos;
- capas GPU cuando aplique;
- batch;
- temperatura/estado térmico si se dispone de él;
- modo de energía cuando pueda afectar al resultado;
- cualquier parámetro que cambie el rendimiento.

Una comparación solo es válida si las condiciones son suficientemente equivalentes.

### 4. Ejecutar

Usar un adaptador de runtime aprobado. No introducir manualmente un número de tok/s como si fuese una medición.

El runner debe obtener el dato de la salida real del proceso y pasarlo al contrato común. El circuito actual ya está diseñado para ello. fileciteturn130file0L2-L2

### 5. Repetir

Realizar varias ejecuciones bajo las mismas condiciones. Registrar cada ejecución, no solo el promedio.

Como protocolo inicial:

- 3 ejecuciones mínimas;
- descartar únicamente ejecuciones con fallo técnico documentado;
- conservar todos los valores válidos;
- calcular promedio y dispersión como información derivada.

### 6. Clasificar

Aplicar el contrato CABE/RULA únicamente después de obtener `tokens_per_second` real:

```text
<1        → NO_CABE
1–<10     → CABE
10–100    → RULA
>100      → RULA+
```

### 7. Validar

El registro debe superar el validador de benchmarks medidos y contener identidad suficiente de modelo, hardware y runtime. fileciteturn130file0L2-L2

### 8. Publicar

Solo una medición validada puede entrar en la evidencia publicada y posteriormente ser consumida por Atlas/recomendador.

## Primera campaña recomendada

La primera campaña debe priorizar hardware representativo y fácil de reproducir:

| Perfil | CPU | RAM | GPU | Objetivo |
|---|---|---:|---|---|
| A | Intel i5 | 16 GB | ninguna | referencia CPU básica |
| B | Intel i7 | 32 GB | ninguna | referencia CPU media |
| C | Intel i7 | 32 GB | RTX 4060 | portátil GPU consumo |
| D | CPU moderna | 64 GB | ninguna | memoria alta |
| E | CPU moderna | 64 GB+ | NVIDIA | referencia GPU |

Los perfiles son categorías de campaña, no resultados. No se publicará rendimiento hasta ejecutar realmente los equipos.

## Qué modelos medir primero

Prioridad:

1. modelos ya presentes en Atlas y compatibles con el runtime;
2. modelos pequeños que permitan completar rápidamente la campaña;
3. modelos que representen distintas familias y cuantizaciones;
4. modelos relevantes para CABE (1–10 tok/s);
5. modelos relevantes para RULA (10–100 tok/s).

La campaña no debe seleccionar únicamente modelos rápidos: necesitamos cubrir los dos límites de utilidad definidos por LEONES.

## Criterios de calidad

Una medición es apta para evidencia cuando:

- procede de una ejecución real;
- el modelo está identificado inequívocamente;
- el hardware está identificado;
- el runtime está identificado;
- las condiciones son reproducibles;
- el valor de tok/s es obtenido por el runner;
- pasa el validador;
- puede trazarse hasta la ejecución original.

## No hacer

- No copiar resultados de terceros como mediciones propias.
- No convertir estimaciones en `measured`.
- No mezclar runtimes sin registrarlos.
- No comparar cuantizaciones diferentes como si fueran el mismo experimento.
- No eliminar outliers sin documentar la causa técnica.
- No sobrescribir mediciones históricas.
- No publicar una cifra única sin conservar las ejecuciones originales.

## Evidencia externa

Los benchmarks de terceros pueden conservarse como **evidencia externa**, pero no deben presentarse como mediciones físicas de LEONES. Deben mantener fuente, fecha, hardware, runtime y condiciones conocidas.

## Resultado de la campaña

Cada campaña debe producir:

```text
raw executions
      ↓
validated measurements
      ↓
CABE / RULA
      ↓
physical evidence JSONL
      ↓
Atlas
      ↓
hardware matrix
      ↓
recommender
```

## Cierre

Este documento cierra el **protocolo de validación física**, no la cobertura empírica. La fase solo podrá marcarse como empíricamente validada cuando existan ejecuciones reales suficientes y reproducibles.

## Regla de no concurrencia

Todo workflow que publique resultados físicos debe respetar la regla global de no concurrencia de LEONES: un único grupo escritor (`leones-main-writers`) y `cancel-in-progress: false`.
