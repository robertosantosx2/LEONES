# LEONES — MSA · Run local

**Fuente canónica:** https://msa.millaguie.net/#local  
**Alias histórico:** `msa.millaguie.net/#sc-local` (ancla no encontrada; la sección real es `Run local` / `#local`)  
**Nombre del sitio:** Model Spend Arena (MSA)  
**Estado:** fuente verificada · acceso primario recuperado  
**Fecha de primera revisión:** 2026-08-23 (UNRESOLVED)  
**Fecha de verificación:** 2026-09-02

## 1. Qué es

**Model Spend Arena** es un mapa público de coste y calidad de modelos de coding (API y local). Agrega precios, índices de calidad de terceros (p. ej. Artificial Analysis) y, en la sección **Run local**, mediciones first-party de modelos open-weight en hardware real.

La sección relevante para LEONES es **Run local** (`#local` / `#localpick`): catálogo de modelos que caben por presupuesto de VRAM, con tamaños GGUF medidos, contexto residual por cuantización y resultados propios de BigCodeBench-Hard donde existen.

## 2. Resultado de la verificación (2026-09-02)

- El sitio `https://msa.millaguie.net/` responde y está actualizado (p. ej. 2026-08-30).
- No existe un ancla estable `#sc-local`. La sección de ejecución local se identifica como **Run local** con anclas `#local`, `#localpick`, `#8-gb`, `#12-gb`, `#16-gb`, `#24-gb`, `#32-gb`.
- Contenido observado (no inventado):
  - Tablas por tier de VRAM (≤8 / 12 / 16 / 24 / 32 GB).
  - Pesos reales en bytes GGUF (~Q4 y otras cuantizaciones).
  - Ranking mixto: **% BCB** (BigCodeBench-Hard first-party de MSA) vs **coding index** de Artificial Analysis cuando no hay medición local.
  - Aviso explícito de que ambas escalas **no son comparables** y de que mediciones anteriores al 2026-08-23 con protocolo de 121 problemas fueron retiradas.
  - Uso de **llama.cpp / llama-server**, cuantizaciones GGUF, MTP speculative decoding, tok/s medidos en GPUs de escritorio (no solo en cluster).
  - Créditos: DIIC (Universidad de Murcia) + GPUs domésticas; tok/s solo desde tarjetas de casa.

## 3. Qué aporta a LEONES

- **Fuente de prospección** de candidatos open-weight orientados a coding local.
- **Evidencia externa first-party** (MSA) de calidad agentica/coding bajo protocolo documentado, distinta del índice AA.
- Criterios útiles para el selector: VRAM real (pesos + KV), trade-off cuantización vs contexto, y que “cabe” no implica “útil”.
- Referencia metodológica: retirada de números no comparables en lugar de convertirlos.

## 4. Cómo lo usará LEONES

```text
MSA Run local
      ↓
descubrimiento de candidatos (modelo + quant + VRAM)
      ↓
identidad primaria + procedencia (reported / MSA-first-party)
      ↓
quality gate
      ↓
candidate → runtime-selection.v1
      ↓
benchmark LEONES (no sustituye la medición propia)
      ↓
evidence
```

Reglas:

- Las cifras de MSA son **`reported`** (publicadas por MSA) o **first-party MSA**, nunca `measured` de LEONES.
- No se promocionan a recomendación oficial sin pasar por el pipeline LEONES.
- El ancla canónica a citar es `#local`, no `#sc-local`.

## 5. Contrato de evidencia

| Estado | Significado |
|--------|-------------|
| `reported` | Dato publicado por MSA (precio, índice AA, tabla local) |
| `observed` | LEONES confirmó la presencia del dato en la fuente |
| `verified` | Comprobado contra la URL primaria en una fecha dada |
| `measured` | Solo si LEONES ejecuta el mismo protocolo en su hardware |

## 6. Limitaciones

- Catálogo en evolución; MSA avisa de que no es “gospel”.
- Mezcla deliberada de escalas BCB e idx en los tiers: no usarlas como una sola métrica.
- Hardware y build de llama.cpp de MSA no son el hardware del usuario de LEONES.

## 7. Enlaces

- Sitio: https://msa.millaguie.net/
- Run local: https://msa.millaguie.net/#local
- Pick of the week (local): https://msa.millaguie.net/#localpick
- Página web LEONES: `web/msa-sc-local.html`
