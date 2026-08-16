# LEONES — Router y cuadro de mandos

## Estado

**🟢 Contrato funcional cerrado · implementación UI pendiente**

El Router de LEONES debe disponer de un **cuadro de mandos para el usuario**. LEONES proporciona valores predefinidos razonables, pero el usuario puede afinarlos cuando quiera.

## Principio

```text
PERFIL DEL USUARIO
       ↓
PRESETS LEONES
       ↓
CUADRO DE MANDOS
       ↓
PREFERENCIAS AFINADAS
       ↓
EVIDENCIA + RESTRICCIONES
       ↓
ROUTER
       ↓
RECOMENDACIÓN EXPLICABLE
```

Los valores del usuario son preferencias/objetivos, no una licencia para saltarse gates de evidencia, OSI, compatibilidad o seguridad.

## Parámetros configurables

El cuadro de mandos debe permitir ajustar, como mínimo:

### Rendimiento

- prioridad de latencia;
- prioridad de tokens/s;
- umbral mínimo de velocidad;
- objetivo de tiempo de respuesta;
- modo `CABE` (1–<10 tok/s);
- modo `RULA` (10–100 tok/s);
- tolerancia a velocidades superiores.

### Calidad

- calidad/resolución de la tarea;
- prioridad de benchmarks relevantes;
- prioridad de razonamiento/coding/visión/uso general;
- tolerancia a modelos sin evidencia empírica propia.

### Hardware

- CPU disponible;
- RAM disponible;
- GPU disponible;
- VRAM disponible;
- uso CPU-only permitido;
- consumo/temperatura cuando exista evidencia.

### Agentic

- agente/harness preferido;
- herramientas permitidas;
- MCP permitido;
- memoria requerida;
- autonomía requerida;
- sandbox requerido;
- recuperación ante errores requerida.

### Apertura y política

- requisito de OSI;
- prioridad de Copyleft/permisividad según la política de LEONES;
- exclusión de componentes no verificados;
- restricciones de privacidad/ejecución local.

### Economía

- presupuesto máximo;
- coste por ejecución/token cuando exista evidencia;
- prioridad rendimiento/precio;
- prioridad TCO.

## Presets LEONES

El usuario no tiene que configurar nada para empezar. El Router debe ofrecer presets como punto de partida:

| Preset | Objetivo |
|---|---|
| **Equilibrado LEONES** | equilibrio entre calidad, velocidad, apertura y coste |
| **Máxima velocidad** | minimizar latencia y maximizar tok/s |
| **CABE** | priorizar configuraciones entre 1 y <10 tok/s |
| **RULA** | priorizar configuraciones entre 10 y 100 tok/s |
| **Calidad** | priorizar capacidad aunque aumente latencia |
| **Local / privado** | ejecución local y restricciones de privacidad |
| **Open Source** | máxima prioridad a elegibilidad OSI y trazabilidad |
| **Económico** | maximizar valor por coste |
| **Agentic** | priorizar capacidad de herramientas y autonomía |

Los presets son **valores iniciales**, no restricciones permanentes.

## Interacción recomendada

El usuario debe poder:

1. elegir un preset;
2. ver sus valores;
3. modificar sliders/selectores;
4. guardar preferencias;
5. restaurar valores LEONES;
6. comparar la configuración personalizada con el preset;
7. ejecutar una recomendación;
8. ver por qué un candidato ganó o quedó excluido.

## Explicabilidad

Cada resultado debe mostrar al menos:

```text
RECOMENDADO
¿Por qué?
¿Qué preferencias pesaron?
¿Qué restricciones se aplicaron?
¿Qué candidatos fueron excluidos y por qué?
¿Qué evidencia respalda la decisión?
¿Qué parte procede de preferencia del usuario?
```

El Router no debe ocultar una exclusión detrás de una puntuación única.

## Pesos y restricciones

La interfaz debe distinguir:

- **restricciones duras**: si no se cumplen, el candidato queda fuera;
- **preferencias blandas**: afectan al ranking;
- **evidencia**: determina qué afirmaciones pueden utilizarse;
- **políticas**: OSI, privacidad, seguridad y otras reglas del sistema.

Ejemplo:

```text
VRAM < requisito mínimo → EXCLUIR
OSI_UNKNOWN              → EXCLUIR del Atlas verificable
latencia preferida       → penalizar
precio preferido         → ponderar
coding benchmark         → ponderar si la tarea es coding
```

## Regla de seguridad del Router

El usuario puede afinar preferencias, pero **no puede usar el cuadro de mandos para saltarse una restricción obligatoria de LEONES**.

```text
usuario puede cambiar preferencias
             ↓
usuario NO puede cambiar
OSI / evidencia / seguridad / identidad
```

## Persistencia

Las preferencias de usuario deben mantenerse separadas de los valores oficiales de LEONES:

```text
LEONES_DEFAULTS
      +
USER_PREFERENCES
      ↓
EFFECTIVE_PROFILE
```

Nunca se sobrescriben los defaults globales cuando un usuario personaliza su perfil.

## No concurrencia

Los workflows que escriban perfiles, presets o resultados canónicos deben utilizar exclusivamente `leones-main-writers` y `cancel-in-progress: false`.

## Criterio de cierre

El contrato funcional del Router y su cuadro de mandos queda cerrado. La implementación visual y la integración con el motor de recomendación quedan como trabajo posterior.
