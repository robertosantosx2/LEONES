# Buddy — límite de licencia para integraciones

Buddy declara **GPL-3.0** upstream. ODS y Magnitude declaran **Apache-2.0** en sus repositorios actuales.

Por ello, la integración prevista debe mantener Buddy como componente separado y no copiar su código dentro de los árboles Apache de ODS o Magnitude. Un adaptador LEONES independiente puede comunicarse con Buddy mediante interfaces/procesos definidos, pero cualquier distribución conjunta debe pasar revisión de licencias y de la forma concreta de enlace/empaquetado.

## Regla operativa

```text
ODS (Apache-2.0) ── API/process boundary ── Buddy (GPL-3.0)
Magnitude (Apache-2.0) ── API/process boundary ── Buddy (GPL-3.0)
LEONES ── adapter/documentation ── Buddy
```

No se debe presentar una integración como “incluida” dentro de ODS/Magnitude hasta verificar los artefactos finales de distribución y sus licencias transitivas.
