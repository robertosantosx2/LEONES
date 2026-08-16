# H07 — JGB sistemático

**Estado: 🟡 INFRAESTRUCTURA OPERATIVA; clasificación factual pendiente de evidencia primaria.**

## Objetivo

Aplicar de forma reproducible el marco JGB de Jesús M. Gonzalez-Barahona a los candidatos del Atlas sin convertir apertura en una puntuación de calidad, rendimiento o precio.

## Regla fundamental

Una etiqueta comercial como `open weights`, la posibilidad de descargar pesos o la posibilidad de ejecutar localmente **no basta** para asignar JGB.

Cada dimensión se conserva separada:

- Access
- Model control
- Data control
- Autonomy
- Trust

Y el estado de la evaluación puede ser:

- `verified`
- `provisional`
- `unknown`
- `disputed`

Cuando falta evidencia, el resultado correcto es `unknown`.

## Flujo

```text
CANDIDATO ATLAS
      ↓
EVIDENCIA PRIMARIA
      ↓
ACCESS
MODEL CONTROL
DATA CONTROL
AUTONOMY
TRUST
      ↓
REQUISITOS DE CLASE
      ↓
JGB CLASS
      ↓
CONFIDENCE + SOURCES
```

## Separaciones obligatorias

```text
JGB ≠ benchmark
JGB ≠ calidad
JGB ≠ rendimiento
JGB ≠ precio
JGB ≠ self-hostability
JGB ≠ CABE
JGB ≠ RULA
```

Un modelo puede ser excelente técnicamente y tener JGB bajo; también puede tener JGB alto y no caber en un hardware concreto.

## Evidencia mínima

Para una clasificación `verified` se necesita evidencia suficiente para justificar cada dimensión relevante y la clase final. Deben conservarse fuente primaria, URL, fecha de comprobación, licencia/condiciones, disponibilidad de pesos, software y documentación de entrenamiento cuando sean requisitos de la clase.

## Resultado actual

La infraestructura JGB queda preparada, pero **no se inventarán clasificaciones para los 193 candidatos H06**: el informe H06 confirmó que los candidatos actuales son `unverified` y ninguno ha sido promovido al Atlas canónico. Por tanto, H07 empieza con una cola de verificación, no con un catálogo JGB falsamente completo.

## Subfases

- H07.1 contrato y reglas 🟢
- H07.2 auditoría de candidatos 🟡
- H07.3 evidencia primaria 🟡
- H07.4 clasificación verificable ⚪
- H07.5 integración con recomendador ⚪
- H07.6 validación final ⚪

## Documentación base

- [`../../../web/proyectos/atlas/openness/JGB-INDEX.md`](../../../web/proyectos/atlas/openness/JGB-INDEX.md)
- [`../../../web/proyectos/atlas/openness/JGB-MATRIX.md`](../../../web/proyectos/atlas/openness/JGB-MATRIX.md)
- [`../../../web/proyectos/atlas/openness/JGB-METHOD.md`](../../../web/proyectos/atlas/openness/JGB-METHOD.md)
- [`../2026-08-atlas-expanded/`](../2026-08-atlas-expanded/)

## Criterio de cierre

H07 solo podrá declararse 🟢 cuando las clasificaciones publicadas tengan evidencia suficiente, sean reproducibles, mantengan `unknown` cuando corresponda y pasen una auditoría que impida inferir JGB desde rendimiento, licencia nominal o self-hostability.
