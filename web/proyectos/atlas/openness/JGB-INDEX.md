# Índice JGB v0.1 — apertura de modelos de IA generativa

## Base documental

Este índice se deriva de la presentación **“Generative AI in your own infrastructure”**, de Jesús M. Gonzalez-Barahona, presentada en el 1st Workshop on Free Software and Open Artificial Intelligence (Fuenlabrada, 6 de julio de 2026). La presentación distingue un espectro de modelos: *Behind-app model*, *Directly accessible model*, *Available weights model*, *Open weight model*, *Open source model* y *Reproducible (libre) model*. fileciteturn7file0L89-L99

## Qué mide

El marco no pretende medir calidad, inteligencia o rendimiento. Evalúa cinco dimensiones de libertad/control:

1. **Access** — hasta qué punto se puede acceder y ejecutar el modelo.
2. **Model control** — hasta qué punto se puede controlar/modificar el modelo.
3. **Data control** — hasta qué punto se controlan prompts y resultados/datos.
4. **Autonomy** — dependencia respecto del proveedor.
5. **Trust** — posibilidad de asegurar que el modelo funciona como se espera.

Estas dimensiones aparecen explícitamente en la presentación y se relacionan con uso, innovación, integración, privacidad, independencia, competencia, seguridad y transparencia. fileciteturn7file0L103-L105 fileciteturn7file0L105-L106

## Clases JGB

| Nivel | Clase | Access | Model control | Data control | Autonomy | Trust |
|---|---|---|---|---|---|---|
| 0 | Behind-app model | App-defined | None | None | None | None |
| 1 | Directly accessible model | API restrictions | Limited | None | None | None |
| 2 | Available weights model | With conditions | With conditions | Complete | With conditions | None |
| 3 | Open weight model | Use as you want | Deep control | Complete | Study restricted | None |
| 4 | Open source model | Use as you want | Deep control | Complete | Detailed study restricted | Partial |
| 5 | Reproducible (libre) model | Use as you want | Deep control | Complete | Complete | Complete |

La tabla de síntesis aparece en la página 32 de la presentación. fileciteturn7file0L151-L153

## Evidencias mínimas

### Available weights

Los pesos están disponibles y normalmente existe software de inferencia/FOSS; puede ejecutarse en infraestructura confiable y suele ser posible hacer fine-tuning. Sin embargo, uso, redistribución o modificación pueden estar condicionados o prohibidos. fileciteturn7file0L119-L123

### Open weight

Permite uso, redistribución y obras derivadas, sin condiciones para el uso; incluye fine-tuning e integración. No exige información sobre el modelo o su entrenamiento, por lo que no proporciona libertad de estudio. fileciteturn7file0L127-L129

### Open source

Añade software open source para entrenamiento, inferencia y una descripción detallada del entrenamiento; la disponibilidad del dataset de entrenamiento no es obligatoria. fileciteturn7file0L131-L135

### Reproducible (libre)

Añade toda la información sobre el modelo y requiere disponibilidad del dataset de entrenamiento. El resultado del marco es control profundo del modelo, control completo de datos, autonomía completa y confianza completa. fileciteturn7file0L139-L143

## Regla de clasificación del Atlas

El Atlas almacenará **cada dimensión por separado** y también la clase JGB derivada. No se debe inferir una clase superior solamente porque un modelo tenga pesos disponibles, sea muy buen modelo o pueda ejecutarse localmente.

La presentación señala expresamente que existen cuestiones abiertas: relación compleja entre datos, recetas, arquitectura, pesos y software; definiciones exactas pendientes para varias categorías; dificultad para determinar la categoría de un modelo; tratamiento de fine-tunes/evoluciones; y necesidad de verificar que las declaraciones sean verdaderas. fileciteturn7file0L153-L154

Por ello, el Atlas debe guardar también **evidencia y confianza**, no solamente la etiqueta.

## Self-hostable no equivale a máxima apertura

La presentación separa el concepto operativo de modelo *self-hostable*. Como mínimo, para ejecutarlo en infraestructura propia se necesita software de inferencia con bibliotecas, parámetros/pesos y metadatos, además de informe técnico; el model card se considera conveniente. Con software de soporte disponible, las categorías incluyen available weights, open weights, open source y reproducible. fileciteturn7file0L155-L159

Esto será una dimensión especialmente útil para el recomendador de LEONES: **JGB apertura/libertad** y **self-hostability/viabilidad técnica** deben seguir siendo conceptos diferentes.

## Relación con el Atlas

```text
MODEL
  ├── JGB class
  ├── access
  ├── model_control
  ├── data_control
  ├── autonomy
  ├── trust
  ├── evidence
  └── confidence
```

JGB debe convivir con la clasificación de apertura existente en el Atlas. No se sustituye una clasificación por otra y ninguna de ellas se convierte automáticamente en un score de calidad.

## Fuente primaria

Jesús M. Gonzalez-Barahona, *Generative AI in your own infrastructure*, seLIA: 1st Workshop on Free Software and Open Artificial Intelligence, Fuenlabrada, Spain, 6 July 2026. La presentación se distribuye bajo Creative Commons Attribution-ShareAlike 4.0. fileciteturn7file0L89-L90 fileciteturn7file0L164-L165
