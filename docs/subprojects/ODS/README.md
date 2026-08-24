# Subproyecto ODS — Osmantic Deployment System

## 1. Misión

Integrar ODS en LEONES como **stack de despliegue local opcional**, sin convertirlo en dependencia del núcleo.

En la revisión del 20-08-2026 se identificó `v2.6.0` como release estable según la documentación revisada. Esta referencia debe volver a verificarse antes de congelar una instalación de producción o benchmark.

Fuente primaria del proyecto: `https://github.com/Osmantic/ODS`

## 2. Mapa documental

- [`../../integrations/ODS/README.md`](../../integrations/ODS/README.md) — contrato de integración LEONES.
- [`../../sources/ODS.md`](../../sources/ODS.md) — ficha de conocimiento y separación fuente/evidencia/estimación/medición.
- [`../ODS-Magnitude-INTEGRATION.md`](../ODS-Magnitude-INTEGRATION.md) — relación ODS ↔ Magnitude.
- [`../ODS-Magnitude-AUDIT.md`](../ODS-Magnitude-AUDIT.md) — auditoría conjunta.
- [`../../AGENT_HARNESSES.md`](../../AGENT_HARNESSES.md) — Hermes/ODS y otros harnesses.
- [`../../E2E.md`](../../E2E.md) — validación de integraciones.
- [`../../../schemas/result.schema.json`](../../../schemas/result.schema.json) — resultado canónico.
- [`../../../atlas/README.md`](../../../atlas/README.md) — destino de evidencia apta.

## 3. Frontera de responsabilidad

```text
LEONES
 ├── Atlas              identidad + evidencia
 ├── Recommender        selección
 ├── Benchmark          medición
 └── ODS adapter        despliegue
                          ↓
                     ODS / servicios
```

ODS instala y opera servicios. **LEONES decide qué medir y qué evidencia aceptar.**

## 4. Contrato de integración

### Entrada

- recomendación de modelo/hardware;
- versión ODS fijada;
- configuración del entorno;
- política de permisos;
- destino de instalación.

### Salida

- versión exacta instalada;
- servicios activos;
- modelo/runtime configurados;
- configuración relevante;
- hardware no identificativo;
- estado de verificación;
- referencia al benchmark ejecutado.

Los secretos nunca forman parte de la salida.

## 5. Ciclo operativo

```text
DETECT
  ↓
SELECT
  ↓
PIN
  ↓
INSTALL
  ↓
VERIFY
  ↓
MEASURE
  ↓
REPORT
  ↓
CLEANUP / RECOVER
```

Cada etapa debe ser idempotente o declarar claramente por qué no lo es.

## 6. Reproducibilidad

Para benchmarking se debe conservar un manifiesto con:

- ref/versión ODS;
- sistema operativo;
- arquitectura;
- CPU/RAM/GPU cuando proceda;
- versión de Docker/Compose si intervienen;
- modelos y revisiones;
- configuración relevante;
- fecha de ejecución;
- benchmark y versión del grader.

No se recomienda seguir `main` para una campaña reproducible.

## 7. Evidencia frente a medición

La documentación y las capacidades declaradas por ODS son **evidencia externa**. No se convierten automáticamente en resultados LEONES.

Solo una ejecución instrumentada puede alimentar `schemas/result.schema.json`.

```text
ODS recommendation → reported / estimated
ODS configuration  → observed
LEONES benchmark   → measured
```

## 8. Validación mínima

Antes de declarar una instalación utilizable:

- [ ] versión fijada;
- [ ] instalación reproducible;
- [ ] servicios esperados activos;
- [ ] health checks correctos;
- [ ] modelo/runtime identificados;
- [ ] secretos fuera de logs/resultados;
- [ ] benchmark smoke ejecutable;
- [ ] cleanup/recovery probado;
- [ ] resultado conforme al contrato canónico cuando exista medición.

## 9. Estado

🟡 **DISEÑO LIMPIO Y CONGELADO.**

Siguiente fase: adaptador ejecutable `detect → pin → install → verify → measure → report`, empezando por una instalación reproducible controlada.

## 10. Referencias

- ODS: `https://github.com/Osmantic/ODS`
- ODS Quick Start: `https://github.com/Osmantic/ODS/blob/main/ods/QUICKSTART.md`
- ODS Architecture: `https://github.com/Osmantic/ODS/blob/main/ARCHITECTURE.md`
- Índice de subproyectos: [`../README.md`](../README.md)
- Integración LEONES: [`../../integrations/ODS/README.md`](../../integrations/ODS/README.md)
- Ficha de conocimiento: [`../../sources/ODS.md`](../../sources/ODS.md)
