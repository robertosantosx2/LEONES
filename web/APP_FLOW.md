# LEONES App — flujo guiado RC4

La aplicación web **no ejecuta la infraestructura local en el navegador**. Explica el recorrido y conduce al usuario hacia las herramientas locales correspondientes.

## Flujo canónico

```text
IDIOMA
   ↓
ESTADO DE LA MÁQUINA
   ↓
USER_INTENT[] · obligatorio · múltiple
   ↓
HARDWARE + RESOURCE PREFLIGHT
   ↓
HF + Artificial Analysis
   ↓
LLMFit opcional · catálogo independiente
   ↓
INTERSECCIÓN → hasta 3 ESTIMATED | insufficient
   ↓
ELECCIÓN HUMANA
   ↓
STACK / RUNTIME
   ↓
CONSENTIMIENTO Y OPERACIONES EXPLÍCITAS
   ↓
VERIFICACIÓN FÍSICA
   ↓
AUTORIZACIÓN DE EJECUCIÓN / MEDICIÓN
   ↓
MEASURED + EVIDENCIA
```

La TUI es presentación. No convierte una recomendación en ejecución.

## Qué aporta cada capa

- **Estado de la máquina:** hardware, recursos y componentes IA observados en el host.
- **USER_INTENT[]:** declara para qué se quiere usar la IA; no puede estar vacío.
- **Hugging Face + Artificial Analysis:** evidencia externa y procedencia.
- **LLMFit / FitLLM:** preselector opcional desde su catálogo propio.
- **Intersección:** solo candidatos con identidad respaldada por ambas superficies llegan a la recomendación.
- **Elección humana:** selecciona modelo/configuración y posteriormente stack/runtime.
- **Runtime físico:** comprueba qué está realmente disponible en Ubuntu.
- **Medición:** solo una ejecución protocolizada produce `MEASURED`.

## ESTIMATED ≠ MEASURED

Las estimaciones sirven para seleccionar y priorizar. Una estimación de LLMFit, Hugging Face, Artificial Analysis u otra fuente externa **no es una medición física de LEONES**.

Una preflight tampoco es una instalación verificada. Una instalación verificada tampoco es un benchmark ejecutado.

## Consentimientos

Las decisiones se mantienen separadas:

```text
recomendar ≠ elegir ≠ instalar ≠ verificar ≠ autorizar ejecución ≠ medir
```

No se descarga ni ejecuta una pila por el mero hecho de recomendarla.

## Manada

La contribución a Manada es voluntaria. Los resultados técnicos agregados pueden ampliar la evidencia sobre hardware real, conservando procedencia y consentimiento.

## Principio de producto

La web documenta y conduce. La infraestructura local ejecuta. LEONES aprende de resultados medidos sin confundir recomendaciones provisionales con hechos físicos.