# Cuadros maestros · actualización diaria (Artificial Analysis)

## Qué se actualiza

- Archivo canónico: [`cuadros-maestros.csv`](./cuadros-maestros.csv)
- Página: [`../cuadros-maestros.html`](../cuadros-maestros.html) (tabla alimentada por el CSV)

## Cadencia

- **Diaria** · **05:00 Europe/Madrid** vía automatización Grok del proyecto LEONES.
- Fuente de ranking: [Artificial Analysis · Model Leaderboard](https://artificialanalysis.ai/leaderboards/models) — **open weights**, Intelligence Index (Coding Index solo para desempates de coding).

## Contrato

- **ESTIMATED ≠ MEASURED**
- Solo open-weight local
- VRAM limita primero; RAM 2–4 GB = no viable
- Flagships open multi-cientos-B solo como MoE parcial / offload en PCs de consumo

## Commit

`data: cuadros maestros AA YYYY-MM-DD (open-weight refresh)`

Si no hay cambios materiales en el ranking o en el encaje VRAM, no se hace commit vacío.
