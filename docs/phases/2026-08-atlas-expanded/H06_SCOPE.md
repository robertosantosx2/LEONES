# H06.1 — Auditoría del alcance del Atlas

**Estado: 🟡 En ejecución**

Este documento convierte H06 en una lista verificable de trabajo. No declara todavía la fase terminada.

## 1. Qué existe ya

El Atlas dispone de un esquema JSON v0.2 con entidades para modelos, familias, organizaciones, runtimes, backends, cuantizaciones, herramientas, benchmarks, hardware, conocimiento y experimentos. El contrato exige como mínimo `id`, `kind`, `name` y `evidence`. También contempla calidad, ciclo de vida, evidencia externa, hardware, sistema de modelo y campos de recomendación.

Referencia: [`atlas/schema.json`](../../../atlas/schema.json).

## 2. Qué debe comprobar H06

### Identidad

- Un identificador estable por entidad.
- Organización, familia, modelo y variante diferenciados.
- Cuantización y artefacto diferenciados del modelo base.
- No confundir nombre comercial, repositorio, checkpoint y variante.
- Detectar colisiones y duplicados.

### Cobertura

Comprobar presencia y coherencia de:

- modelos;
- familias;
- organizaciones;
- runtimes;
- backends;
- cuantizaciones;
- benchmarks;
- hardware;
- experimentos;
- fuentes de evidencia.

### Procedencia

Para cada afirmación relevante, comprobar que sea posible saber:

- de qué fuente procede;
- cuándo fue recuperada;
- qué afirmación respalda;
- qué tipo de evidencia representa;
- si es reproducible o verificada.

### Calidad

Buscar y clasificar:

- campos obligatorios ausentes;
- valores inválidos;
- unidades incompatibles;
- duplicados;
- colisiones de identidad;
- contradicciones;
- fuentes ausentes;
- claims sin soporte;
- información obsoleta.

El esquema ya proporciona `quality_flags` para representar estas incidencias.

## 3. Límites que no se deben romper

H06 mantiene separadas estas dimensiones:

```text
APERTURA / JGB
       ≠
CAPACIDAD / BENCHMARK
       ≠
TOKENS POR SEGUNDO
       ≠
CABE
       ≠
RULA
       ≠
PRECIO
       ≠
INCERTIDUMBRE
```

Tampoco se debe transformar una fuente externa en una medición LEONES por el mero hecho de estar publicada.

## 4. Hardware

El registro de hardware debe poder representar CPU/GPU, memoria, almacenamiento, bandwidth, compute e interconexiones. Cuando exista una cifra de rendimiento, debe quedar claro si es medida o estimada y bajo qué condiciones.

## 5. Evidencia

Los estados oficiales son:

- `reported` — información comunicada pero todavía no suficientemente comprobada;
- `reproducible` — existe información suficiente para reproducir la afirmación;
- `verified` — comprobación independiente satisfactoria;
- `rejected` — no debe entrar en agregados oficiales.

## 6. Resultado esperado de H06.1

Al finalizar la auditoría debe existir un informe que responda, con cifras y listas concretas:

1. ¿Cuántos registros hay por tipo?
2. ¿Cuántos tienen identidad completa?
3. ¿Cuántos tienen evidencia suficiente?
4. ¿Cuántos tienen fuentes?
5. ¿Cuántos tienen flags de calidad?
6. ¿Cuántos duplicados o colisiones existen?
7. ¿Qué campos son sistemáticamente deficitarios?
8. ¿Qué partes del esquema están realmente utilizadas?
9. ¿Qué datos son adecuados para alimentar el recomendador?
10. ¿Qué trabajo queda antes de declarar H06 aceptada?

## 7. Regla de transparencia

Si una comprobación todavía no se ha ejecutado, se escribirá **pendiente de medir/comprobar**, no un cero inventado.

Si no existe información, se conservará `unknown` cuando corresponda.

La auditoría debe producir conocimiento sobre el estado real del Atlas, no maquillar sus carencias.
