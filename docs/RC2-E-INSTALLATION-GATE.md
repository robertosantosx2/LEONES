# RC2-E — Installation Gate and Preparation Contract

**Estado:** 🟢 Contrato fijado

## Objetivo

RC2-E convierte la elección explícita de modelo + stack en un **plan de instalación declarativo y verificable**. No ejecuta instalaciones por sí mismo hasta que el usuario haya dado consentimiento explícito.

## Flujo

```text
modelo elegido
    ↓
stack elegido (ODS | Magnitude)
    ↓
installation plan
    ↓
preflight
    ↓
consentimiento explícito
    ↓
instalador oficial/adaptador del stack
    ↓
verification
    ↓
READY_FOR_BENCHMARK
```

## Reglas canónicas

1. LEONES no implementa un instalador alternativo de ODS ni de Magnitude.
2. Cada stack debe declarar sus requisitos, componentes, comandos/adaptadores y método de verificación.
3. Ninguna acción con efectos laterales se ejecuta durante la generación del plan.
4. La instalación requiere consentimiento explícito del usuario.
5. El plan conserva modelo, cuantización, stack, versión/ref, plataforma y procedencia.
6. Si un requisito no puede verificarse, el estado es `unknown` o `blocked`, nunca `ready` por inferencia.
7. Una instalación correcta no implica que el benchmark se ejecute automáticamente.
8. `READY_FOR_BENCHMARK` significa únicamente que el stack elegido ha superado sus comprobaciones de instalación.

## Estados

- `PLAN_READY`: plan construido, sin efectos laterales.
- `PREFLIGHT_REQUIRED`: faltan comprobaciones locales.
- `CONSENT_REQUIRED`: el plan está listo pero requiere autorización humana.
- `INSTALLING`: instalación en curso.
- `INSTALLED`: instalación finalizada.
- `VERIFICATION_FAILED`: la instalación no puede declararse válida.
- `READY_FOR_BENCHMARK`: instalación y verificación correctas.
- `BLOCKED`: no es seguro o posible continuar.

## Separación de responsabilidades

| Capa | Responsabilidad |
|---|---|
| LLMFit | hardware y fit de modelos |
| LEONES | decisión, plan, consentimiento y evidencia |
| ODS | instalación/preparación de ODS mediante su mecanismo soportado |
| Magnitude | instalación/preparación de Magnitude mediante su mecanismo soportado |
| Runtime | ejecución |
| Benchmark LEONES | medición de tareas |

## Seguridad y privacidad

Antes de instalar se debe informar de cualquier descarga, modificación del entorno, almacenamiento utilizado, acceso de red y credenciales/permisos requeridos. LEONES no debe enviar resultados a servicios externos por defecto.

## Resultado de RC2-E

El resultado de instalación debe ser distinguible de una medición de rendimiento. El contrato de benchmark solo puede activarse después de `READY_FOR_BENCHMARK` y de una decisión separada del usuario de ejecutar benchmark.
