# LEONES Web — referencia obligatoria

## Objetivo

La web de LEONES prioriza, en este orden:

1. simplicidad técnica;
2. legibilidad;
3. funcionalidad;
4. accesibilidad básica;
5. mantenimiento sencillo.

La estética no debe introducir complejidad que no aporte una función clara.

## Estado visible

La web debe reflejar el estado canónico real del repositorio:

- **JALÓN 1:** 🟢 cerrado.
- **JALÓN 2:** 🟢 cerrado, con ejecución física y evidencia reproducible.
- **JALÓN 3:** 🟢 cerrado operativamente, con contrato `runtime-benchmark-evidence.v1.1`.
- **RC1:** 🟢 validado mediante ejecución efectiva end-to-end.
- **ODS / Magnitude:** 🟢 contrato de decisión fijado, sin scoring paralelo.
- **RC2:** 🟡 preparado para beta, con instalación, verificación, consentimiento de benchmark y handoff al camino canónico de RC1.

La página pública de referencia para este estado es [`estado.html`](estado.html).

## RC1

La web no debe presentar RC1 como una simple validación de código. El hito demostrado es físico:

```text
selección → gate → execution autorizado
         → runtime real → modelo real → benchmark
         → medición → evidencia reproducible
```

Las cifras históricas de ejecuciones concretas deben conservarse en su documentación/evidencia correspondiente y no reutilizarse como mediciones de otro equipo, runtime, modelo o configuración. La web no debe convertir una ejecución histórica en un benchmark universal.

## RC2

RC2 organiza el paso desde la selección hasta la ejecución de beta:

```text
necesidad → hardware real → candidatos → elección
          → ODS / Magnitude → stack
          → consentimiento instalación
          → instalar → verificar
          → consentimiento benchmark
          → handoff RC1 → medir → evidenciar
```

Los dos consentimientos son independientes. La instalación no implica autorización para ejecutar un benchmark.

## Arquitectura

```text
HTML semántico
    ↓
CSS compartido
    ↓
JavaScript solo cuando aporta comportamiento
```

La navegación es transversal. El contenido de cada página debe permanecer separado de la infraestructura interna.

## Regla para CSS específico

Antes de crear CSS específico para una página deben agotarse estas alternativas:

1. HTML semántico adecuado.
2. Elementos o clases existentes.
3. Extensión pequeña y reutilizable de `assets/css/site.css`.
4. Solo si existe una excepción conceptual real, CSS específico mínimo y documentado.

## HTML

- `<!doctype html>` y `lang="es"`.
- `charset` y `viewport`.
- título descriptivo y único.
- `meta description` cuando corresponda.
- encabezados en orden lógico.
- `header`, `main`, `section`, `article` y `footer` cuando aporten semántica.
- enlaces reales para navegación.
- código indentado y legible; nunca comprimido en una línea.

## CSS

`site.css` contiene el sistema visual común. `navigation.css` contiene exclusivamente la navegación. No duplicar reglas entre páginas.

## JavaScript

JavaScript resuelve comportamiento, no problemas que HTML o CSS puedan resolver de forma más simple. Los scripts deben ser externos y cargarse con `defer` cuando sea posible.

## Separación de infraestructura

La web documenta, explica y presenta LEONES. No debe convertirse en un paquete que el usuario tenga que descargar para ejecutar la infraestructura.

Los scripts locales son herramientas autónomas. El usuario descarga solo las herramientas necesarias para realizar pruebas en su propio equipo.

## Evidencia y lenguaje

- **ESTIMATED** no equivale a **MEASURED**.
- Una recomendación no equivale a evidencia.
- Una preflight no equivale a una instalación verificada.
- Una instalación verificada no equivale a un benchmark ejecutado.
- Un benchmark ejecutado debe conservar su procedencia y configuración.

## Criterio de terminado

Una página está terminada cuando una persona puede abrirla, entender para qué sirve, navegar al siguiente paso y revisar su contenido sin conocer la arquitectura interna.

## Regla de producto

La web debe reflejar el repositorio real. No anunciar capacidades como cerradas si no existe evidencia correspondiente en el proyecto. Cuando haya una medición física nueva, debe enlazarse a su evidencia y conservar su carácter local y reproducible.
