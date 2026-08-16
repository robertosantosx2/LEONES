# LEONES — Frontera entre web e infraestructura

**Decisión arquitectónica obligatoria — 2026-08-16**

## 1. Principio

La web de LEONES es una **interfaz de consulta, documentación y descubrimiento**.

La infraestructura de Atlas, prospección, ingestión, evaluación, recomendaciones, agentes y automatización es una **capa independiente**.

El usuario final no debe necesitar descargar el repositorio completo ni la infraestructura para consultar la web.

La única parte que la web debe facilitar para ejecución local son los **scripts, ejemplos, configuraciones y documentación necesarios para que el usuario pueda probar su propio LLM en local**.

## 2. Separación conceptual

```text
                         LEONES
                           │
             ┌─────────────┴─────────────┐
             │                           │
          WEB/UI                    INFRAESTRUCTURA
             │                           │
     documentación                  Atlas
     navegación                      ingestión
     resultados                      prospección
     diagramas                       evaluación
     estado                          recomendaciones
     descarga de scripts             agentes
             │                       automatización
             │                           │
             └────────── datos publicados ┘
                         / contratos
```

La web puede **leer y presentar resultados publicados**, pero no debe convertirse en el runtime de la infraestructura.

## 3. Qué pertenece a la web

Dentro de `web/` deben vivir exclusivamente elementos necesarios para publicar la interfaz:

- HTML.
- CSS.
- JavaScript de interfaz.
- SVG, iconos y recursos visuales.
- Datos ligeros necesarios para renderizar páginas públicas.
- Documentación específica presentada al usuario.
- Enlaces a recursos descargables.

La web no debe incorporar:

- credenciales;
- secretos;
- runners de GitHub Actions;
- código de scraping operativo salvo que sea material explícitamente descargable;
- bases de datos de desarrollo completas;
- dependencias de Python/Node necesarias para ejecutar Atlas;
- artefactos de entrenamiento;
- modelos LLM;
- grandes datasets internos;
- lógica de infraestructura que no sea necesaria para la interfaz.

## 4. Qué pertenece a infraestructura

Fuera de `web/` deben mantenerse:

- Atlas y sus pipelines.
- Ingestión.
- Prospección diaria.
- Extracción de fuentes.
- Evaluación.
- Recomendador.
- Agentes.
- Automatizaciones.
- Workflows de GitHub Actions.
- Bases de datos operativas.
- Procesamiento de NDJSON/CSV/SQLite.
- Herramientas de mantenimiento.
- Jobs y runners.

La infraestructura puede generar **artefactos públicos de salida** para que la web los consuma, pero no debe importar código de la web para funcionar.

## 5. Dirección de las dependencias

La dependencia debe ser unidireccional:

```text
infraestructura
      │
      │ genera / publica
      ▼
artefactos públicos
      │
      ▼
     web
      │
      │ enlaza / descarga
      ▼
 scripts locales del usuario
```

Nunca:

```text
web → infraestructura operativa → web
```

La web no debe necesitar ejecutar un pipeline para poder mostrarse.

## 6. Scripts descargables

Los scripts que el usuario pueda ejecutar para probar su propio LLM constituyen una categoría especial: **producto de usuario**, no infraestructura web.

Deben estar en una ubicación claramente separada y documentada, por ejemplo:

```text
scripts/
└── local/
    ├── README.md
    ├── requirements.txt
    ├── examples/
    └── ...
```

La web sólo debe enlazarlos.

Cada paquete descargable debe explicar:

1. qué prueba;
2. qué hardware necesita;
3. qué software necesita;
4. qué modelo puede utilizar;
5. cómo instalarlo;
6. cómo ejecutarlo;
7. qué resultado produce;
8. cómo interpretar el resultado;
9. qué datos se envían o no se envían fuera del equipo.

## 7. Web sin infraestructura

La web debe poder publicarse y funcionar aunque los pipelines estén temporalmente detenidos.

Por tanto:

- una página no debe ejecutar Atlas para renderizarse;
- una página no debe depender de una base de datos operativa local;
- una página no debe requerir Python;
- una página no debe requerir Node.js en el navegador;
- una página no debe depender de GitHub Actions en tiempo de navegación.

Los datos dinámicos deben llegar como **artefactos publicados**, cuando sean necesarios.

## 8. Automatización

Los workflows pueden seguir generando contenido para la web, pero la frontera debe quedar explícita:

```text
Workflow
   ↓
proceso de infraestructura
   ↓
artefacto público/versionado
   ↓
publicación
   ↓
web
```

El workflow no debe introducir directamente lógica de presentación en cada página.

## 9. Publicación

La web se considera un artefacto desplegable independiente.

El objetivo es que una futura migración de infraestructura no obligue a reescribir la interfaz y que una modificación visual no pueda romper Atlas.

## 10. Regla para nuevos ficheros

Antes de añadir un fichero hay que responder:

> ¿Es necesario para que una persona consulte la web o para que pueda descargar/probar localmente un LLM?

Si la respuesta es **sí**, puede pertenecer al producto público correspondiente.

Si la respuesta es **no** y sirve para ejecutar, mantener, ingerir, evaluar o automatizar LEONES, debe permanecer fuera de `web/`.

## 11. Decisión congelada

Esta separación pasa a formar parte del marco de arquitectura web de LEONES.

Cualquier excepción debe documentarse antes de incorporarse y explicar:

- por qué necesita romper la frontera;
- qué dependencia introduce;
- cómo se evita convertirla en una dependencia permanente;
- cómo se prueba de forma independiente.
