# Prospección LEONES

## Objetivo

La prospección de LEONES es un proceso **diario** para descubrir piezas, proyectos, software, modelos, runtimes, agentes, herramientas, benchmarks, técnicas de eficiencia y componentes relacionados con hardware que puedan mejorar la IA local en hardware de consumo.

El criterio principal no es una puntuación propia: **la licencia OSI es la puerta de entrada**.

## Criterio principal: licencia OSI

El bot busca primero un universo amplio de candidatos técnicos y después aplica el filtro de licencia.

Un candidato entra en el conjunto principal de prospección únicamente cuando la licencia SPDX declarada por GitHub aparece en el catálogo actual de **licencias aprobadas por la Open Source Initiative (OSI)**:

https://opensource.org/Licenses

Esto incluye todo el universo OSI, no solo Copyleft.

### Copyleft prioritario

Dentro de las licencias OSI aprobadas, LEONES destaca:

- `GPL-2.0`
- `GPL-3.0`
- `AGPL-3.0`
- `LGPL-2.1`
- `LGPL-3.0`

En la web estos cinco identificadores se muestran con **fondo verde**.

> El fondo verde significa «Copyleft prioritario de LEONES». No significa aprobación técnica.

## Flujo

```text
DESCUBRIR MODELOS / PROYECTOS / SOFTWARE / PIEZAS
                    ↓
             LICENCIA SPDX
                    ↓
          ¿OSI APROBADA?
             ↙           ↘
           NO             SÍ
           ↓              ↓
       DESCARTAR       PROSPECCIÓN
                          ↓
              ¿COPyleft PRIORITARIO?
                   ↓             ↓
                 VERDE          NORMAL
                          ↓
                    REVISIÓN TÉCNICA
                          ↓
                       EVIDENCIA
                          ↓
                    ATLAS / ROUTER
```

La lista OSI se consulta en cada ejecución del bot para evitar depender de una lista estática que pueda quedar obsoleta.

## Descubrimiento diario

Preguntas que debe cubrir el bot:

- ¿Qué modelos o repositorios de modelos han aparecido?
- ¿Qué runtimes de inferencia local son relevantes?
- ¿Qué agentes y harnesses nuevos existen?
- ¿Qué herramientas permiten trabajar con archivos, Git, búsqueda, memoria o código?
- ¿Qué técnicas o herramientas mejoran la eficiencia?
- ¿Qué benchmarks permiten medir mejor el comportamiento real?
- ¿Qué proyectos permiten aprovechar mejor hardware de consumo?
- ¿Qué piezas pueden integrarse en la pila LEONES?

La búsqueda técnica es amplia; el filtro OSI determina qué candidatos entran en el conjunto principal.

## Prospección y recomendación

El descubrimiento no implica recomendación automática.

Cada candidato OSI aprobado debe pasar posteriormente por:

1. actividad y mantenimiento;
2. arquitectura;
3. compatibilidad con hardware de consumo;
4. compatibilidad con Debian, Ubuntu o RHEL cuando proceda;
5. dependencias;
6. reproducibilidad;
7. seguridad;
8. utilidad para una tarea concreta;
9. evidencia disponible.

La secuencia es:

```text
OSI aprobado
    ↓
relevancia técnica
    ↓
compatibilidad
    ↓
evidencia
    ↓
recomendación
```

## Licencia declarada frente a licencia verificada

El filtro utiliza el SPDX declarado por GitHub. Es un criterio de descubrimiento y **no sustituye una revisión jurídica del repositorio completo**.

Un proyecto sin licencia identificable, con licencia propietaria o con una licencia que no figure como aprobada por OSI no debe presentarse como hallazgo OSI aprobado.

Los modelos requieren además una revisión específica de sus términos de uso, porque la licencia del repositorio o del código de inferencia no demuestra por sí sola las condiciones aplicables a los pesos del modelo.

## Qué debe contener una recomendación

Una recomendación debe indicar como mínimo:

1. qué mejora;
2. qué componente de la pila afecta;
3. qué licencia SPDX tiene;
4. si es OSI aprobado;
5. si pertenece al grupo Copyleft prioritario;
6. qué requisitos de hardware añade;
7. qué dependencias introduce;
8. qué versiones son compatibles;
9. qué evidencia existe;
10. cómo instalarlo;
11. cómo revertirlo.

## Regla de evidencia

Prospector **descubre; no valida**.

Un hallazgo debe poder evolucionar por estados:

```text
OSI-approved
      ↓
external-unvalidated
      ↓
revisión
      ↓
evidence
      ↓
Atlas
      ↓
Router
```

La licencia OSI es necesaria para entrar en el conjunto principal de prospección, pero no suficiente para recomendar un componente.

## Documentación relacionada

- `docs/PROSPECTION_LICENSE_POLICY.md` — política completa de licencias.
- `scripts/discover_copyleft.py` — bot diario de descubrimiento.
- `web/data/prospeccion.json` — datos consumidos por la web.
- `web/prospeccion.html` — presentación pública de los hallazgos.
