# Índice JGB v0.1 — apertura de modelos de IA generativa

## Base documental

Este índice se deriva de la presentación **“Generative AI in your own infrastructure”**, de Jesús M. Gonzalez-Barahona, presentada en el 1st Workshop on Free Software and Open Artificial Intelligence (Fuenlabrada, 6 de julio de 2026). La presentación distingue un espectro de modelos: *Behind-app model*, *Directly accessible model*, *Available weights model*, *Open weight model*, *Open source model* y *Reproducible (libre) model*.

## Qué mide

El marco no pretende medir calidad, inteligencia o rendimiento. Evalúa cinco dimensiones de libertad/control:

1. **Access** — hasta qué punto se puede acceder y ejecutar el modelo.
2. **Model control** — hasta qué punto se puede controlar/modificar el modelo.
3. **Data control** — hasta qué punto se controlan prompts y resultados/datos.
4. **Autonomy** — dependencia respecto del proveedor.
5. **Trust** — posibilidad de asegurar que el modelo funciona como se espera.

## Clases JGB

| Nivel | Clase | Access | Model control | Data control | Autonomy | Trust |
|---|---|---|---|---|---|---|
| 0 | Behind-app model | App-defined | None | None | None | None |
| 1 | Directly accessible model | API restrictions | Limited | None | None | None |
| 2 | Available weights model | With conditions | With conditions | Complete | With conditions | None |
| 3 | Open weight model | Use as you want | Deep control | Complete | Study restricted | None |
| 4 | Open source model | Use as you want | Deep control | Complete | Detailed study restricted | Partial |
| 5 | Reproducible (libre) model | Use as you want | Deep control | Complete | Complete | Complete |

## Evidencias mínimas

### Available weights

Los pesos están disponibles y normalmente existe software de inferencia/FOSS; puede ejecutarse en infraestructura confiable y suele ser posible hacer fine-tuning. Sin embargo, uso, redistribución o modificación pueden estar condicionados o prohibidos.

### Open weight

Permite uso, redistribución y obras derivadas, sin condiciones para el uso; incluye fine-tuning e integración. No exige información sobre el modelo o su entrenamiento, por lo que no proporciona libertad de estudio.

### Open source

Añade software open source para entrenamiento, inferencia y una descripción detallada del entrenamiento; la disponibilidad del dataset de entrenamiento no es obligatoria.

### Reproducible (libre)

Añade toda la información sobre el modelo y requiere disponibilidad del dataset de entrenamiento. El resultado del marco es control profundo del modelo, control completo de datos, autonomía completa y confianza completa.

## Regla de clasificación del Atlas

El Atlas almacenará **cada dimensión por separado** y también la clase JGB derivada. No se debe inferir una clase superior solamente porque un modelo tenga pesos disponibles, sea muy buen modelo o pueda ejecutarse localmente.

La clasificación debe conservar siempre la evidencia que la sustenta y su estado de confianza. Una dimensión sin evidencia suficiente permanece `unknown`; una hipótesis no se promociona automáticamente a clasificación definitiva.

## Activación humana por correo

La **activación definitiva de una clase JGB es humana y restringida**. No se realiza mediante un formulario web ni mediante una promoción automática del pipeline.

El mecanismo oficial se denomina:

> **Formulario de validación humana de Índice JGB**

Es un formulario **vía correo electrónico** dirigido a:

`manadaleones.ia@gmail.com`

La solicitud debe contener como mínimo:

- identificador del modelo y variante;
- clase JGB propuesta;
- las cinco dimensiones evaluadas;
- evidencia y fuentes utilizadas;
- estado de confianza;
- fecha de evaluación;
- persona o identidad que solicita la validación.

La respuesta válida de activación debe ser **exactamente una** de estas seis expresiones:

```text
OK LEONES CLASE0
OK LEONES CLASE1
OK LEONES CLASE2
OK LEONES CLASE3
OK LEONES CLASE4
OK LEONES CLASE5
```

La respuesta humana es la **autorización de activación**, no la evidencia primaria del modelo. La evidencia debe existir y permanecer archivada independientemente.

Si la clase propuesta y la clase autorizada son distintas, prevalece exclusivamente la clase indicada en la respuesta humana. Una respuesta distinta de las seis expresiones anteriores no activa ninguna clase.

El registro debe conservar por separado:

```text
EVIDENCIA → CLASE PROPUESTA → VALIDACIÓN HUMANA → CLASE ACTIVADA
```

## Self-hostable no equivale a máxima apertura

La presentación separa el concepto operativo de modelo *self-hostable*. Como mínimo, para ejecutarlo en infraestructura propia se necesita software de inferencia con bibliotecas, parámetros/pesos y metadatos, además de informe técnico; el model card se considera conveniente. Con software de soporte disponible, las categorías incluyen available weights, open weights, open source y reproducible.

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
  ├── confidence
  └── human_validation
       ├── requested_class
       ├── response
       ├── validated_class
       └── validation_date
```

JGB debe convivir con la clasificación de apertura existente en el Atlas. No se sustituye una clasificación por otra y ninguna de ellas se convierte automáticamente en un score de calidad.

## Fuente primaria

Jesús M. Gonzalez-Barahona, *Generative AI in your own infrastructure*, seLIA: 1st Workshop on Free Software and Open Artificial Intelligence, Fuenlabrada, Spain, 6 July 2026. La presentación se distribuye bajo Creative Commons Attribution-ShareAlike 4.0.
