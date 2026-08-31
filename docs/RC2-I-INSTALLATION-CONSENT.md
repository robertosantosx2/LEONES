# RC2-I — Installation consent and verification

**Estado:** 🟢 Contrato fijado

RC2-I conecta la elección de ODS/Magnitude con una instalación explícitamente autorizada. La selección nunca instala por sorpresa.

## Antes de instalar

LEONES debe presentar un resumen verificable del plan que se ejecutará:

- modelo y variante seleccionados;
- stack seleccionado;
- componentes/acciones;
- versión o referencia cuando se conozca;
- almacenamiento previsto cuando se conozca;
- uso de red y descargas;
- permisos requeridos;
- cambios locales;
- información que permanecerá local;
- opción de cancelar.

Todo dato desconocido se presenta como desconocido/null; nunca se inventa.

## Flujo

```text
STACK_SELECTED
      ↓
INSTALL_PLAN_READY
      ↓
┌─────────────────────────────────────────────┐
│ LEONES explica el plan                      │
└──────────────────────┬──────────────────────┘
                       ↓
              ¿AUTORIZAR INSTALACIÓN?
                 /              \
               NO               SÍ
               ↓                 ↓
        INSTALL_DECLINED   INSTALL_AUTHORIZED
                                  ↓
                              INSTALLING
                                  ↓
                              VERIFY
                         /              \
                       OK              ERROR
                       ↓                 ↓
          READY_FOR_BENCHMARK       BLOCKED
```

## Consentimiento

El consentimiento debe identificar el stack y el plan. Un consentimiento anterior no autoriza una instalación diferente. Cancelar no es un error.

El contrato de persistencia es `schemas/rc2-install-consent.v1.json`.

## Instalación y verificación

El instalador es el único componente autorizado a producir efectos laterales. Debe ser idempotente cuando sea posible. Si el componente ya está correctamente instalado y verificado, no debe modificarse innecesariamente.

La verificación es independiente de la instalación. Solo una verificación satisfactoria puede producir `READY_FOR_BENCHMARK`.

**Instalar correctamente no autoriza ningún benchmark.** El consentimiento de benchmark sigue gobernado por RC2-F.

## Seguridad

No se aceptan comandos ocultos ni acciones fuera del plan autorizado. Los secretos y credenciales no se imprimen ni se incorporan a la evidencia.

## Integración

RC2-I consume `stack_selection`, genera un plan y persiste su consentimiento/resultado en la sesión RC2-G. Después entrega el control al gate de benchmark y al pipeline de ejecución/evidencia validado en RC1.

RC2-I no redefine los contratos de ODS/Magnitude ni el runner RC1.
