# RC2-M — Puente de perfilado de hardware

**Estado:** 🟢 Contrato fijado · implementación física pendiente

RC2 necesita convertir el hardware declarado/detectado en un perfil canónico que pueda alimentar la selección de modelos. Esta capa no inventa mediciones: conserva `unknown`/`null` cuando el dato no está disponible.

## Fuente de decisión

LEONES utilizará **LLMFit como referencia de ajuste hardware→modelo**, no creará un catálogo paralelo de compatibilidad. El resultado que consuma RC2 debe conservar el vínculo con la fuente y su versión/revisión cuando estén disponibles.

ODS y Magnitude no sustituyen esta función. Sus adaptadores actuales son límites de integración y preparación de ejecución: ODS valida y prepara un `ExecutionSpec` local; Magnitude prepara metadatos para el modo agente. fileciteturn89file0L1-L7 fileciteturn90file0L1-L7

## Perfil mínimo

```text
CPU
RAM
GPU
VRAM
OS
arquitectura
aceleradores
fuente del perfil
versión/revisión de la fuente
```

## Flujo RC2-M

```text
DECLARACIÓN DEL USUARIO
        ↓
DETECCIÓN LOCAL
        ↓
LLMFIT / FUENTE DE AJUSTE
        ↓
PERFIL CANÓNICO
        ↓
CANDIDATOS
        ↓
USUARIO ELIGE
```

La declaración del usuario no debe ser presentada como medición física si no ha sido verificada. Cuando haya discrepancia entre declaración y detección, se conserva la discrepancia y se solicita confirmación.

## Siguiente implementación

Crear el adaptador de perfilado y el normalizador de candidatos, primero con fixtures reproducibles y tests. La prueba física se hará después en Ubuntu, únicamente para validar detección real y el comportamiento del instalador/runtime sobre hardware real.
