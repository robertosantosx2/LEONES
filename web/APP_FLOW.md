# LEONES App — flujo guiado

La aplicación web no ejecuta scripts en el navegador. Su función es conducir al usuario y generar el siguiente comando local.

## Flujo

Necesidad → Hardware → Modelo → Inferencia → Evaluación → Informe → Privacidad/Publicación → Estadísticas → mejores recomendaciones.

Cada usuario puede detenerse en cualquier punto. El estado del recorrido se conserva localmente en `localStorage`.

## Manada

La contribución es voluntaria. Los resultados técnicos agregados permiten conocer qué combinaciones funcionan realmente en hardware de consumo y mejorar futuras recomendaciones. La aplicación explica qué datos son útiles y qué categorías no deben publicarse.

## Evidencia

La interfaz distingue entre recomendación provisional y evidencia. Si no existe evidencia suficiente, la recomendación debe considerarse desconocida/provisional y no un hecho.
