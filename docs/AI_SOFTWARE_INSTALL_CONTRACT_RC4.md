# LEONES RC4 — contrato permanente de gestión de software IA

> **Regla normativa y extensible:** este contrato se aplica a **todo software IA que LEONES gestione**, tanto a los componentes actuales como a cualquier componente futuro que se incorpore al proyecto.
>
> Ningún instalador futuro puede limitarse a comprobar que existe un ejecutable. La operación `instalar` significa mantener el componente en un estado instalado, operativo y actualizado según su fuente upstream estable.

## Ciclo obligatorio de gestión

Para **cada** software IA gestionado por LEONES deben existir y verificarse estos cinco estados:

1. **Instalación desde cero**
   - Si el software no está instalado, LEONES debe instalarlo mediante su mecanismo soportado.
   - Al terminar, debe comprobar que el software quedó realmente disponible.

2. **Detección de instalación rota → reparación**
   - La mera presencia de un binario, wrapper, directorio o enlace no demuestra que la instalación sea válida.
   - LEONES debe comprobar que el componente puede ejecutarse y obtener su estado/versionado.
   - Si existe pero está roto o incompleto, `instalar` debe reparar la instalación.

3. **Detección de versión actual → no actualizar innecesariamente**
   - Si el componente está operativo, LEONES debe determinar su versión instalada.
   - Debe consultar la versión estable upstream correspondiente a ese componente.
   - Si instalada == última estable, **no debe reinstalar, actualizar ni ejecutar una operación de actualización innecesaria**.

4. **Versión antigua → actualización real**
   - Si la versión instalada es inferior a la última estable upstream, `instalar` debe ejecutar el mecanismo de actualización soportado por ese software.
   - La actualización debe ser real, no una simple revalidación.
   - Debe verificarse posteriormente que la nueva versión quedó instalada y operativa.

5. **Verificación operacional posterior**
   - Toda instalación, reparación o actualización termina únicamente después de verificar que el software está operativo.
   - Si la verificación falla, LEONES debe informar del fallo y devolver un estado de error; nunca debe declarar correctamente completada la operación.

## Regla de decisión

El comportamiento normativo de `instalar` es:

```text
                 ┌─ no instalado ───────────────→ INSTALAR
                 │
                 ├─ instalado pero roto ────────→ REPARAR
                 │
instalar ────────┼─ operativo + versión actual → NO ACTUALIZAR
                 │
                 └─ operativo + versión antigua → ACTUALIZAR
                                                        │
                                                        ↓
                                           VERIFICAR OPERATIVIDAD
```

## Requisitos para software futuro

Antes de incorporar un nuevo componente al instalador de LEONES, deben definirse explícitamente:

- método de instalación desde cero;
- criterio fiable para detectar que está instalado;
- criterio fiable para detectar que está operativo;
- comando o mecanismo para obtener la versión instalada;
- fuente upstream de la última versión estable;
- comparación de versiones adecuada al esquema utilizado por el proyecto upstream;
- mecanismo oficial o soportado de actualización;
- comprobación operacional final;
- comportamiento de error cuando cualquiera de esas comprobaciones no pueda realizarse.

No se acepta como implementación suficiente:

- `command -v <software>` como única prueba de instalación;
- reinstalar siempre que se solicite `instalar`;
- comparar contra una etiqueta que no represente la versión del software;
- declarar éxito sin una comprobación operacional final.

## Aplicación a los componentes actuales

El contrato se aplica actualmente a:

- FitLLM / LLMFit
- Osmantic ODS
- Magnitude
- Hermes
- Oh My Hermes (OMH)

Y se aplica automáticamente a **cualquier componente IA futuro** que LEONES incorpore al ciclo de instalación.

## Relación con CI y mantenimiento

Este contrato es parte de la arquitectura RC4. Cualquier nuevo instalador o modificación de un instalador existente debe conservar estas cinco garantías y añadir pruebas que cubran, como mínimo, los cinco estados anteriores.

Si una implementación concreta del upstream no permite alguno de los pasos directamente, el adaptador de LEONES debe resolver esa diferencia; no se debe eliminar la garantía del contrato.
