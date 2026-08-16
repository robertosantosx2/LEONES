# Runtime adapters

Los adaptadores conectan el harness de `llm-smoke-test` con un runtime local concreto.

## Regla de aislamiento

Cada adaptador es opcional. El núcleo del test no depende de ningún runtime.

```text
llm-smoke-test
      │
      ├── adapter: llama.cpp
      ├── adapter: Ollama
      ├── adapter: Transformers
      └── adapter: otros runtimes
```

Un adaptador debe:

- comprobar que su runtime está instalado;
- no instalarlo silenciosamente;
- recibir explícitamente modelo y parámetros;
- ejecutar únicamente en el equipo del usuario;
- devolver resultados al esquema común;
- no importar código de `atlas/`, `agents/` ni infraestructura de LEONES;
- documentar requisitos y limitaciones;
- no enviar datos externos salvo que el usuario lo configure explícitamente.

La primera implementación real se hará sólo después de fijar el esquema de métricas del benchmark. Este directorio define la frontera, no una garantía de compatibilidad todavía.
