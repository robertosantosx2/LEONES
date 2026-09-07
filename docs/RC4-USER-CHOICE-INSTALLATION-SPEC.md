# LEONES RC4 — Especificación de elección, costes e instalación

**Estado:** 🔒 **FIJADO**  
**Fecha:** 2026-09-07  
**Ámbito:** selección de modelos, soluciones Personal AI / SOHO, costes, instalación y desinstalación.

## Principio rector

LEONES informa, calcula y asiste; **el usuario decide**. El usuario puede seleccionar varios propósitos, uno o varios LLM, Asistente IA personal, Servicio completo Small Office/Home Office (SOHO), o ambos. Una recomendación no equivale a elección, consentimiento, instalación, verificación ni medición.

```text
MEDICIÓN/OBSERVACIÓN → INFORMACIÓN → OPCIONES COMPATIBLES
→ USUARIO ELIGE → COSTE INDIVIDUAL + CONJUNTO → USUARIO CONFIRMA
→ INSTALACIÓN EXACTA → VERIFICACIÓN → MEDICIÓN (solo con autorización separada)
```

## Máquina ya medida

La existencia de una medición física válida de LEONES impide exigir un nuevo profiling para decidir el LLM. ODS y Magnitude son tooling opcional, no componentes canónicos ni selectores de modelo/producto.

## Modelos

La selección humana es múltiple y **no tiene límite artificial de 3**. Los límites de collectors/catalogs/recomendadores no pueden convertirse en límites de elección del usuario.

Por modelo se informa, cuando exista: id/nombre, proveedor/repo, arquitectura, cuantización/formato, tamaño de artefacto, runtime, contexto, RAM, VRAM, carga CPU/GPU, rendimiento externo, fuente, estado de evidencia y licencia. Lo desconocido es `UNKNOWN`.

## Coste individual y conjunto

Para cada modelo se muestran artefacto, runtime/dependencias, RAM/VRAM y carga estimada. Para el conjunto se calcula:

```text
disco modelos + runtimes/dependencias + datos necesarios + margen
= espacio total requerido
```

La UI distingue instalación, residencia y carga simultánea: no suma mecánicamente la RAM de modelos instalados pero no cargados simultáneamente.

## Gate de disco

```text
disco libre actual ≥ modelos + runtimes/dependencias + componentes + margen
```

Resultados: `SUFICIENTE`, `INSUFICIENTE` o `UNKNOWN`. `UNKNOWN` no se convierte en PASS. Si no cabe, la instalación queda bloqueada y no se instala parcialmente por defecto.

## Soluciones

### Asistente IA personal

Antes de instalar: componentes, funciones, modelos, runtimes, disco, RAM/VRAM, CPU/GPU, servicios/procesos, puertos, dependencias, permanencia y uninstall.

### Servicio completo SOHO

Antes de instalar: todos los componentes y funciones, modelos, runtimes, almacenamiento, red/puertos, daemons, RAM/CPU/GPU/VRAM, disco, consumo individual/total, dependencias y uninstall.

### Ambos

Además: componentes compartidos, duplicados, consumo/espacio adicional, total, conflictos de puertos/servicios y posibilidades de ejecución simultánea.

## Consentimiento e instalación

Las decisiones se mantienen separadas: propósito(s) → modelo(s) → solución(es) → cálculo → información → confirmación explícita → instalación.

LEONES instala **exactamente** lo confirmado. No añade modelos, runtimes o servicios por conveniencia sin informar y obtener el consentimiento correspondiente.

La instalación debe registrar componentes, versión/revisión, ubicación, artefactos, dependencias, resultado y fallos/pendientes. `exit 0` no equivale por sí solo a PASS de LEONES.

## Desinstalación

Todo componente ofrecido para instalar debe tener uninstall equivalente. Debe indicarse qué elimina, qué conserva, espacio recuperado si se conoce, servicios detenidos y restos opcionales. No se eliminan por defecto evidencias, mediciones, perfiles de hardware ni registros de decisiones/consentimientos.

## Estados

`DECLARED` = declarado por usuario/fuente; `ESTIMATED` = estimado; `OBSERVED` = observado; `MEASURED` = medición física protocolizada; `UNKNOWN` = no disponible/no comprobado; `BLOCKED` = requisito no resuelto.

Los benchmarks externos nunca son medición del host.

## ODS / Magnitude

Si se ofrecen, se describen como tooling independiente: función, utilidad concreta, dependencias, disco, RAM/residencia, impacto, compatibilidad y uninstall. Su elección pertenece al usuario cuando ambos sean válidos. No sustituyen la evidencia física existente.

## Criterio de cierre de esta capa

RC4 debe disponer de catálogo Personal AI/SOHO, selección múltiple de modelos sin límite artificial, costes individuales y agregados, gate de disco, carga individual/conjunta, elección Personal/SOHO/Ambos, confirmación, instalación exacta, verificación, uninstall y separación ESTIMATED/OBSERVED/MEASURED.

**Regla de memoria:** antes de modificar selección, catálogo, TUI, instalador, lifecycle, desinstalador o web relacionados con esta materia, leer este documento y comprobar que el cambio no contradice sus reglas.
