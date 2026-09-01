# LEONES App — flujo guiado

La aplicación web **no ejecuta la infraestructura local en el navegador**. Su función es explicar el recorrido, recoger decisiones y conducir al usuario hacia las herramientas locales que correspondan.

## Flujo canónico RC2

```text
Necesidad
   ↓
Hardware real
   ↓
LLMFIT
   ↓
Candidatos
   ↓
Elección humana
   ↓
ODS / Magnitude
   ↓
Stack propuesto
   ↓
Consentimiento de instalación
   ↓
Instalar → Verificar
   ↓
Consentimiento de benchmark
   ↓
Handoff RC1
   ↓
Medir
   ↓
Evidencia
   ↓
Recomendación
```

La elección del usuario y la autorización de operaciones son explícitas. **El consentimiento para instalar no autoriza automáticamente un benchmark.** Son dos decisiones independientes.

## Qué aporta cada capa

- **Hardware real:** establece las capacidades observables del equipo.
- **LLMFIT:** ayuda a acotar candidatos compatibles con el hardware.
- **ODS / Magnitude:** aportan conocimiento especializado sobre despliegue, modelos, inferencia y agentes. LEONES los utiliza como fuentes/decisión de stack; no crea un scoring paralelo que los sustituya.
- **RC1:** recibe la configuración autorizada y mantiene el camino canónico de ejecución y evidencia.
- **Benchmark:** comprueba una tarea concreta y no solo una cifra sintética.
- **Evidencia:** conserva qué se ejecutó, dónde, cuándo y con qué resultado.

## ESTIMATED ≠ MEASURED

Las estimaciones sirven para seleccionar y priorizar. Una estimación de ODS, Magnitude, LLMFIT u otra fuente externa **no es una medición física de LEONES**.

Solo una ejecución real registrada mediante el camino de ejecución/evidencia correspondiente puede producir evidencia física. Los valores desconocidos permanecen desconocidos; no se rellenan por inferencia.

## Manada

La contribución a Manada es voluntaria. Los resultados técnicos agregados pueden servir para conocer qué combinaciones funcionan realmente en hardware de consumo y mejorar futuras recomendaciones. La aplicación debe explicar qué datos son útiles antes de cualquier publicación.

## Principio de producto

La web documenta y conduce. La infraestructura local ejecuta. RC1 mide y produce evidencia. LEONES aprende de los resultados sin confundir recomendaciones provisionales con hechos medidos.
