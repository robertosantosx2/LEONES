# Axolotl — proveedor del servicio Post-Training de ODS

## Resumen ejecutivo

[Axolotl](https://github.com/axolotl-ai-cloud/axolotl) es un framework open source para post-entrenamiento y fine-tuning de modelos modernos de lenguaje y multimodales. Su flujo basado en configuración, soporte Docker, amplitud de métodos de entrenamiento, ejecución distribuida y orientación a entornos cloud lo convierten en un candidato fuerte para integrarlo con ODS.

La arquitectura recomendada no es convertir Axolotl en una dependencia central de ODS. ODS debería exponer un Post-Training Service estable y registrar Axolotl como proveedor intercambiable junto a LLaMA-Factory y futuros backends.

LEONES → ODS Post-Training Service → proveedor Axolotl → training job → artefacto → validación/conversión → ODS Model Registry → ODS Runtime → benchmark → evidencia → LEONES.

## Encaje con ODS

La documentación actual de Axolotl describe soporte para supervised fine-tuning y pretraining; full fine-tuning, LoRA y QLoRA; métodos de preferencia como DPO, IPO, KTO y ORPO; RL como GRPO/GDPO; reward-model workflows; modelos multimodales de lenguaje/visión y determinados modelos de audio; cuantización y quantization-aware training; entrenamiento distribuido con FSDP2, DeepSpeed, Torchrun y Ray; datasets locales y remotos; Docker; inferencia y merge de LoRA.

Consultar la [documentación oficial de Axolotl](https://docs.axolotl.ai/) para la matriz de capacidades vigente.

## Contrato propuesto para ODS

ODS debería exponer una API independiente del proveedor. El YAML de Axolotl debe seguir siendo un detalle de implementación y un artefacto de procedencia, no la API pública de ODS.

El contrato conceptual debe cubrir creación, consulta, cancelación, logs, artefactos y benchmark de jobs de post-training.

El registro de capacidades puede anunciar SFT, LoRA, QLoRA, full fine-tuning, DPO/IPO/KTO/ORPO, GRPO, reward modelling, multimodal, cuantización y ejecución distribuida.

ODS seleccionaría el proveedor según los requisitos del workload y la evidencia medida, en lugar de codificar un framework concreto.

## Ciclo de vida del job

CREATE → PREPARE → RUN → VALIDATE → EXPORT → CONVERT (si es necesario) → REGISTER → BENCHMARK → DEPLOY.

Axolotl se ocupa de la fase de entrenamiento. ODS debería controlar planificación, credenciales, aislamiento, artefactos, procedencia, validación, registry e integración de despliegue.

## Integración mediante contenedores

Axolotl publica imágenes Docker oficiales y documenta ejecución con GPU mediante contenedores. Esto encaja directamente con un provider de jobs de ODS.

El provider debe lanzar Axolotl por job con mounts explícitos de datasets/modelos/cache, secrets con alcance limitado, límites de recursos y directorio explícito de artefactos. Axolotl no necesita convertirse en un daemon permanente de ODS.

## Artefactos y runtime de ODS

Los adapters deben ser artefactos de primera clase.

Flujo representativo:

modelo base + dataset → Axolotl → LoRA/QLoRA adapter → validación → merge opcional → conversión de formato → ODS Model Registry → ODS inference runtime.

La compatibilidad entre un resultado de entrenamiento y un runtime de inferencia de ODS debe validarse explícitamente. Un checkpoint Hugging Face/Transformers no debe considerarse automáticamente compatible con todos los backends de ODS.

Cuando un runtime necesite GGUF u otra representación, la conversión debe ser una etapa explícita y registrar herramienta, versión, configuración y resultado.

## Datasets

ODS debería mediar el acceso a datasets en lugar de permitir que cada provider defina el modelo de datos de la plataforma.

El contrato debería incluir identificador/versión, referencia reproducible, formato/schema, política de acceso, credenciales cuando sean necesarias, preprocessing y procedencia.

Los traces de producción no deberían convertirse automáticamente en datos de entrenamiento. Ese flujo debe pasar por política explícita, consentimiento, filtrado/redacción y procedencia.

## Computación híbrida

Axolotl soporta ejecución local y orientada a cloud, pero disponer de ejecución cloud no constituye por sí mismo evidencia de independencia.

ODS debería separar Training Provider de Compute Provider.

Training Provider: Axolotl.

Compute Provider: máquina local, VM remota, Kubernetes, GPU cloud u otro sustrato de ejecución.

Así LEONES puede elegir el framework de entrenamiento independientemente del lugar donde se ejecute el workload.

## Relación con TangleML

TangleML y Axolotl resuelven capas distintas:

TangleML = orquestación de workflows.
Axolotl = ejecución de training/post-training.
ODS = registry, deployment, inference y operaciones.

TangleML puede orquestar pipelines de varias etapas mientras Axolotl ejecuta la fase de entrenamiento. ODS mantiene el límite operativo estable.

## Ruta avanzada

Ruta propuesta:

1. PoC SFT + LoRA.
2. QLoRA.
3. Validación y merge de adapters.
4. Exportación/conversión al formato de inferencia soportado por ODS.
5. DPO y otros métodos de preferencia.
6. Post-training multimodal.
7. GRPO/RL.
8. Integración con sistemas de serving usados durante RL, incluidos los flujos documentados de sincronización de LoRA con vLLM cuando corresponda.

Cada etapa debe generar evidencia independiente; la documentación del framework no debe registrarse como medición de LEONES.

## Seguridad y aislamiento

El provider ODS debería imponer ejecución aislada, mounts explícitos, credenciales con alcance limitado, acceso de red controlado, límites de recursos, exportación explícita de artefactos, procedencia de configuración/versiones y política de borrado/retención.

El provider de entrenamiento no debería obtener acceso silencioso a datos o credenciales ajenos al job.

## Modelo de evidencia

LEONES debe distinguir estimated, reported, observed y measured.

Para Axolotl:
- reported = capacidad declarada por la documentación;
- observed = comportamiento observado durante una integración ODS;
- measured = resultado de benchmark independiente;
- estimated = predicción del planner antes de ejecutar.

Los benchmarks o ejemplos publicados por Axolotl no deben registrarse como mediciones LEONES salvo que se reproduzcan.

## Licencia e independencia

El repositorio de Axolotl declara licencia Apache-2.0. Esto permite evaluarlo como proveedor externo, pero su licencia no determina los términos de modelos base, datasets, datos de entrenamiento, checkpoints, proveedores cloud, registros de contenedores o servicios externos.

LEONES debe registrar estos elementos por separado.

## Prueba de concepto recomendada

ODS API → Axolotl provider → contenedor aislado → SFT + LoRA → adapter artifact → validación → merge opcional → conversión si es necesaria → ODS Model Registry → ODS runtime → benchmark → evidence.

Criterios de éxito: creación reproducible del job, aislamiento del provider, descubrimiento de artefactos, captura de procedencia, registro correcto, inferencia validada, benchmark independiente y cancelación/fallos limpios.

## Evaluación

Axolotl es un candidato de primera línea para la capa de proveedores del Post-Training Service de ODS.

Sus propiedades más relevantes para ODS son el modelo de jobs compatible con contenedores, la reproducibilidad basada en configuración, la amplitud del post-training, el soporte multimodal y las opciones de ejecución distribuida/cloud.

Debe mantenerse como provider intercambiable y no convertirse en dependencia central de ODS. LLaMA-Factory y Axolotl deberían evaluarse mediante el mismo contrato ODS y seleccionarse según capacidades del workload y evidencia.

## Referencias oficiales

- [Documentación Axolotl](https://docs.axolotl.ai/)
- [Repositorio GitHub](https://github.com/axolotl-ai-cloud/axolotl)
- [Instalación](https://docs.axolotl.ai/docs/installation.html)
- [Docker](https://docs.axolotl.ai/docs/docker.html)
- [Quickstart](https://docs.axolotl.ai/docs/getting-started.html)
- [Formatos de datasets](https://docs.axolotl.ai/docs/dataset-formats/index.html)
- [CLI y configuración cloud](https://docs.axolotl.ai/docs/cli.html)
- [Documentación RLHF](https://github.com/axolotl-ai-cloud/axolotl/blob/main/docs/rlhf.qmd)
