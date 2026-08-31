# RC2-L — Recorrido beta integrado

**Estado:** 🟢 Diseño fijado · integración en curso

El wizard RC2 presenta simultáneamente Español, English y 中文 y conduce al usuario por el recorrido completo sin convertir una decisión humana en autorización implícita.

```text
HARDWARE
   ↓
PERFIL + CANDIDATOS
   ↓
MODELO
   ↓
ODS / MAGNITUDE
   ↓
PLAN DE INSTALACIÓN
   ↓
CONSENTIMIENTO
   ↓
INSTALACIÓN + VERIFICACIÓN
   ↓
¿BENCHMARK?
   ├── NO → queda listo para uso
   └── SÍ → handoff RC1
                    ↓
              runtime → A01 → grader
                    ↓
              measured → evidence
```

La internacionalización afecta únicamente a la presentación; los contratos, identificadores técnicos, gates y métricas permanecen canónicos.

## Próximo bloque

Conectar el perfilado físico y la selección de candidatos al wizard, y después sustituir los adaptadores pendientes de instalación por integraciones reales verificables. Ubuntu solo será necesario cuando una prueba física no pueda sustituirse por CI, fixtures o revisión en GitHub.
