# RC1 — ODS, Magnitude y LLMFit: frontera de responsabilidades

> Documento de decisión para evitar duplicación funcional.

## 1. Hallazgo operativo

La investigación de RC1 confirma que LEONES no debe implementar por su cuenta tres capacidades que ya están cubiertas aguas abajo:

- **LLMFit** detecta hardware y hace análisis de fit/modelo, incluyendo recomendaciones JSON y planificación.
- **ODS** ya integra detección de hardware/selección de modelo, `llama-server` como backend de inferencia y Hermes como agente por defecto.
- **Magnitude** combina agente, perfilado de hardware, recomendación/descarga de modelos e inferencia local.

Fuentes revisadas:

- LLMFit: documentación oficial de CLI y funcionamiento.
- ODS: README y documentación de Hermes.
- Magnitude: web oficial y documentación pública enlazada desde ella.

## 2. Consecuencia para LEONES

La frontera RC1 queda así:

```text
LLMFit
  "qué encaja aproximadamente"
          ↓
LEONES
  "qué merece probarse y cómo conservar la evidencia"
          ↓
ODS / Magnitude
  "cómo resolver la tarea con su stack propio"
          ↓
runtime real
          ↓
LEONES
  "qué ocurrió realmente"
```

LEONES no debe convertirse en una copia reducida de LLMFit, ODS o Magnitude.

## 3. LLMFit

LLMFit se utiliza como **primera capa de fit**.

Su documentación actual describe detección de RAM/CPU/GPU, backend, modelos, cuantización, fit, estimación de velocidad, contexto y recomendaciones JSON. También dispone de `doctor` para diagnóstico de hardware. Esto hace innecesario que LEONES implemente otro sistema general de fit.

La pieza propia `hardware_profile.py` conserva una responsabilidad distinta: producir una observación local mínima y trazable para evidencia y para alimentar integraciones. No decide fit y no hace benchmark.

## 4. ODS

ODS es el candidato natural para el escenario SOHO.

La documentación pública actual de ODS describe:

- `llama-server` como motor de inferencia;
- Open WebUI y dashboard;
- detección de hardware y selección de modelo;
- Hermes Agent como agente local-first por defecto;
- LiteLLM y otras extensiones;
- instalación y configuración del stack.

Hermes no se incorpora como componente de LEONES. Si ODS es la ruta elegida, Hermes forma parte de la trayectoria que LEONES debe medir como sistema externo integrado.

## 5. Magnitude

Magnitude es el candidato natural para el escenario de asistente personal.

La documentación pública actual describe una solución local/offline que:

- perfila el hardware;
- recomienda modelos;
- descarga modelos;
- ejecuta los modelos localmente;
- integra la experiencia de agente y skills;
- permite modelos GGUF externos y endpoints OpenAI-compatible.

Por tanto, LEONES no debe reconstruir el perfilado, recomendación, descarga ni motor del asistente de Magnitude.

## 6. ODS vs Magnitude

No se pretende una única implementación para ambos.

| Escenario RC1 | Sistema preferente |
|---|---|
| SOHO / servidor doméstico | ODS |
| asistente personal local | Magnitude |
| escenario diferente | evaluar evidencia antes de ampliar |

La selección final depende de la tarea concreta y de la compatibilidad real en el hardware probado.

## 7. Hermes

Hermes pertenece a ODS cuando ODS lo habilita. La documentación de ODS indica que Hermes usa un proveedor OpenAI-compatible apuntando al `llama-server` del stack y que ODS empaqueta el agente upstream en vez de mantener un fork propio.

Esto refuerza la regla LEONES:

> **No meter Hermes dentro de LEONES; medir la trayectoria ODS que ya lo contiene.**

## 8. AirLLM y FreeToken

Se mantienen como fuentes técnicas y posibles mejoras upstream.

No se convierten en adapters LEONES por defecto.

```text
AirLLM / FreeToken
       ↓
comprobar utilidad
       ↓
¿mejora ODS/Magnitude?
       ↓ sí
proponer upstream
       ↓ no viable
conector mínimo
```

## 9. Qué medirá LEONES

La medición debe producir dos familias de resultados:

### Runtime

- tokens/s cuando el runtime lo exponga de forma comparable;
- latencia;
- contexto/configuración;
- memoria y hardware observado;
- estabilidad/repetibilidad.

### Tarea/agente

- éxito de la tarea;
- tiempo total;
- llamadas a herramientas;
- errores;
- recuperaciones;
- artefactos;
- criterios específicos de la tarea.

No se debe mezclar automáticamente el rendimiento del runtime con el éxito de la trayectoria agentiva.

## 10. Próxima prueba física

La primera prueba real debe determinar cuál de las dos rutas puede convertirse en la demostración RC1:

1. perfilar hardware;
2. obtener fit inicial de LLMFit;
3. seleccionar escenario ODS/Magnitude;
4. instalar solamente lo imprescindible;
5. identificar el runtime real usado por el sistema;
6. cargar un modelo pequeño y conocido;
7. ejecutar una tarea mínima;
8. medir;
9. conservar evidencia;
10. decidir la ruta RC1.

No se ejecutará una batería de modelos antes de comprobar que la ruta completa funciona.

## 11. Estado

**Pre-Ubuntu: investigación y frontera cerradas; instalación y comportamiento real pendientes.**

El siguiente gate requiere la máquina física.
