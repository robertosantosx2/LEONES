# Dubir · Local LLM Hardware Calculator

## Identidad
- **Fuente primaria:** https://dubir.net/tools/local-llm-hardware-calculator/
- **Capa LEONES:** recomendación hardware + workload.
- **Estado:** `research-candidate`.
- **Revisión:** 2026-08-25.

## Qué es
Calculadora que relaciona hardware, modelo, contexto y **caso de uso**. Esto la hace conceptualmente importante para LEONES: un modelo no debe recomendarse únicamente porque quepa en memoria.

## Problema que introduce
El selector necesita dos preguntas:

```text
¿Puede ejecutarse?
        +
¿Es adecuado para mi tarea?
```

La primera es principalmente física/runtime. La segunda incorpora workload, contexto, calidad y latencia objetivo.

## Fuente y evidencia
Sus recomendaciones y cálculos son información externa y deben registrarse con fecha/metodología. No son mediciones LEONES.

## Estimación
La selección de modelo y rendimiento esperado son estimaciones. Deben conservarse como `external_estimate` y no entrar directamente como `measured`.

## Variables útiles para LEONES
La idea de cruzar hardware con workload sugiere que `runtime-selection.v1` debería poder recibir, cuando proceda:

- tarea;
- contexto objetivo;
- latencia máxima;
- throughput mínimo;
- privacidad/offline;
- hardware;
- memoria;
- runtime preferido.

## Relación con LLMFit
LLMFit aporta un score multidimensional de fit, speed, quality y context. Dubir aporta la idea editorial de hacer explícito el **workload**. LEONES debe mantener ambas señales separadas y construir su propia decisión.

## Relación con benchmark
El workload declarado por el usuario debe terminar convertido en un workload ejecutable y versionado. No basta con seleccionar una categoría «coding» o «chat».

```text
user intent
   ↓
workload contract
   ↓
model/runtime candidate
   ↓
executor
   ↓
grader
   ↓
measured outcome
```

## Medición LEONES
Pendiente. La medición debe incluir no solo tok/s, sino resultado funcional del workload y calidad del grader.

## Valor para LEONES
Alto como referencia de **task-aware selection**. Puede ayudar a cerrar el hueco entre un calculador de hardware y el Router.

## Limitaciones
- No sustituye benchmarks propios.
- La selección depende de supuestos externos.
- Un workload genérico no representa necesariamente el caso real del usuario.
- El rendimiento esperado puede variar mucho con runtime y configuración.

## Clasificación
`research-candidate`.

## Próximo paso
Extraer un pequeño vocabulario de workloads y cruzarlo con `runtime-selection.v1`, manteniendo separado el perfil de intención del hardware detectado.