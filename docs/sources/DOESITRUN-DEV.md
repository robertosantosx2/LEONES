# doesitrun.dev

## Identidad
- **Fuente primaria:** https://doesitrun.dev/
- **Capa LEONES:** compatibilidad hardware/modelo.
- **Estado:** `research-candidate`.
- **Revisión:** 2026-08-25.

## Qué es
Calculadora web que reduce la pregunta de ejecución local a un cruce entre modelo y hardware. Es útil como referencia independiente de la familia «Can I run this LLM?».

## Qué aporta a LEONES
Su principal valor no es una funcionalidad única, sino aportar una **señal independiente**. En un sistema de recomendación serio, varios estimadores pueden ser mejores como detectores de discrepancias que como fuentes de una cifra promedio.

## Fuente y evidencia
La web es la fuente primaria de sus resultados. Estos deben conservarse como información externa y fecharse durante la incorporación.

## Estimación
Compatibilidad, memoria y requisitos de ejecución son estimaciones del servicio. No son mediciones LEONES.

## Medición LEONES
Pendiente. Una futura prueba debe usar exactamente el modelo, cuantización, contexto y runtime que se esté contrastando.

## Relación con otros estimadores

```text
doesitrun.dev
     │
     ├── comparación → LLMFit
     ├── comparación → localmodel.run
     ├── comparación → VRAMBudget
     └── comparación → CanIRun.ai
```

La salida de cada fuente debe mantenerse separada para poder estudiar falsos positivos y falsos negativos.

## Valor
Medio. Es una buena fuente de prospección/cross-validation, pero no debe alimentar directamente la recomendación final sin pasar por el contrato de LEONES.

## Limitaciones
- Datos externos potencialmente cambiantes.
- Fit no equivale a rendimiento.
- No demuestra calidad funcional.
- No sustituye la selección de runtime ni el benchmark real.

## Integración
`source → external estimate → candidate → runtime-selection.v1 → executor → grader → benchmark`.

## Clasificación
`research-candidate`.

## Próximo paso
Incluirlo en el conjunto de estimadores comparados y medir cuántas discrepancias aporta frente a los modelos de cálculo más completos.