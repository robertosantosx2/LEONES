# LEONES — LLM Smoke Test

**Estado: experimental.**

Pequeña herramienta local para comprobar que un runtime de LLM puede ejecutarse en el equipo del usuario y producir un resultado medible.

No necesitas instalar LEONES, Atlas ni su infraestructura para utilizar este paquete.

## 1. Qué hace

El paquete proporciona un núcleo común y adaptadores opcionales para runtimes locales.

```text
usuario
   │
   ├── modelo local
   │
   └── runtime local
          │
          ▼
   llm-smoke-test
          │
          ▼
   resultado JSON
```

La primera integración ejecutable es **llama.cpp**.

El objetivo inicial es comprobar:

- que el runtime está disponible;
- que el modelo local puede cargarse;
- que una solicitud puede ejecutarse;
- cuánto tiempo tarda la operación;
- qué métricas explícitas proporciona el runtime;
- que el resultado cumple el esquema común `RESULT_SCHEMA v0.1`.

## 2. Qué NO hace

Esta herramienta todavía **no es un benchmark oficial de LEONES**.

No proporciona por sí sola:

- una puntuación de calidad;
- un ranking de modelos;
- una equivalencia estadística entre máquinas;
- consumo energético;
- mediciones exactas de RAM/VRAM si el runtime no las proporciona;
- una metodología universal de rendimiento.

No se inventan métricas. Cuando un valor no puede medirse de forma fiable se devuelve `null`.

## 3. Privacidad y aislamiento

La prueba está diseñada para ejecutarse localmente.

- No importa módulos internos de LEONES.
- No accede a Atlas.
- No necesita GitHub Actions.
- No necesita credenciales de LEONES.
- No descarga modelos silenciosamente.
- No envía los resultados a LEONES por defecto.

El usuario controla el modelo, el runtime, el prompt y la ejecución.

## 4. Requisitos

- Linux/macOS/Windows con Python moderno compatible.
- Python 3.11+ recomendado.
- Un runtime local compatible con el adaptador elegido.
- Un modelo local compatible con ese runtime.

**No hay `requirements.txt` en esta fase:** el núcleo utiliza exclusivamente la biblioteca estándar de Python.

El runtime y el modelo se instalan/configuran aparte.

## 5. Comprobar la herramienta

Desde este directorio:

```bash
python3 run_tests.py
```

El comando ejecuta toda la batería de pruebas sin `pytest` ni dependencias adicionales.

## 6. Probar llama.cpp

Necesitas tener `llama-cli` instalado y accesible en el `PATH`, además de un modelo GGUF local.

Ejemplo:

```bash
python3 adapters/llama-cpp/run.py \
  --model ./modelo.gguf \
  --prompt "Explica qué es un LLM en una frase" \
  --new-tokens 32 \
  --context 2048
```

Para guardar el resultado:

```bash
python3 adapters/llama-cpp/run.py \
  --model ./modelo.gguf \
  --output resultado.json
```

El proceso devuelve código `0` si la prueba termina correctamente y `1` si existe un error de ejecución o de validación.

## 7. Validar un resultado

Puedes validar cualquier resultado generado por el paquete:

```bash
python3 validate_result.py resultado.json
```

Resultado esperado:

```text
VALID: schema 0.1
```

## 8. Métricas

El esquema común define, entre otras:

- TTFT;
- tiempo de generación;
- tiempo total;
- tokens de prompt;
- tokens generados;
- tokens/segundo;
- RAM máxima cuando pueda medirse;
- VRAM máxima cuando pueda medirse.

La v0.1 diferencia claramente entre una métrica medida y una métrica no disponible.

## 9. Runtimes

La matriz de runtimes se mantiene en [`RUNTIME_MATRIX.md`](RUNTIME_MATRIX.md).

Prioridad actual:

1. llama.cpp — P0;
2. Ollama — P0;
3. Transformers — P1;
4. vLLM — P1;
5. MLX — P2.

Que un runtime aparezca en la matriz **no significa que su adaptador esté implementado**.

## 10. Arquitectura del paquete

```text
llm-smoke-test/
├── README.md
├── RESULT_SCHEMA.md
├── RUNTIME_MATRIX.md
├── validate_result.py
├── run_tests.py
├── adapters/
│   ├── README.md
│   └── llama-cpp/
│       ├── README.md
│       └── run.py
└── tests/
    ├── test_validator.py
    └── test_llama_adapter.py
```

La separación es intencionada:

```text
LEONES web/documentación
          │
          │  independiente
          ▼
scripts/local
          │
          ▼
LLM + runtime del usuario
```

La web puede documentar, explicar y presentar resultados, pero el paquete local no depende de ella.

## 11. Diseño y evolución

Los adaptadores deben traducir las capacidades de cada runtime al mismo esquema sin falsear comparaciones.

Si un runtime no permite obtener una métrica de forma equivalente, el resultado debe conservar `null` y documentar la limitación.

Antes de convertir este paquete en un benchmark oficial se deberá fijar una metodología completa: prompts, modelos de referencia, warm-up, repeticiones, control de variables y tratamiento estadístico.

## 12. Copia independiente

Este directorio está diseñado para poder copiarse fuera del repositorio LEONES y seguir siendo entendible.

Una herramienta local **no debe importar**:

```text
atlas/
agents/
workflows/
```

ni otros componentes internos de la infraestructura.

Esa frontera es una decisión arquitectónica deliberada: **la web es el escaparate; los scripts son herramientas locales autónomas**.
