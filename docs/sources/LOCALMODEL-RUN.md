# localmodel.run

## 1. Identidad y procedencia
- **Fuente primaria:** https://github.com/ansumanshah/localmodel.run
- **Web:** https://localmodel.run/
- **Capa LEONES:** compatibility knowledge / preselector.
- **Código:** MIT declarado por el proyecto.
- **Dataset:** CC BY 4.0 declarado por el proyecto.
- **Estado LEONES:** `research-candidate`.
- **Revisión:** 2026-08-25.

## 2. Qué es
localmodel.run responde a una pregunta muy concreta: **«¿puedo ejecutar este modelo en este dispositivo?»**. El usuario selecciona modelo y hardware y recibe un veredicto, memoria calculada, herramienta/runtime sugerido y alternativas. La fuente declara cobertura de macOS, Windows, Linux, iOS y Android. fileciteturn21file0

## 3. Qué lo hace especialmente interesante
Su principio metodológico es que los números no dependen únicamente de una fórmula abstracta. El proyecto declara que obtiene tamaños GGUF medidos y especificaciones de dispositivos con fuente, y que cada número enlaza a su fuente primaria. fileciteturn21file0

Esto encaja directamente con el contrato LEONES:

```text
dato externo trazable
      ↓
estimación reproducible
      ↓
comparación
      ↓
medición LEONES
```

## 4. Dataset
La fuente declara 153 modelos en cuatro modalidades y 40 dispositivos, además de 54 modelos WebGPU/WASM. Para texto indica 125 LLM, y conserva tamaños GGUF medidos. También expone datos mediante JSON y API y mantiene una copia en Hugging Face. fileciteturn21file0

Las cifras de catálogo son **estado de la fuente revisada**, no una afirmación permanente de LEONES.

## 5. Modelo de memoria
Para LLM de texto la fuente describe:

```text
weights at selected quant
+ KV cache
+ runtime overhead
```

Además declara soporte de lógica MoE y tratamiento de memoria unificada de Apple. fileciteturn21file0

Esto lo convierte en un excelente punto de comparación con VRAMBudget y LLMFit.

## 6. Evidencia
Hay varias evidencias de interés:

- catálogo separado del contenido web;
- cada fila lleva `sources[]`;
- tamaños de archivo GGUF medidos desde árboles de Hugging Face/Ollama;
- especificaciones de dispositivos con fuentes;
- gate CI que valida filas y exige source URL para anchors de VRAM no textuales;
- actualización semanal para detectar drift. fileciteturn21file0

La trazabilidad de datos es posiblemente su mayor aportación a LEONES.

## 7. Estimación
El veredicto `can run` y la memoria calculada son **estimaciones de compatibilidad**, aunque utilicen datos medidos como entradas.

LEONES debe distinguir:

```text
source measured size
≠
LEONES measured inference
```

Un tamaño GGUF medido no es un benchmark de velocidad.

## 8. Modalidades
La arquitectura no se limita a texto. El proyecto cubre también imagen, vídeo y audio y usa modelos de memoria específicos para cada modalidad, con anchors de peak VRAM/memory y gates de runtime. fileciteturn21file0

Esto abre una posible segunda fase de conocimiento LEONES: aplicar el mismo contrato de cuatro capas a modelos multimodales sin asumir que la fórmula de un LLM textual sirve para todo.

## 9. Runtime gate
Una idea especialmente útil es no emitir un verdict de compatibilidad solo porque la memoria parezca suficiente. La fuente incorpora un **runtime gate**: si no existe runtime local razonable para una combinación plataforma/modelo, no la presenta como ejecutable. fileciteturn21file0

LEONES debería adoptar el mismo principio, pero con `runtime-selection.v1` como autoridad.

## 10. Relación con LLMFit

```text
localmodel.run
modelo + dispositivo → ¿puede correr?

LLMFit
hardware + intención → ¿qué merece la pena probar?

LEONES
hardware + intención + evidencia + runtime + medición → recomendación
```

Son complementarios, no competidores directos.

## 11. Relación con CanIRun.ai
CanIRun.ai enfatiza detección inmediata desde navegador y personalización del hardware. localmodel.run enfatiza un **dataset abierto y trazable** de modelo × dispositivo. LEONES puede combinar ambas ideas sin mezclar sus resultados.

## 12. Medición LEONES
**Pendiente.**

La primera batería debe elegir pares del dataset y comprobar:

1. verdict de memoria;
2. runtime gate;
3. instalación real;
4. ejecución;
5. TTFT;
6. TPOT/tok/s;
7. RAM/VRAM;
8. estabilidad;
9. resultado funcional.

## 13. Valor para LEONES
Muy alto para la capa de **evidencia trazable** y para validar la matemática de fit.

Una integración futura puede importar solo registros cuya procedencia se conserve:

```text
localmodel.run dataset
        ↓
source/evidence validation
        ↓
LEONES candidate
        ↓
runtime-selection.v1
        ↓
executor
        ↓
benchmark
```

## 14. Limitaciones
- Compatibilidad matemática no equivale a rendimiento.
- Los datos pueden cambiar.
- Un tamaño de archivo no captura necesariamente memoria efectiva del runtime.
- El verdict depende de plataforma, modalidad y runtime.
- La cobertura declarada debe actualizarse periódicamente.

## 15. Licencia y reutilización
El proyecto declara MIT para código y CC BY 4.0 para dataset. Antes de importar datos a Atlas, LEONES debe conservar atribución y procedencia y comprobar que cada dato importado mantiene su `sources[]`. fileciteturn21file0

## 16. Clasificación
**`research-candidate` → candidato a fuente de compatibilidad trazable.**

## 17. Próximo paso
Crear un importador **solo de conocimiento**, no de mediciones: `model_id`, `device_id`, `memory_estimate`, `runtime_gate`, `sources[]`, licencia y timestamp. Después contrastar una muestra con LLMFit, VRAMBudget y ejecución real.