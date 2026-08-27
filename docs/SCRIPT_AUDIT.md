# Auditoría de scripts

## Criterio

Se aplica `docs/SCRIPT_STYLE_CONTRACT.md`: un script debe ser pequeño, tener una responsabilidad clara y poder entenderse sin conocer previamente el proyecto.

## Primera limpieza aplicada

- Se fijó el contrato de simplicidad y documentación.
- Se añadió `scripts/check_script_quality.py` como auditor incremental.
- Se añadieron pruebas del auditor.
- Se simplificó y documentó `scripts/model_selector.py`, que era uno de los scripts más comprimidos y difíciles de leer.
- Se mantiene la compatibilidad funcional: la selección sigue exigiendo el runtime antes de puntuar modelos y conserva la evidencia de LLMFit, memoria, contexto y parámetros.

## Regla para el resto

No se hará una reescritura masiva. Cada script se limpia cuando se toca, siguiendo este orden:

1. eliminar instrucciones comprimidas en una misma línea;
2. separar imports y constantes;
3. dar nombres descriptivos;
4. documentar entrada, salida y límites;
5. explicar decisiones no obvias;
6. eliminar duplicación demostrada;
7. conservar las pruebas antes de aceptar el cambio.

Los scripts históricos pueden seguir existiendo durante la migración. No se consideran incumplimiento nuevo mientras no se modifiquen sin aplicar este contrato.
