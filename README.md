# LEONES

## Estado del proyecto

| Bloque | Estado | Resultado |
|---|---|---|
| V1 / A01 | 🟢 Cerrado | Cadena real de selección → ejecución → benchmark → evidencia |
| JALÓN 1 | 🟢 Cerrado | Base CI y contratos iniciales |
| JALÓN 2 | 🟢 Cerrado | Ejecución física + evidencia reproducible con llama.cpp |
| JALÓN 3 | 🟢 Cerrado | Contrato de medición real + auditoría física |
| JALÓN 4 | 🟢 **Cerrado** | Metodología AA + contratos de integración + benchmark de tareas + tiers |
| RC1 | 🟢 **Validado** | Ejecución efectiva end-to-end |
| RC2 | 🟡 **En validación física** | Orquestación beta, instalación y piloto externo |
| **RC3** | 🟢 **Arquitectura fijada** | **Hermes-first discovery → elección de usuario → Magnitude/ODS → medición LEONES** |

## RC3 — arquitectura canónica

RC3 retira LLMFit/FitLLM del camino canónico. **Hermes es ahora el bootstrap de descubrimiento de hardware y fit inicial de modelos.** LEONES normaliza el resultado y conserva la autoridad sobre verificación física, ejecución, medición y evidencia.

```text
                         HERMES
                 discovery + initial fit
                           ↓
                  hardware-profile.v1
                           ↓
                    LEONES normalize
                           ↓
                  candidate-set.v1
                           ↓
                ┌──────────┴──────────┐
                ↓                     ↓
           MAGNITUDE                  ODS
        profiling/tuning         install/stack
                ↓                     ↓
                └──────────┬──────────┘
                           ↓
                    selected runtime
                           ↓
                      LEONES tasks
                           ↓
                    real measurement
                           ↓
                       evidence
                           ↓
                     recommendation
```

### Regla de autoridad

**Hermes descubre. El usuario elige. Magnitude u ODS ejecutan/optimizan. LEONES verifica, mide y sentencia.**

Hermes puede detectar hardware, valorar memoria/fit y seleccionar una configuración local compatible. Su resultado es una preselección externa, no una medición LEONES. La documentación oficial de Hermes confirma que su flujo Local Models gestiona `llama.cpp`, selecciona builds según hardware y comprueba fit de memoria/contexto antes de descargar. citeturn19file0L2-L2

### FitLLM / LLMFit

FitLLM/LLMFit queda **fuera de RC3**: no es dependencia dura, no se instala y no participa en el flujo canónico. Se conserva como conocimiento y posible proveedor externo futuro, pero separado de la ejecución RC3.

### Handoff de usuario

Después del descubrimiento y de la selección del modelo/configuración, el usuario elige explícitamente:

- **Magnitude** → perfilado, estimación, tuning y ejecución mediante su interfaz canónica.
- **ODS** → instalación y stack local mediante su interfaz canónica.

LEONES no crea instaladores alternativos ni duplica los runtimes.

## Instalación mínima

Para RC3, el orden conceptual es:

```text
INSTALAR LEONES
      ↓
VERIFICAR / INSTALAR HERMES
      ↓
HERMES DESCUBRE HARDWARE
      ↓
LEONES REGISTRA Y NORMALIZA
      ↓
ELEGIR MODELO / CONFIGURACIÓN
      ↓
ELEGIR MAGNITUDE U ODS
      ↓
CONSENTIMIENTO
      ↓
INSTALAR / PREPARAR
      ↓
VERIFICAR FÍSICAMENTE
      ↓
TAREAS LEONES
      ↓
MEDIR
      ↓
EVIDENCIA
```

El detalle contractual está en [docs/RC3-ARCHITECTURE.md](docs/RC3-ARCHITECTURE.md).

## RC2

RC2 permanece como línea histórica y de validación física. Su documentación conserva la integración LLMFit utilizada en esa release, pero **RC3 la reemplaza en el camino canónico**.

La regla de distribución de RC3 es deliberadamente pequeña: LEONES + Hermes como bootstrap; Magnitude u ODS sólo cuando el usuario los seleccione.
