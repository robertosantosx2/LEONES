# LEONES Web — referencia obligatoria

## Objetivo

La web de LEONES prioriza, en este orden:

1. simplicidad técnica;
2. legibilidad;
3. funcionalidad;
4. accesibilidad básica;
5. mantenimiento sencillo.

## Estado visible · 8 septiembre 2026

La web debe reflejar el estado canónico del repositorio (`rc4-fitllm-recommender`):

| Pieza | Estado |
|-------|--------|
| JALONES 1–4 · RC1 | 🟢 cerrados / validados |
| RC2 | 🟢 histórico (`./leones --rc2`) |
| RC3 | 🟢 fase cerrada (2026-09-05) |
| RC4 decisión + capa recomendación + gate | 🟢 fijada y endurecida en código |
| Inventario / uninstall independiente | 🟢 |
| Orquestador MEASURED (`rc4_measured_chain.py`) | 🟢 |
| MEASURED E2E físico Ubuntu | 🟡 pendiente (modelo real + doble autorización) |

Página pública de referencia: [`estado.html`](estado.html) · [`rc4.html`](rc4.html).

## RC4 · recorrido canónico

Punto de entrada por defecto: `./leones` → `scripts/rc4_runner.py`.

```text
inventario (opt) → USER_INTENT[]
   ↓
resource + ubuntu preflight
   ↓
HF + Artificial Analysis → feed ≤100
   ↓
LLMFit CLI (opcional) → intersección → ≤3 ESTIMATED | insufficient
   ↓
selección humana → stack magnitude|ods|none
   ↓
runtime → [opt-in] execute + authorize ×2 → MEASURED
```

Compatibilidad histórica:

```bash
./leones --rc2
```

## Reglas de contenido web

- **ESTIMATED ≠ MEASURED.**
- FitLLM/LLMFit es **preselector opcional**, no dependencia dura de arranque ni autoridad.
- Hermes/OMH **no** son el selector de modelo RC4.
- No inventar métricas ni promover ESTIMATED a MEASURED en copy de producto.
- Cache-bust de CSS/JS al cambiar páginas de estado (`?v=YYYY-MM-DD-N`).

## Páginas de estado (mantener alineadas)

- `index.html` — portada RC4 + ecosistema
- `estado.html` — cerrado / abierto
- `rc4.html` — capa recomendación + orquestador
- `inicio-rapido.html` · `operacion.html` · `scripts.html`
- `rc3.html` · `rc2.html` — histórico

## Publicación

Los HTML bajo `web/` son la superficie publicada. Cualquier cambio de estado de proyecto debe reflejarse aquí el mismo día, no solo en `docs/`.
