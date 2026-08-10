# LOAS — Política de descubrimiento Open/Copyleft

## Principio

LOAS debe descubrir **todas las piezas potencialmente relevantes que sean Open Source según criterios de la OSI**, no únicamente las que utilicen Copyleft.

La licencia es un filtro de descubrimiento y una dimensión de evaluación, no un filtro que haga desaparecer el resto del ecosistema Open.

## Prioridad LOAS

Una vez descubiertos los proyectos Open, LOAS los prioriza así:

1. **Copyleft**, especialmente GPL/AGPL/LGPL cuando sean compatibles con el componente y el uso previsto.
2. **Otros proyectos Open Source compatibles con criterios OSI**.
3. Proyectos no Open: quedan fuera de la pila Libre-Open.

La prioridad Copyleft no significa que un proyecto permisivo quede descartado. Un proyecto Apache, MIT, BSD u otra licencia OSI-compatible puede ser técnicamente superior y debe poder aparecer como candidato, compararse y, si aporta valor, formar parte de una configuración LOAS.

## Evaluación posterior

Descubrimiento no equivale a incorporación.

Cada candidato debe evaluarse por:

- licencia y estado de la licencia;
- relevancia para la pila agentic;
- CABE en hardware objetivo;
- rendimiento;
- memoria;
- estabilidad;
- mantenimiento y actividad;
- reproducibilidad;
- seguridad;
- compatibilidad con el resto de la pila;
- mejora de UX.

## Regla fundamental

**LOAS descubre Open, prioriza Copyleft y selecciona por evidencia.**

Esto evita dos errores opuestos:

- perder proyectos Open excelentes porque no son Copyleft;
- introducir un proyecto solo porque tiene una licencia favorable sin demostrar que mejora LOAS.

## Ciclo diario

El descubrimiento se ejecuta diariamente mediante GitHub Actions. Los candidatos se registran para posterior evaluación; el descubrimiento automático no debe modificar por sí mismo la pila candidata congelada.
