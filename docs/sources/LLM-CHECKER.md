# LLM Checker

## Identidad
- Fuente primaria: https://github.com/signerless/llm-checker
- Capa: preselector + scoring + runtime targeting.
- Estado LEONES: `research-candidate`.

## Qué es
CLI que detecta hardware, analiza modelos locales y produce recomendaciones mediante un núcleo de scoring con Quality, Speed, Fit y Context. Integra catálogos de Ollama, Hugging Face y GPT4All y puede orientar el runtime.

## Evidencia
La documentación actual describe detección multiplataforma, estimación de memoria calibrada con tamaños reales de Ollama, catálogo multi-fuente y métricas de tokens/s durante ejecuciones. Sus releases recientes también documentan correcciones específicas para MoE, multi-GPU y scoring canónico.

## Estimación
El scoring, compatibilidad, memoria prevista y recomendaciones son estimaciones/decisiones del propio LLM Checker. Deben almacenarse como evidencia externa o estimate, nunca como medición LEONES.

## Medición LEONES
Pendiente. Su `ai-run` puede ser interesante como fuente de contraste, pero LEONES debe ejecutar su propio protocolo y conservar runtime/configuración/workload.

## Valor para LEONES
Muy alto: su separación entre detección, catálogo, scoring y ejecución ofrece material para comparar con `runtime-selection.v1`. También es relevante su experiencia con errores de sizing de MoE y GPU.

## Integración propuesta
`catalogue → hardware facts → external score → candidate → runtime-selection.v1 → executor → grader → benchmark`.

## Limitaciones
La licencia NPDL-1.0 y las condiciones de redistribución deben verificarse antes de reutilizar código/datos. El catálogo y scoring cambian con releases.

## Próximo paso
Analizar `scoring-core`, detector, registry y calibration fixtures; identificar qué conceptos pueden incorporarse como evidencia metodológica sin copiar el scoring externo.