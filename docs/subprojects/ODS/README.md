# Subproyecto ODS — Osmantic Deployment System

## 1. Misión

Integrar ODS en LEONES como **stack de despliegue local opcional**, sin convertirlo en dependencia del núcleo.

En la revisión del 20-08-2026 se identificó `v2.6.0` como release estable según la documentación revisada. Esta referencia debe volver a verificarse antes de congelar una instalación de producción o benchmark.

Fuente primaria del proyecto: `https://github.com/Osmantic/ODS`

## 2. Frontera de responsabilidad

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

## 3. Contrato de integración

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

## 4. Ciclo operativo

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

## 5. Reproducibilidad

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

## 6. Evidencia frente a medición

La documentación y las capacidades declaradas por ODS son **evidencia externa**. No se convierten automáticamente en resultados LEONES.

Solo una ejecución instrumentada puede alimentar `schemas/result.schema.json`.

## 7. Validación mínima

Antes de declarar una instalación utilizable:

- [ ] versión fijada;
- [ ] instalación reproducible;
- [ ] servicios esperados activos;
- [ ] health checks correctos;
- [ ] modelo/runtime identificados;
- [ ] secretos fuera de logs/resultados;
- [ ] benchmark smoke ejecutable;
- [ ] cleanup/recovery probado.

## 8. Estado

🟡 **DISEÑO LIMPIO Y CONGELADO.**

Siguiente fase: adaptador ejecutable `detect → pin → install → verify → measure → report`, empezando por una instalación reproducible controlada.

## Referencias

- ODS: `https://github.com/Osmantic/ODS`
- Índice de subproyectos: `docs/subprojects/README.md`
- Contrato de resultados: `schemas/result.schema.json`
