# LEONES — Adquisición de artefactos

La adquisición es posterior a la selección y al resolver GGUF:

```text
SELECTOR → RUNTIME GATE → GGUF RESOLVER → ACQUISITION → RUNTIME
```

## Fuente primaria

Hugging Face es la fuente remota primaria cuando el plan contiene una URL
explícita. La adquisición no busca ni recomienda modelos por su cuenta.

## Garantías

- caché local determinista;
- descarga atómica mediante archivo temporal + rename;
- SHA-256 cuando se proporciona;
- ningún artefacto con checksum incorrecto pasa al nombre final;
- procedencia persistida en `.leones.json`;
- modelo y cuantización son datos de entrada y nunca se sustituyen;
- CI no descarga modelos grandes.

## Estados

`ACQUIRED`, `CACHE_HIT`, `CHECKSUM_MISMATCH` y `ACQUISITION_REQUIRED`.

La siguiente capa puede conectar esta salida al GGUF resolver y al adaptador
llama.cpp. La adquisición sigue sin ejecutar modelos.
