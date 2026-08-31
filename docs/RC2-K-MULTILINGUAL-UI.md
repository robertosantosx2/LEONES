# RC2-K — Interfaz trilingüe

**Estado:** 🟢 Contrato fijado

La interfaz de usuario de RC2 será simultánea en **Español · English · 中文**. No será una traducción posterior ni una opción que oculte los otros idiomas: las tres lenguas forman parte de la presentación principal del wizard.

## Regla visual

Cada pantalla operativa debe presentar el mismo significado en los tres idiomas:

```text
┌────────────────────────────────────────────────────────────┐
│  ELIGE TU MODELO                                           │
│  CHOOSE YOUR MODEL                                         │
│  选择你的模型                                               │
└────────────────────────────────────────────────────────────┘
```

## Alcance

Se traducen simultáneamente:

- títulos y navegación;
- estados y mensajes de progreso;
- explicaciones de hardware;
- candidatos de modelos;
- funcionalidades de ODS y Magnitude;
- requisitos y efectos de instalación;
- consentimiento de instalación;
- consentimiento de benchmark;
- errores, bloqueos y recuperación;
- resultados y resumen final.

Los identificadores técnicos, nombres de modelos, comandos, rutas, métricas y valores de contrato permanecen en su forma canónica para evitar ambigüedad.

## Requisitos de calidad

1. No mezclar traducciones que cambien el significado técnico.
2. No ocultar información por idioma.
3. El texto chino debe usar Unicode UTF-8 y una tipografía con cobertura CJK adecuada.
4. El ASCII art debe seguir siendo legible en las tres versiones.
5. Los mensajes críticos de consentimiento deben mostrar las tres lenguas en la misma pantalla.
6. Los tests deben verificar que cada clave obligatoria tiene ES/EN/ZH.

## Arquitectura

La interfaz debe consumir claves semánticas, no cadenas duplicadas dentro del código. Esto permite ampliar idiomas posteriormente sin modificar la máquina de estados ni los contratos de ejecución.

Ejemplo conceptual:

```text
ui.confirm_benchmark
  ├── es: ¿Quieres ejecutar el benchmark?
  ├── en: Do you want to run the benchmark?
  └── zh: 是否运行基准测试？
```

La internacionalización no modifica las decisiones ni los gates de seguridad: solo cambia la presentación humana del mismo estado canónico.
