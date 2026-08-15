# Índice JGB — método operativo del Atlas

## Criterio fijado

El Atlas adopta como marco de apertura/libertad el presentado por Jesús M. Gonzalez-Barahona en *Generative AI in your own infrastructure* (seLIA, 6 July 2026).

El marco distingue seis clases:

0. Behind-app model
1. Directly accessible model
2. Available weights model
3. Open weight model
4. Open source model
5. Reproducible (libre) model

Y cinco dimensiones independientes:

- Access
- Model control
- Data control
- Autonomy
- Trust

## Regla de oro

**No se asigna un nivel JGB por el nombre comercial de la licencia, por la etiqueta "open weights" del proveedor, por poder descargar pesos, ni por poder ejecutar el modelo localmente.**

La clasificación requiere evidencia suficiente sobre las dimensiones y los requisitos de la categoría.

En particular, `Open weights` en el Atlas de modelos es una **señal de investigación**, no una clasificación automática JGB=3.

## Estados permitidos

`verified`, `provisional`, `unknown`, `disputed`

La ausencia de evidencia se representa como `unknown`; nunca se convierte silenciosamente en una categoría superior.

## Flujo de verificación

```text
             MODELO DEL ATLAS
                    |
                    v
          ¿hay evidencia primaria?
             /            \
           no              sí
           |                |
        UNKNOWN       extraer evidencias
                            |
             +--------------+--------------+
             |              |              |
          Access          Model          Data
          control         control        control
             |              |              |
             +--------------+--------------+
                            |
                  Autonomy + Trust
                            |
                            v
                   evaluar requisitos
                            |
                            v
                     NIVEL JGB
                            |
                            v
                confidence + evidence
```

## Separación con el recomendador

```text
JGB / LIBERTAD
      |
      +-- Access
      +-- Model control
      +-- Data control
      +-- Autonomy
      +-- Trust

NO ES:
      |
      +-- calidad
      +-- benchmark
      +-- tokens/s
      +-- memoria
      +-- facilidad de instalación

Y TAMPOCO ES SINÓNIMO DE:
      |
      +-- self-hostability
```

Para el recomendador, `JGB` puede ser una **restricción o preferencia del usuario**, mientras que la viabilidad técnica se calcula separadamente a partir de hardware, runtime, formato, cuantización, memoria y carga de trabajo.

## Aplicación inicial al Atlas 2026

Los registros actuales de `models_atlas_2026_base.csv` contienen `openness_status=Open weights` para numerosos modelos, pero muchos aparecen como `candidate — verify metadata` y sin licencia verificada ni `open_weights_verified` confirmado. Por tanto, la primera cola de trabajo se registra como `unknown / needs verification`.

Esto es intencionado: el Atlas debe preferir **no clasificar** antes que fabricar una clasificación JGB.

## Fuentes y evidencia

Cada clasificación verificada deberá conservar:

- fuente primaria
- URL
- fecha de comprobación
- licencia y texto relevante
- disponibilidad de pesos
- software de inferencia
- software/código de entrenamiento cuando sea relevante
- descripción técnica del entrenamiento
- datasets cuando sean relevantes para categorías superiores
- evidencia de derechos de uso, redistribución y obras derivadas
- notas sobre fine-tunes/evoluciones

## Referencia

Jesús M. Gonzalez-Barahona, *Generative AI in your own infrastructure*, seLIA: 1st Workshop on Free Software and Open Artificial Intelligence, Fuenlabrada, Spain, 6 July 2026.
