# H07 — JGB sistemático

**Estado: 🟢 INFRAESTRUCTURA Y PROCESO CERRADOS; evidencia real por modelo pendiente.**

## Nota de cierre

H07 queda **cerrado en cuanto a infraestructura, procedimiento, integración y validación del mecanismo**.

**Pendiente:** obtener y registrar evidencia primaria real para cada modelo antes de publicar una clasificación JGB factual como `verified`. La ausencia de esa evidencia no se rellenará mediante inferencias: el modelo permanecerá `unknown` o `provisional` según corresponda.

Este cierre **no significa que los 193 candidatos dispongan ya de una clasificación JGB verificada**. Significa que LEONES dispone del mecanismo necesario para producirla de forma trazable cuando exista evidencia suficiente.

## Objetivo y reglas

Aplicar de forma reproducible el marco JGB de Jesús M. Gonzalez-Barahona sin convertir apertura en una puntuación de calidad, rendimiento o precio.

Las dimensiones se conservan separadas: Access, Model control, Data control, Autonomy y Trust. Los estados son `verified`, `provisional`, `unknown` y `disputed`. Cuando falta evidencia, el resultado correcto es `unknown`.

```text
CANDIDATO → EVIDENCIA PRIMARIA → DIMENSIONES JGB → REQUISITOS DE CLASE
          → JGB CLASS → CONFIDENCE + SOURCES → ATLAS / ROUTER
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

## Evidencia mínima

Una clasificación `verified` necesita evidencia suficiente para justificar cada dimensión relevante y la clase final. Se conserva fuente primaria, URL, fecha, condiciones de licencia, disponibilidad de pesos, software y documentación de entrenamiento cuando sean requisitos de la clase.

## Estado factual

La infraestructura JGB está preparada y validada, pero los 193 candidatos H06 siguen `unverified` y ninguno ha sido promovido al Atlas canónico. La cola futura es **evidencia real por modelo**, no desarrollo de infraestructura.

## Subfases cerradas

- H07.1 contrato y reglas 🟢
- H07.2 auditoría de candidatos 🟢
- H07.3 evidencia primaria — mecanismo 🟢
- H07.4 clasificación verificable — mecanismo 🟢
- H07.5 integración Atlas/Router — contrato 🟢
- H07.6 validación final — mecanismo 🟢

## Documentación

- `H07.2-AUDIT.md`
- `H07.3-PRIMARY-EVIDENCE.md`
- `H07.4-VERIFIABLE-CLASSIFICATION.md`
- `H07.5-ATLAS-INTEGRATION.md`
- `H07.6-FINAL-VALIDATION.md`
- `../../../web/proyectos/atlas/openness/JGB-INDEX.md`
- `../../../web/proyectos/atlas/openness/JGB-MATRIX.md`
- `../../../web/proyectos/atlas/openness/JGB-METHOD.md`

## Mantenimiento

No se reabre H07 para añadir infraestructura salvo que aparezca un fallo reproducible. Las futuras evidencias deben conservar procedencia y mantener `unknown` cuando la fuente primaria no permita una conclusión verificable.

## No concurrencia

Todo workflow futuro que escriba en el catálogo o artefactos canónicos debe respetar la regla global: `leones-main-writers` y `cancel-in-progress: false`.
