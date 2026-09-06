# LEONES — Captura canónica de terminal

Mecanismo único para publicar salidas largas ejecutadas en Ubuntu sin
copiarlas manualmente al chat.

```text
Ubuntu
  ↓
scripts/run_capture.sh -- <comando>
  ↓
artifacts/terminal-capture/<timestamp>.txt
  ↓
docs/audits/terminal/latest.txt
  ↓
git commit + git push
  ↓
GitHub
```

`latest.txt` es el snapshot estable que se consulta para la última ejecución.

La captura completa permanece local bajo `artifacts/terminal-capture/`.
El código de salida del comando se conserva, incluyendo ejecuciones fallidas.

La captura se detiene antes de copiar `latest.txt` y antes de ejecutar Git,
siguiendo el contrato de `docs/STRICT-RUNNER-NOTES.md`.
