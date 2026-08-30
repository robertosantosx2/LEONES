# JALÓN 3 — Auditoría reproducible

Esta carpeta contiene el espejo Git-tracked de la salida del runner de auditoría de JALÓN 3.

## Flujo

```text
Ubuntu
  ↓
scripts/run_jalon3_audit.sh
  ↓
artifacts/jalon3-audit/<timestamp>.txt   (salida completa local, ignorada)
  ↓
docs/audits/jalon3/latest.txt          (espejo rastreado por Git)
  ↓
push
  ↓
GitHub
```

El objetivo es evitar copiar salidas largas del terminal al chat. El fichero `latest.txt` es la referencia compacta que debe consultarse para la última auditoría.

Los artefactos de runtime continúan bajo `artifacts/` y no se convierten en masa en ficheros Git-tracked.
