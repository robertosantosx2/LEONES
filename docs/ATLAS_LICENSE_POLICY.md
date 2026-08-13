# LEONES Atlas — política de licencias

## Regla principal

La prospección descubre; no valida. Un elemento descubierto entra primero como `external-unvalidated`.

Para software, runtimes, agentes, skills, harnesses y herramientas, LEONES prioriza licencias aprobadas por OSI. La licencia se debe verificar contra la lista oficial de OSI antes de marcar un componente como `osi-approved`.

Los modelos se tratan por separado: una licencia de pesos open-weight no se convierte en licencia OSI de software. Atlas conserva `open_weights`, `license` y `osi_status` como campos independientes.

## Estados

- `osi-approved`: licencia de software verificada como aprobada por OSI.
- `non-osi-model-license`: licencia de pesos/modelo que no debe clasificarse como licencia OSI de software.
- `unknown`: no se ha podido verificar.
- `restricted`: existen restricciones incompatibles con la política de recomendación Libre/Open.
- `rejected`: no entra en la pila recomendada.

## Flujo

`fuente -> descubrimiento -> deduplicación -> licencia -> external-unvalidated -> revisión -> Atlas`

Ningún bot debe convertir automáticamente un hallazgo en evidencia `verified`.
