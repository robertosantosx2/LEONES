# Buddy ↔ Magnitude

## Decisión

**No integrar Buddy dentro del núcleo del runtime de Magnitude.** La integración correcta es como harness/cliente alternativo que puede consumir el mismo backend de modelo y, cuando sea útil, el mismo hardware profile.

Magnitude y Buddy tienen responsabilidades distintas:

- Buddy: asistente personal, memoria persistente local, file-first tools, UX Tauri.
- Magnitude: agente/coding runtime e infraestructura de inferencia/ejecución.

## Arquitectura

```text
                 LEONES task
                     │
             Harness adapter
               /           \
          Buddy             Magnitude
            │                  │
            └───────┬──────────┘
                    │
              common model API
                    │
             inference backend
```

## Dos modos

### A. Modo benchmark

Magnitude y Buddy reciben:

- mismo modelo;
- misma configuración de decodificación cuando sea compatible;
- mismo hardware;
- mismo prompt/tarea;
- mismo presupuesto temporal;
- mismas reglas de evaluación.

LEONES recoge la traza normalizada y compara resultado, trayectoria, tiempo/coste y seguridad.

### B. Modo integración de plataforma

Buddy puede utilizar un endpoint de inferencia gestionado por Magnitude cuando éste exponga una API compatible. La integración debe ser externa y configurable; no se debe enlazar Buddy contra módulos privados del runtime de Magnitude.

## Adaptador LEONES

El adaptador debe traducir:

```text
Buddy session/logs/events
        ↓
LEONES HarnessEvent
        ↓
benchmark result
```

El log Markdown de Buddy no debe ser la única fuente de telemetría de benchmark: se generará una traza estructurada durante la ejecución para evitar reconstrucciones ambiguas.

## Qué no hacer

- No copiar Pi SDK dentro de Magnitude.
- No modificar el agente de Magnitude para emular Buddy.
- No compartir el workspace de memoria de Buddy con el workspace de código de Magnitude.
- No conceder shell a Buddy sólo para conseguir paridad funcional.

## Pruebas de aceptación

1. Una tarea LEONES puede ejecutarse en Buddy y Magnitude con el mismo modelo.
2. Se conserva la separación de workspaces.
3. La traza de ambos se normaliza al mismo contrato.
4. Se puede calcular éxito, pasos, herramientas, tiempo y coste.
5. Se registran fallos y recuperaciones.
6. Las pruebas de seguridad distinguen capacidades disponibles en cada harness.
