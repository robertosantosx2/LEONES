# LEONES — Implementation Readiness

## Estado

**🟢 Contratos preparados · código de ejecución aún pendiente**

Este documento consolida el punto de partida para implementar LEONES sin alterar las decisiones arquitectónicas ya cerradas.

## Componentes preparados

- ADIVINO / descubrimiento continuo
- OSI Gate
- Evidence
- Quality Gate
- Router
- MANADA
- Observabilidad
- Alertas / notificaciones
- CI/CD
- Secretos / credenciales
- Contrato común de datos y estados
- Cuantización
- Fine-tuning
- Contrato Atlas ↔ Router ↔ Evidence

## Orden recomendado de implementación

```text
1. contratos / schemas
2. almacenamiento y Atlas
3. Evidence
4. OSI Gate
5. Quality Gate
6. ADIVINO / discovery
7. CI/CD
8. Alertas
9. Router
10. MANADA
11. cuantización
12. fine-tuning
13. validación física
14. WebApp / dashboard
```

El orden evita implementar interfaces de usuario o runners sobre contratos todavía inestables.

## Regla de implementación

Primero se implementan contratos verificables y adaptadores; después los ejecutores. Una integración externa no puede convertirse en dependencia canónica sin pasar los gates establecidos.

## Datos mínimos

Todo componente debe conservar, cuando corresponda:

- identidad;
- versión;
- procedencia;
- estado;
- evidencia;
- timestamp;
- trazabilidad;
- linaje.

## No inventar datos

Los campos no conocidos permanecen explícitamente ausentes, estimados o pendientes según el contrato. Nunca se rellenan para completar tablas o satisfacer un schema.

## Promoción

```text
DESCUBRIMIENTO
 → IDENTIDAD
 → OSI (si aplica)
 → EVIDENCIA
 → QUALITY GATE
 → PROMOTION
 → ATLAS
```

## Writer único

Las tareas pueden ejecutarse en paralelo, pero la escritura canónica continúa centralizada en `leones-main-writers` con `cancel-in-progress: false`.

## Cuantización y fine-tuning

Ambos elementos se implementarán como capacidades independientes, reutilizando:

- identidad;
- evidencia;
- Quality Gate;
- observabilidad;
- estados;
- CI/CD;
- seguridad;
- promoción a Atlas.

Cada variante conserva linaje propio y no hereda automáticamente evidencia física del modelo base.

## Router

El dashboard futuro permitirá ajustar únicamente parámetros de decisión permitidos por el contrato. OSI no será un parámetro editable: el usuario podrá seleccionar `Open (todos)` o `forzar check copyleft`, según la política ya definida.

## Validación física

La validación física permanecerá separada de estimaciones y se integrará como fuente de evidencia reproducible. No se marcará una propiedad como `MEASURED` sin una medición del artefacto/modelo concreto y del entorno correspondiente.

## Criterio de entrada a implementación

Antes de cada módulo deben existir:

1. contrato de entrada;
2. contrato de salida;
3. estados;
4. errores;
5. trazabilidad;
6. política de evidencia;
7. política de concurrencia;
8. pruebas de aceptación.

## Cierre

LEONES queda en condiciones de pasar de arquitectura a implementación incremental. La siguiente actividad técnica debe ser construir los schemas y contratos ejecutables, empezando por Atlas y Evidence, y validar sus transiciones antes de desarrollar runners de modelos.
