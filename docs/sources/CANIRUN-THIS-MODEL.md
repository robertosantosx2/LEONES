# CanIRunThisModel

## Identidad
- Fuente primaria: https://canirunthismodel.sefarai.com/
- Capa: preselector modelo→hardware.
- Estado LEONES: `research-candidate`.

## Qué es
Herramienta orientada a responder la pregunta inversa de un selector: dado un modelo de Hugging Face, ¿puede ejecutarse en este hardware y con qué método?

## Qué aporta
Organiza la compatibilidad alrededor del modelo concreto y contempla memoria, hardware y métodos/runtimes como Ollama, llama.cpp, vLLM o Transformers.

## Evidencia
La fuente es una calculadora/servicio externo; sus resultados deben considerarse evidencia de su propia metodología, no resultados de LEONES.

## Estimación
Memoria necesaria, compatibilidad, método recomendado y comandos son estimaciones/transformaciones del servicio.

## Medición LEONES
Pendiente. El objetivo es reproducir varios casos y comprobar fit y rendimiento con el executor canónico.

## Valor para LEONES
Complementa a LLMFit: LLMFit ayuda a responder “qué puedo ejecutar”; esta familia de herramientas ayuda a responder “¿puedo ejecutar este modelo?”. Ambas preguntas deben existir en LEONES.

## Próximo paso
Verificar metodología y fórmulas actuales, registrar fuente/release y contrastar una muestra de modelos con LLMFit y CanIRun.ai.