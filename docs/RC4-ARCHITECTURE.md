# LEONES RC4 — FitLLM recommender architecture

**Estado:** 🟢 Decisión fijada · implementación en curso  
**Predecesor:** RC3 (CERRADA)  
**Decisión:** 6 de septiembre de 2026  
**Acta:** `docs/completed/RC4-DECISION-FITLLM-RECOMMENDER-2026-09-06.md`

## 1. Objetivo

RC4 mantiene la sonda física y la autoridad de medición de LEONES.
Cambia el tramo de **preselección de modelo**: **FitLLM / LLMFit** produce una preselección de **3 LLM candidatos** a partir del hardware detectado. La preselección es ESTIMATED y no autoriza ejecución.

**RC4 no usa Hermes ni OMH en el camino canónico.** No participan en la preselección, selección, preparación, ejecución ni medición de RC4.

## 2. Flujo canónico

```text
hardware_profile.py
        ↓
hardware-profile.v1
        ↓
LEONES candidate-set.v1
        ↓
FitLLM / LLMFit
(preselección de 3 candidatos · ESTIMATED)
        ↓
usuario elige modelo
        ↓
usuario elige Magnitude | ODS
        ↓
consentimiento → install/prepare
        ↓
oferta opt-in: desinstalar FitLLM
        ↓
verificación física
        ↓
Leo001 … Leo010
        ↓
MEASURED (solo tras ejecución real)
        ↓
evidencia / recomendación final
```

## 3. Responsabilidades

| Actor | Hace | No hace |
|-------|------|---------|
| LEONES | Sonda física, candidate-set, contratos, consent log, verify, Leo*, MEASURED, evidencia y recomendación final | No sustituye instaladores de stack |
| FitLLM / LLMFit | Preselecciona y ordena **3 LLM candidatos** (ESTIMATED) | No mide, no ejecuta, no autoriza y no elige stack |
| Usuario | Elige modelo, stack (Magnitude / ODS), consentimientos y opt-in de desinstalación | — |
| Magnitude / ODS | Preparan y ejecutan según su interfaz | No son selectores de modelo LEONES |

## 4. Fronteras

- ESTIMATED ≠ MEASURED
- OBSERVED ≠ VALIDATED
- Preselección ≠ elección humana
- Recomendación ≠ ejecución
- FitLLM ausente ≠ LEONES roto
- La ausencia de FitLLM solo degrada el paso de preselección, con mensaje explícito
- Hermes / OMH **no forman parte de RC4**

## 5. Bootstrap

```text
LEONES (required)
  ↓
hardware_profile (required)
  ↓
FitLLM / LLMFit (optional — preselección de 3 candidatos)
  ↓
usuario elige modelo
  ↓
Magnitude | ODS (usuario elige)
  ↓
consentimiento
  ↓
prepare / execute
  ↓
Leo001…Leo010 cuando la medición esté autorizada
```

FitLLM es opcional y no es dependencia dura de arranque. RC4 puede funcionar sin él; en ese caso LEONES comunica que la preselección automática no está disponible y no inventa candidatos.

## 6. Relación con RC3

RC3 permanece documentada como fase cerrada.
RC4 no reabre RC3 ni invalida el acta `RC3-CLOSED-2026-09-05`.
La rama `rc3-hermes-task-benchmarks` es histórica respecto al selector y **no define el camino canónico RC4**.

## 7. Implementación

Orden mínimo:

1. Contrato de preselección FitLLM → candidate-set / recomendación de 3 candidatos.
2. Gate que garantice que FitLLM no puede autorizar ejecución ni producir MEASURED.
3. Selección humana explícita de uno de los candidatos o de otro modelo válido.
4. Selección humana de Magnitude u ODS.
5. Consentimientos separados y costes de instalación conforme a `docs/LEONES-INTERFACE-RULES.md`.
6. Preparación/ejecución física.
7. Suite Leo001…Leo010.
8. Medición y puente de evidencia → MEASURED.
9. Gate RC4 y validación física Ubuntu.

## 8. Interfaz

Toda UI CLI/web de RC4 cumple `docs/LEONES-INTERFACE-RULES.md`:

- idioma único por sesión: `es`, `en`, `zh` o `ja`;
- una sola lengua en pantalla;
- cada opción con descripción breve;
- FitLLM presentado como **preselección ESTIMATED de 3 candidatos**;
- recomendación y elección humana separadas;
- instalación y desinstalación ofrecidas por la misma vía;
- antes de instalar: disco, RAM en ejecución y residencia/daemon (o `UNKNOWN`);
- instalar, verificar y medir separados;
- ESTIMATED / OBSERVED / MEASURED explícitos;
- cancelación segura y explícita.

## 9. No objetivos

- No reabrir RC3.
- No usar Hermes ni OMH como selector, recomendador o capa canónica RC4.
- No añadir otro selector de modelos paralelo a FitLLM.
- No convertir FitLLM en autoridad de hardware o medición.
- No mapear velocidades de proveedores externos a `measured_tps` local.
- No presentar preselección ESTIMATED como medición del equipo.

## 10. Criterio de cierre RC4

RC4 se cierra cuando exista evidencia reproducible de un flujo físico completo que cubra:

`hardware → candidate-set → FitLLM (3 candidatos) → elección humana → stack → consentimiento → preparación → ejecución → Leo001…Leo010 → medición → MEASURED → evidencia → recomendación final`.

FitLLM puede estar ausente en una ejecución; eso debe quedar registrado como degradación de preselección, no como fallo de LEONES.
