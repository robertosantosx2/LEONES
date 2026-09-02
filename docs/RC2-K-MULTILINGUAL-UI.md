# RC2-K — Interfaz multilingüe

**Estado:** 🟢 Contrato fijado (feedback beta 2026-09-02)

## Regla de presentación

1. Al arrancar, el wizard pregunta **una sola vez** el idioma.
2. A partir de esa elección, **solo se muestra el idioma seleccionado**.
3. El catálogo interno (`scripts/rc2_i18n.py`) mantiene ES / EN / ZH.
4. `tr(key)` devuelve un solo idioma; `tr_all(key)` es solo depuración.

```text
ELIGE EL IDIOMA / CHOOSE LANGUAGE / 选择语言
┌──────────────────────────────────────────┐
│  [1] Español                             │
│  [2] English                             │
│  [3] 中文                                 │
└──────────────────────────────────────────┘
```

## Motivo

La presentación simultánea de tres idiomas en cada línea dificultaba la lectura y empeoraría al añadir idiomas. La pregunta inicial reduce ruido sin perder cobertura.

## Requisitos

1. No mezclar traducciones que cambien el significado técnico.
2. Identificadores técnicos, comandos y métricas permanecen canónicos.
3. Tests: cada clave tiene ES/EN/ZH; el wizard no emite columnas trilingües tras la elección.
