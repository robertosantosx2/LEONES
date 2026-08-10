# LOAS — Nivel de prospección

## Objetivo

Además del descubrimiento diario de proyectos Open/Copyleft, LOAS tendrá un nivel de **prospección semanal** dedicado a buscar piezas que mejoren las **skills, funciones o características de los harnesses** de la pila.

El objetivo no es sustituir automáticamente componentes. Es descubrir mejoras potenciales y convertirlas en recomendaciones que el usuario pueda instalar cuando sean compatibles con su configuración.

## Diferencia entre descubrimiento y prospección

### Descubrimiento diario

Pregunta:

> ¿Qué proyectos Open nuevos han aparecido?

Prioridad: identificar el universo Open y dar prioridad a Copyleft.

### Prospección semanal

Pregunta:

> ¿Qué piezas nuevas pueden mejorar las capacidades del harness que ya utiliza el usuario?

Prioridad: **utilidad para una pila concreta**.

## Qué buscar

La prospección debe buscar especialmente:

- nuevas skills;
- nuevos tool adapters;
- herramientas de navegación y búsqueda;
- integración con Git/GitHub;
- ejecución de código;
- manejo de archivos;
- memoria y recuperación de contexto;
- planificación y ejecución multietapa;
- subagentes;
- observabilidad;
- evaluación;
- recuperación ante errores;
- seguridad y sandboxing;
- automatización;
- conectores;
- nuevas capacidades de coding;
- mejoras de UX del harness;
- componentes que permitan hacer más con el mismo hardware.

## Menú de recomendaciones

Los candidatos relevantes deben aparecer en un menú de recomendaciones de LOAS.

Una recomendación debe responder como mínimo:

1. **Qué mejora.**
2. **Qué harness afecta.**
3. **Qué versiones son compatibles.**
4. **Qué licencia tiene.**
5. **Si es Copyleft.**
6. **Qué requisitos de hardware añade.**
7. **Qué dependencias introduce.**
8. **Qué mejora de UX se espera.**
9. **Cómo instalarlo.**
10. **Cómo desinstalarlo/revertirlo.**
11. **Qué evidencia existe.**

## Recomendaciones condicionadas a la pila

LOAS no debe mostrar una lista genérica de novedades como si todas fueran aplicables.

Debe cruzar cada candidato con la configuración detectada por el usuario:

```text
hardware
   +
OS
   +
harness
   +
modelo
   +
backend
   +
versión
   ↓
compatibilidad
   ↓
recomendación
```

Ejemplo conceptual:

```text
✓ Recomendado
   Esta skill es compatible con Buddy 1.x
   y tu configuración actual.

⚠ Compatible con cambios
   Requiere Python >= X / Y GB adicionales.

✗ No recomendado
   No CABE en tu perfil H1.
```

## Prioridad de recomendaciones

Las recomendaciones deben ordenarse por:

1. mejora potencial de UX;
2. compatibilidad con la pila actual;
3. beneficio/coste;
4. impacto sobre memoria y rendimiento;
5. licencia, dando prioridad a Copyleft;
6. madurez y mantenimiento;
7. reproducibilidad/evidencia.

## Regla CABE + RULA

Una recomendación no debe presentarse como mejora garantizada.

Debe distinguirse entre:

- **CABE:** puede instalarse razonablemente en la configuración;
- **RULA:** ha sido ejecutada y medida en una configuración comparable;
- **RECOMENDADA:** LOAS tiene evidencia suficiente para recomendarla;
- **EXPERIMENTAL:** prometedora pero todavía sin evidencia suficiente.

## Instalación bajo control del usuario

La prospección **no instala automáticamente** componentes.

El usuario decide qué recomendación instalar.

Antes de instalar, LOAS debe mostrar los cambios previstos y permitir conservar la configuración anterior o revertirlos cuando sea técnicamente posible.

## Relación con el Score

La prospección alimentará progresivamente el **Libre-Open Agentic Stack Score** y, cuando exista suficiente evidencia, permitirá descubrir combinaciones de componentes superiores a la pila de referencia.

La métrica no debe premiar una herramienta únicamente por tener muchas funciones. Debe valorar si esas funciones producen una mejora real y reproducible de la experiencia agentic en hardware de consumo.

## Resultado esperado

LOAS evoluciona así:

```text
DESCUBRE
   ↓
PROSPECTA
   ↓
EVALÚA
   ↓
RECOMIENDA
   ↓
USUARIO DECIDE
   ↓
RULA
   ↓
APRENDE
```

El nivel de prospección es, por tanto, el puente entre el ecosistema que aparece cada semana y la evolución práctica de la pila de cada usuario.
