# Política de licencias de la prospección LEONES

## Criterio principal

La **licencia es el primer filtro de la prospección**.

El bot de Prospector busca diariamente piezas, proyectos, software, runtimes, herramientas, agentes, benchmarks, componentes relacionados con hardware y modelos/repositorios de modelos que puedan ser relevantes para ejecutar IA localmente. Pero un candidato **solo entra en el conjunto de hallazgos públicos de prospección cuando su licencia declarada por GitHub corresponde a una licencia aprobada por la Open Source Initiative (OSI)**.

Fuente canónica de la lista de licencias aprobadas:

https://opensource.org/Licenses

La página de OSI identifica las licencias aprobadas y sus identificadores SPDX. OSI explica que una licencia open source debe cumplir la Open Source Definition y pasar por su proceso de revisión. citehttps://opensource.org/Licenses

## Dos niveles dentro del criterio OSI

### 1. Universo OSI: criterio de entrada

Se contemplan **todas las licencias aprobadas por OSI**, no únicamente las licencias Copyleft.

Por tanto, una licencia OSI aprobada puede aparecer en Prospección aunque sea permisiva, recíproca, de propósito especial, histórica/superseded o esté incluida en otra categoría de OSI. La clasificación de OSI se conserva como información de contexto y no se sustituye por una puntuación propia de LEONES.

### 2. Copyleft prioritario: criterio de destaque

Dentro del universo OSI, LEONES destaca especialmente estas cinco licencias:

- `GPL-2.0`
- `GPL-3.0`
- `AGPL-3.0`
- `LGPL-2.1`
- `LGPL-3.0`

En la web se representan con **fondo verde** para que el visitante pueda reconocer inmediatamente los hallazgos que pertenecen a este grupo prioritario.

> Verde significa **"licencia Copyleft prioritaria de LEONES"**. No significa por sí mismo que el proyecto esté validado, sea técnicamente mejor ni que deba incorporarse a la pila.

## Qué hace el bot

El script `scripts/discover_copyleft.py` sigue este orden:

```text
FUENTES / GITHUB
       ↓
DESCUBRIR MODELOS, PROYECTOS, SOFTWARE, RUNTIMES,
AGENTS, HERRAMIENTAS, BENCHMARKS Y COMPONENTES
       ↓
OBTENER SPDX DECLARADO POR GITHUB
       ↓
COMPARAR CON LA LISTA ACTUAL DE OSI
       ↓
¿OSI APROBADA?
   ├── NO / UNVERIFIED → fuera del conjunto público de hallazgos
   └── SÍ
        ↓
   HALLAZGO DE PROSPECCIÓN
        ↓
   ¿GPL-2.0 / GPL-3.0 / AGPL-3.0 /
      LGPL-2.1 / LGPL-3.0?
        ├── SÍ → destacar en verde
        └── NO → mostrar como OSI aprobado normal
        ↓
REVISIÓN TÉCNICA
        ↓
EVIDENCIA
        ↓
ATLAS / ROUTER, SI PROCEDE
```

El universo de licencias OSI se obtiene de la página de OSI en cada ejecución. Así el bot no depende de una lista cerrada que pueda quedar obsoleta si OSI modifica su catálogo.

## Licencia declarada frente a licencia verificada

El filtro de prospección utiliza el **SPDX que GitHub declara para el repositorio**. Esto es un criterio de descubrimiento, no una auditoría jurídica.

Un proyecto con licencia ausente, `UNVERIFIED`, una licencia propietaria o una licencia que no aparezca en el catálogo OSI **no pasa el filtro primario**.

La licencia puede cambiar y un repositorio puede contener componentes con licencias diferentes. Por eso la fase posterior de revisión debe comprobar el repositorio y, cuando corresponda, sus archivos de licencia y dependencias.

## Qué NO significa el filtro

El filtro OSI no significa:

- que el proyecto sea adecuado para hardware de consumo;
- que sea seguro;
- que esté activo;
- que sea reproducible;
- que tenga una arquitectura útil para LEONES;
- que el modelo tenga pesos realmente abiertos bajo la misma licencia;
- que las dependencias tengan licencias compatibles;
- que LEONES lo recomiende.

La licencia es el **primer criterio**, no el último.

## Por qué es el criterio principal

LEONES quiere construir un ecosistema que pueda estudiarse, ejecutarse, modificarse y reproducirse localmente. Por ello la procedencia y las condiciones de reutilización del software no pueden ser un dato secundario añadido después de descubrir candidatos.

La prospección debe empezar por un universo jurídicamente identificable: **OSI aprobado → después relevancia técnica → después evidencia → después recomendación**.

Esto evita presentar como equivalentes:

- software realmente Open Source bajo una licencia OSI;
- proyectos con licencia desconocida;
- repositorios sin licencia;
- software source-available con restricciones no aprobadas por OSI;
- modelos cuyos términos de uso no permiten las libertades esperadas.

## Estado del candidato

La clasificación recomendada es:

| Estado | Significado |
|---|---|
| `OSI-approved` | Licencia declarada coincide con una licencia aprobada por OSI. Pasa el filtro primario. |
| `priority-copyleft` | Además, usa una de las cinco licencias Copyleft prioritarias de LEONES. Se destaca en verde. |
| `external-unvalidated` | Candidato descubierto fuera del filtro o pendiente de comprobación. No entra en el conjunto principal de Prospección. |
| `evidence` | Ya existe revisión/evidencia suficiente para continuar el proceso de conocimiento. |

## Regla para la web

En cualquier tabla o tarjeta generada automáticamente por Prospección:

- licencia OSI aprobada → mostrar la licencia y la marca `OSI`;
- una de las cinco licencias prioritarias → **fondo verde**;
- licencia no OSI o desconocida → no presentarla como hallazgo OSI aprobado.

La presentación visual nunca sustituye al dato SPDX.

## Fuente

Open Source Initiative — **OSI Approved Licenses**:

https://opensource.org/Licenses
