# JALÓN 4 — Taxonomía y alcance de runtimes físicos

**Estado:** 🟠 IMPLEMENTACIÓN FIJADA · VALIDACIÓN DE HOST PENDIENTE  
**Base:** `rc1-minimal-script-cleanup`

## 1. Objetivo

Convertir el registro de runtimes en un contrato de selección física: LEONES debe distinguir qué runtimes son apropiados para workstation/local y cuáles para datacenter/serving, antes de intentar ejecutarlos.

JALÓN 4 no mide rendimiento. Define el **alcance operativo** y evita seleccionar un runtime incompatible con el tipo de despliegue o servicio solicitado.

## 2. Taxonomía canónica

### Deployment class

- `workstation`
- `datacenter`

### Serving profile

- `single_user`
- `multi_user`

La combinación de ambos campos forma parte del contrato de selección.

## 3. Registro actual

El registro `runtime-registry.v1.1` contiene 11 runtimes. Cada entrada declara clase de despliegue, perfil de servicio, modos, arquitecturas, formatos, backends, capacidades, entrypoint, disponibilidad, métrica y requisitos del host.

## 4. Regla de selección

El selector no debe considerar equivalente un runtime local y uno de serving.

```text
workstation + single_user → runtimes workstation
 datacenter + multi_user   → runtimes datacenter
```

La clasificación no afirma rendimiento. Solo determina compatibilidad declarativa.

## 5. Regla física

Toda entrada marcada `physical_test_required: true` necesita validación en el host antes de convertirse en evidencia de rendimiento.

El registro puede declarar compatibilidad; no puede convertir esa declaración en medición.

## 6. Integración realizada

La puerta `scripts/runtime_gate.py` aplica ahora la taxonomía del registro al candidato seleccionado. Si se proporcionan `deployment_class`, `serving_profile`, arquitectura, formato, modo, backend o capacidades requeridas, cualquier incompatibilidad bloquea el plan antes de la ejecución física.

Además, las pruebas de JALÓN 4 cubren tanto la taxonomía del registro como su aplicación efectiva en la puerta de runtime.

## 7. Separación respecto de JALÓN 3

JALÓN 3 fija cómo medir y conservar evidencia.

JALÓN 4 fija **qué runtime puede entrar legítimamente en el plan de ejecución** según el contexto de despliegue.

```text
selección
   ↓
JALÓN 4 — compatibilidad
   ↓
runtime físico
   ↓
JALÓN 3 — medición/evidencia
```

## 8. Lo que queda fuera

- benchmark físico de cada runtime;
- comparación de rendimiento entre runtimes;
- instalación automática de runtimes;
- elección de un runtime por velocidad estimada;
- convertir datos de terceros en mediciones locales.

## 9. Criterio de cierre

JALÓN 4 podrá cerrarse cuando la validación en el host confirme que el flujo real respeta la taxonomía y las combinaciones incompatibles quedan bloqueadas sin intervención manual.

## 10. Próximo paso

**Ubuntu:** ejecutar únicamente la batería corta de JALÓN 4 y devolver el resultado resumido. No hay que rediseñar ni escribir código adicional antes de esa validación.
