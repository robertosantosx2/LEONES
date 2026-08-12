# Hardware Intelligence

## Objetivo

Hardware Intelligence convierte el equipo local en un perfil que LEONES puede utilizar para decidir qué modelos y runtimes son viables.

## Primera versión

La primera implementación detecta únicamente información básica:

- CPU;
- arquitectura;
- RAM total;
- número de CPUs lógicas;
- sistema operativo;
- capacidades básicas detectadas.

No intenta todavía medir rendimiento ni detectar exhaustivamente GPU/NPU.

## Scripts

### `leones.hardware_report`

Solo detecta y muestra el perfil.

```bash
python -m leones.hardware_report
```

### `leones.hardware_register`

Solo detecta el perfil y lo registra en un Atlas SQLite.

```bash
python -m leones.hardware_register --atlas leones_atlas.sqlite
```

La separación es intencionada: **detectar** y **registrar** son responsabilidades diferentes.

## Evolución prevista

Se añadirán posteriormente probes independientes para:

- GPU y VRAM;
- NPU;
- instrucciones CPU relevantes;
- memoria disponible;
- almacenamiento;
- microbenchmarks LEONES.

Cada probe debe conservar la regla básica de LEONES: una responsabilidad pequeña, documentación clara y resultado reproducible.
