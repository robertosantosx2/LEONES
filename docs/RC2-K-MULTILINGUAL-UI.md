# RC2-K — Interfaz multilingüe

**Estado:** 🟢 Contrato actualizado (feedback beta 2026-09-02)

La interfaz de usuario de RC2 soporta **Español · English · 中文**.

## Regla de presentación (actualizada)

1. Al arrancar, el wizard pregunta **una sola vez** el idioma.
2. A partir de esa elección, **solo se muestra el idioma seleccionado**.
3. El catálogo interno sigue manteniendo las tres traducciones completas.
4. Añadir un idioma nuevo no debe obligar a mostrar todos a la vez.

```text
ELIGE EL IDIOMA / CHOOSE LANGUAGE / 选择语言
┌──────────────────────────────────────────┐
│  [1] Español                             │
│  [2] English                             │
│  [3] 中文                                 │
└──────────────────────────────────────────┘
```

Después, por ejemplo en español:

```text
ELIGE TU MODELO
```

No:

```text
ES │ ELIGE TU MODELO
EN │ CHOOSE YOUR MODEL
ZH │ 选择你的模型
```

## Motivo del cambio

La presentación simultánea de los tres idiomas en cada línea dificultaba la lectura del beta tester y empeoraría al añadir más idiomas. La pregunta inicial de idioma reduce ruido sin perder cobertura multilingüe.

## Alcance traducido

Se traducen al idioma activo:

- títulos y navegación;
- estados y mensajes de progreso;
- explicaciones de hardware;
- candidatos de modelos;
- resúmenes y funcionalidades de ODS y Magnitude;
- requisitos y efectos de instalación;
- consentimiento de instalación;
- consentimiento de benchmark;
- errores, bloqueos y recuperación;
- resultados y resumen final.

Los identificadores técnicos, nombres de modelos, comandos, rutas, métricas y valores de contrato permanecen en su forma canónica.

## Requisitos de calidad

1. No mezclar traducciones que cambien el significado técnico.
2. No ocultar información crítica por falta de traducción en el idioma activo.
3. El texto chino debe usar Unicode UTF-8.
4. El ASCII art debe seguir siendo legible.
5. Los mensajes de consentimiento se muestran en el idioma activo (no en tres columnas).
6. Los tests verifican que cada clave tiene ES/EN/ZH y que el wizard usa un solo idioma tras la elección.

## Arquitectura

La interfaz consume claves semánticas (`tr("choose_model")`), no cadenas duplicadas en el código. `set_language()` fija el idioma de sesión; `tr_all()` queda solo como ayuda de depuración.

La internacionalización no modifica las decisiones ni los gates de seguridad: solo cambia la presentación humana del mismo estado canónico.
