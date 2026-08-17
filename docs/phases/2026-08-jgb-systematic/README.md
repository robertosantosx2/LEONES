# H07 — JGB sistemático

**Estado: 🟡 INFRAESTRUCTURA Y PROCESO CERRADOS; captura de evidencia real iniciada.**

## Nota de estado

H07 está cerrado en cuanto a infraestructura, procedimiento, integración y validación del mecanismo. La siguiente etapa ya no es diseñar más infraestructura: es **obtener, registrar y auditar evidencia primaria real por modelo**.

La ausencia de evidencia no se rellenará mediante inferencias: el modelo permanecerá `unknown` o `provisional` según corresponda.

Se ha iniciado la primera comprobación real con **Qwen3.5-9B**. El registro de evidencia se encuentra en `web/proyectos/atlas/openness/jgb_primary_evidence.csv`. Esta primera tanda todavía no permite una clase JGB verificada porque `data_control`, `autonomy` y, especialmente, `trust` no están suficientemente demostrados con las fuentes recogidas.

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

El evaluador exige ahora, además, **nivel válido + estado de evidencia + al menos una fuente por dimensión** antes de derivar una clase. Una evidencia `provisional`, `unknown` o `disputed` no puede producir por sí sola una clase global respaldada.

## Estado factual

Los 193 candidatos H06 siguen `unverified` y ninguno ha sido promovido al Atlas canónico. La nueva cola de trabajo es evidencia real por modelo.

### Primer registro real: Qwen3.5-9B

Las fuentes primarias consultadas documentan pesos públicos, licencia Apache 2.0 y rutas de ejecución local. Eso permite registrar evidencia positiva para `access` y `model_control`; no basta por sí solo para cerrar las cinco dimensiones JGB. La licencia Apache 2.0 concede reproducción, obras derivadas y distribución bajo sus condiciones, y el repositorio documenta ejecución local con Transformers, vLLM y SGLang. 

**Resultado H07 actual:** evidencia parcial, clasificación global aún `unknown`.

## Subfases cerradas

- H07.1 contrato y reglas 🟢
- H07.2 auditoría de candidatos 🟢
- H07.3 evidencia primaria — mecanismo 🟢 / captura real 🟡
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
- `../../../web/proyectos/atlas/openness/jgb_primary_evidence.csv`

## Mantenimiento

No se reabre H07 para añadir infraestructura salvo que aparezca un fallo reproducible. La actividad normal de H07 pasa a ser la captura, revisión y auditoría progresiva de evidencia primaria. Las futuras evidencias deben conservar procedencia y mantener `unknown` cuando la fuente primaria no permita una conclusión verificable.

## No concurrencia

Todo workflow futuro que escriba en el catálogo o artefactos canónicos debe respetar la regla global: `leones-main-writers` y `cancel-in-progress: false`.
