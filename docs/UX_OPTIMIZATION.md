# LOAS — Optimización de UX mediante la pila

## 1. Principio

LOAS no debe limitarse a decir al usuario **«tu máquina obtiene X tok/s»**. Debe decirle:

> **«Con tu hardware, modelo y tareas, estas son las piezas de la pila que puedes cambiar para mejorar tu experiencia de uso, en qué orden, cuánto esperamos ganar y qué coste introduce cada cambio».**

La UX de LOAS es el resultado de toda la cadena:

```text
Hardware
   ↓
Sistema operativo
   ↓
Runtime / backend de inferencia
   ↓
Modelo + cuantización
   ↓
Servidor/API
   ↓
Agente
   ↓
Herramientas
   ↓
Contexto / memoria
   ↓
Tareas
   ↓
UX real
```

Por tanto, optimizar UX no significa necesariamente cambiar de modelo.

## 2. Recomendaciones basadas en evidencia

LOAS debe recomendar cambios **después de medir**, no por preferencias generales.

Cada recomendación debe contener:

- problema observado;
- pieza que se recomienda cambiar;
- alternativa propuesta;
- motivo técnico;
- mejora esperada;
- coste o inconveniente;
- nivel de confianza;
- prueba necesaria para confirmar la mejora.

Ejemplo:

```text
Problema: generación < 10 tok/s
Cambio: Q4_K_M → cuantización menor
Resultado esperado: mayor velocidad / menor memoria
Coste: posible pérdida de calidad
Confianza: experimental
Acción: repetir LOTB-0
```

## 3. Orden de intervención

LOAS debe intentar mejorar la UX con el **cambio menos invasivo que resuelva el problema**.

Orden inicial recomendado:

### Nivel 0 — Configuración

Antes de cambiar componentes:

- contexto;
- batch;
- threads;
- offloading;
- parámetros de servidor;
- concurrencia;
- warm-up;
- prompts y herramientas.

### Nivel 1 — Cuantización

Si el modelo cabe pero es demasiado lento o consume demasiada memoria:

- Q8 → Q6/Q5/Q4;
- comparar calidad frente a velocidad;
- mantener el mismo modelo para aislar la variable.

### Nivel 2 — Modelo

Si la cuantización no resuelve el problema:

- cambiar a un modelo menor;
- probar una familia optimizada para coding/reasoning/tool use;
- mantener el mismo backend cuando sea posible.

### Nivel 3 — Backend/runtime

Si el modelo es adecuado pero la inferencia no lo es:

- comparar llama.cpp con otros runtimes compatibles;
- probar CPU/GPU/offloading;
- evaluar AirLLM, WASTE, KTransformers y otras soluciones cuando sean CABE para el hardware.

### Nivel 4 — Agente

Si la inferencia es suficientemente rápida pero la UX agentic es mala:

- cambiar agente;
- cambiar estrategia de tool calling;
- cambiar memoria/context management;
- revisar Hermes/LangGraph/Buddy;
- reducir pasos innecesarios.

### Nivel 5 — Sistema operativo

Solo después de medir el resto:

- Debian;
- Ubuntu;
- RHEL/Fedora;
- drivers y toolchain.

El cambio de distribución debe recomendarse únicamente cuando existan pruebas que indiquen una ventaja para ese hardware/backend.

### Nivel 6 — Hardware

Si ningún cambio de software alcanza el objetivo:

- aumentar RAM;
- incorporar GPU;
- aumentar VRAM;
- cambiar CPU;
- mejorar almacenamiento cuando sea un cuello de botella.

El objetivo es que LOAS **no recomiende comprar hardware antes de demostrar que un cambio de software no basta**.

## 4. Qué significa «mejor UX»

LOAS debe considerar como mínimo:

| Dimensión | Medida |
|---|---|
| Velocidad | generation tok/s |
| Respuesta inicial | time-to-first-token / carga |
| Memoria | peak RAM/VRAM |
| Fiabilidad | porcentaje de tareas completadas |
| Agentic | B01-B05 |
| Tool use | tool calls y errores |
| Latencia | tiempo total de tarea |
| Calidad | éxito y calidad de salida |
| Recursos | CPU/GPU/RAM |
| Complejidad | número de cambios necesarios |

Una configuración con más tok/s pero que falla B03 o B04 no debe considerarse automáticamente mejor.

## 5. Motor de recomendaciones

La arquitectura futura debe producir una lista ordenada:

```text
LOAS diagnóstico
        ↓
Identificación del cuello de botella
        ↓
Candidatos CABE
        ↓
Comparación de alternativas
        ↓
Estimación de impacto
        ↓
Recomendación
        ↓
RULA de la alternativa
        ↓
Comparación antes/después
```

### Ejemplo conceptual

```text
MÁQUINA: H1 / 16 GB / i5 / CPU
MODELO: Qwen3-8B Q4_K_M

Diagnóstico:
  inferencia = 7.8 tok/s
  B01 = OK
  B02 = OK
  B03 = lento
  B04 = OK
  B05 = OK

LOAS recomienda:

1. Cambiar cuantización → Q4_K_M → Q3/Q4 alternativa
   Motivo: memoria/CPU
   CABE: sí
   Impacto esperado: alto
   Riesgo: calidad

2. Probar backend alternativo
   Motivo: cuello de botella de inferencia
   CABE: por verificar
   Impacto: medio/alto

3. Cambiar agente
   Motivo: B03 requiere demasiados pasos
   CABE: sí
   Impacto: medio

4. Comprar GPU
   Motivo: último recurso
   Coste: alto
```

## 6. «CABE» como filtro

Una alternativa solo puede recomendarse si **cabe** en el hardware objetivo y en las restricciones del proyecto.

CABE debe considerar:

- RAM;
- VRAM;
- almacenamiento;
- CPU;
- GPU;
- sistema operativo;
- compatibilidad del backend;
- licencia;
- posibilidad real de instalación.

Una solución excelente en un servidor de 256 GB no es una recomendación válida para un usuario H1 de 16 GB.

## 7. «RULA» como verificación

Toda recomendación que implique cambiar una pieza de la pila debe poder **rular** una prueba comparable.

Por ejemplo:

```text
ANTES
Qwen3-8B Q4_K_M + llama.cpp + Buddy

CAMBIO
Qwen3-8B Q5_K_M + llama.cpp + Buddy

RULA
LOTB-0 + B01-B05

DESPUÉS
comparar UX
```

No se debe declarar una mejora simplemente porque un benchmark sintético haya aumentado.

## 8. Libertad como restricción

El recomendador debe respetar la filosofía Libre-Open de LOAS.

Cuando existan varias alternativas técnicamente equivalentes:

1. Libre/Open;
2. Copyleft;
3. reproducible/auditable;
4. compatible con hardware de consumo;
5. rendimiento;
6. facilidad de uso.

Una solución privativa puede aparecer como referencia comparativa si es necesaria para entender el estado del arte, pero **no debe convertirse automáticamente en recomendación de la pila LOAS**.

## 9. Resultado final para el usuario

La salida ideal de LOAS no será una tabla de benchmarks sino algo parecido a:

```text
DIAGNÓSTICO LOAS

Tu configuración: H1 / 16 GB / i7 / CPU

Estado: RULA, pero UX limitada

Cuello de botella principal:
  inferencia del modelo

MEJORAS RECOMENDADAS

1. ██████████  Cambiar backend
   Impacto: alto
   Coste: bajo
   CABE: sí
   Riesgo: bajo

2. ████████    Cambiar cuantización
   Impacto: alto
   Coste: bajo
   CABE: sí
   Riesgo: medio

3. █████       Cambiar modelo
   Impacto: medio
   Coste: medio
   CABE: sí
   Riesgo: medio

4. ███         Cambiar agente
   Impacto: medio
   Coste: medio
   CABE: sí
   Riesgo: bajo

5. ██          Cambiar hardware
   Impacto: alto
   Coste: alto
   CABE: requiere inversión

PRÓXIMA PRUEBA:
  ejecutar alternativa #1 y comparar LOTB
```

## 10. Evolución futura

El sistema de recomendaciones deberá aprender de metaLOAS. Cuantos más resultados anónimos y reproducibles haya, mejor podrá estimar:

- qué modelo CABE en cada perfil;
- qué backend funciona mejor;
- qué cuantización ofrece mejor equilibrio;
- qué agente completa mejor cada tipo de tarea;
- qué cambios producen mejoras reales de UX;
- cuándo merece la pena cambiar de sistema operativo;
- cuándo el software ya no puede compensar la limitación del hardware.

El objetivo final es convertir LOAS en un **asesor de configuración agentic local**, no solamente en un benchmark.
