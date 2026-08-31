# RC2-I — Installation consent and verification

**Estado:** 🟢 Contrato fijado

RC2-I conecta la elección de ODS/Magnitude con una instalación explícitamente autorizada. La selección nunca instala por sorpresa.

## Flujo

```text
STACK_SELECTED
      ↓
INSTALL_PLAN_READY
      ↓
┌─────────────────────────────────────────────┐
│ LEONES explica qué instalará                 │
│ • componentes                               │
│ • versión/ref                              │
│ • espacio requerido si se conoce            │
│ • red/descargas                             │
│ • permisos                                  │
│ • cambios locales                            │
│ • opción de cancelar                         │
└──────────────────────┬──────────────────────┘
                       ↓
              ¿AUTORIZAR INSTALACIÓN?
                 /              \
               NO               SÍ
               ↓                 ↓
        INSTALL_DECLINED   INSTALL_AUTHORIZED
                                  ↓
                              INSTALL
                                  ↓
                              VERIFY
                         /              \
                       OK              ERROR
                       ↓                 ↓
          READY_FOR_BENCHMARK       BLOCKED
```

## Reglas

1. La instalación requiere consentimiento específico.
2. El consentimiento debe identificar el stack y el plan que se va a ejecutar.
3. Un consentimiento anterior no autoriza automáticamente una instalación diferente.
4. Cancelar no se considera error.
5. La instalación debe ser idempotente cuando el componente ya esté verificado.
6. Verificación separada: instalar no equivale a estar listo.
7. Ningún benchmark queda autorizado por instalar correctamente.
8. Los secretos y credenciales no se solicitan salvo que un componente los requiera y el usuario lo haya aceptado expresamente.

## Estados canónicos

- `INSTALL_PLAN_READY`
- `INSTALL_CONSENT_REQUIRED`
- `INSTALL_DECLINED`
- `INSTALL_AUTHORIZED`
- `INSTALLING`
- `INSTALL_VERIFIED`
- `INSTALL_FAILED`
- `READY_FOR_BENCHMARK`

## Integración

El instalador será un adaptador con efectos laterales. El wizard presenta y solicita consentimiento; el adaptador ejecuta. La sesión conserva el resultado y los detalles de verificación.

RC2-I no redefine los contratos de ODS/Magnitude ni el runner RC1.
