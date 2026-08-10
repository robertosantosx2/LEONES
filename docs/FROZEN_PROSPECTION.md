# LOAS — Decisión congelada: Prospección semanal de harnesses

**Estado: CONGELADA**

## Regla

LOAS tendrá un nivel permanente de **prospección semanal** dedicado a descubrir proyectos y componentes que mejoren las **skills, funciones o características de los harnesses** de la pila.

El resultado de esta prospección alimentará un **menú de recomendaciones personalizado** para cada usuario.

> **LOAS prospecta semanalmente, cruza los candidatos con la pila del usuario y recomienda mejoras instalables; el usuario decide y después RULA verifica.**

## Qué se prospecta

Especial atención a:

- skills;
- tools y adapters;
- navegación y búsqueda;
- Git/GitHub;
- coding;
- ejecución de código;
- archivos;
- memoria y recuperación de contexto;
- planificación;
- subagentes;
- observabilidad;
- evaluación;
- recuperación ante errores;
- seguridad y sandboxing;
- automatización;
- conectores;
- nuevas capacidades del harness;
- mejoras de UX;
- componentes que permitan hacer más con el mismo hardware.

## Recomendación personalizada

LOAS no mostrará simplemente una lista genérica de novedades. Cada candidato se cruzará con:

```text
hardware
+ sistema operativo
+ harness
+ versión
+ modelo
+ backend
+ memoria disponible
        ↓
compatibilidad
        ↓
recomendación
```

La recomendación debe indicar como mínimo qué mejora, qué harness afecta, compatibilidad, licencia, si es Copyleft, requisitos de hardware, dependencias, impacto esperado en UX, instalación, reversibilidad y evidencia disponible.

## Estados

Cada recomendación debe distinguir:

- **CABE** — puede instalarse razonablemente en la configuración;
- **RULA** — ha sido ejecutada y medida en una configuración comparable;
- **RECOMENDADA** — existe evidencia suficiente para recomendarla;
- **EXPERIMENTAL** — prometedora, pero todavía sin evidencia suficiente.

## Orden de prioridad

Las recomendaciones se ordenarán principalmente por:

1. mejora potencial de UX;
2. compatibilidad con la pila;
3. beneficio/coste;
4. impacto en memoria y rendimiento;
5. prioridad Copyleft dentro del universo Open;
6. madurez y mantenimiento;
7. reproducibilidad y evidencia.

## Instalación

La prospección y el menú de recomendaciones **no instalarán componentes automáticamente**.

El usuario deberá decidir qué recomendación instalar. Cuando sea técnicamente posible, LOAS deberá mostrar los cambios previstos y conservar una ruta de reversión.

## Relación con la evolución de LOAS

El ciclo queda congelado como:

```text
DESCUBRIR
   ↓
PROSPECTAR
   ↓
EVALUAR
   ↓
RECOMENDAR
   ↓
USUARIO DECIDE
   ↓
RULA
   ↓
APRENDER
```

La decisión podrá revisarse en el futuro mediante una modificación explícita de una decisión congelada.
