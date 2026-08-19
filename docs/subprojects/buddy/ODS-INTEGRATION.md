# Buddy ↔ ODS

## Decisión

**Integración recomendada: extensión/servicio aislado de ODS.** Buddy no debe convertirse en una modificación del núcleo de ODS.

ODS aporta infraestructura, modelos, almacenamiento/configuración y exposición de servicios; Buddy aporta el harness de asistencia personal y su memoria Git/Markdown.

## Arquitectura

```text
ODS
├── model/runtime backend
│       └── OpenAI-compatible endpoint
│
├── buddy service
│       ├── Node worker + Pi SDK
│       ├── permission layer
│       ├── session lifecycle
│       └── buddy workspace (Git + Markdown)
│
└── dashboard / service management
```

### Conexión de modelo

Buddy ya contempla un `baseUrl` para proveedores compatibles con OpenAI. Por tanto, el primer adaptador debe apuntar al endpoint de inferencia que ODS exponga, sin introducir otro servidor de inferencia dentro de Buddy.

Variables conceptuales:

```text
BUDDY_PROVIDER=custom
BUDDY_BASE_URL=<ODS model endpoint>
BUDDY_MODEL=<ODS selected model>
```

Los nombres finales de variables deben ajustarse al contrato real de ODS antes de implementar el instalador.

## Empaquetado

Propuesta:

```text
ODS extension: buddy
├── manifest
├── healthcheck
├── start/stop hooks
├── model endpoint configuration
├── workspace mount
└── permission policy
```

El workspace de Buddy debe persistir fuera del contenedor efímero:

```text
ODS persistent volume
└── buddy/
    ├── AGENTS.md
    ├── agent_brain/
    ├── user/
    └── logs/
```

## Seguridad

El aislamiento debe conservar la propiedad clave de Buddy: el agente no recibe Bash/shell por defecto. El filesystem debe exponerse mediante una raíz explícita y la capa de permisos por zonas.

No se debe dar a Buddy acceso al Docker socket ni a credenciales de ODS que no necesite.

## Integración con el dashboard

Fase 1: servicio instalable, healthcheck y configuración de modelo.  
Fase 2: botón de apertura/estado y configuración.  
Fase 3: trazas y métricas de evaluación exportables a LEONES.

## Pruebas de aceptación

1. ODS inicia Buddy sin duplicar el runtime de inferencia.
2. Buddy puede usar un modelo servido por ODS.
3. Reiniciar el servicio conserva el workspace.
4. El agente permanece sin shell salvo una política explícita futura.
5. Las trazas de sesión se pueden transformar al contrato LEONES.
6. Un fallo del servicio Buddy no derriba el resto de ODS.
