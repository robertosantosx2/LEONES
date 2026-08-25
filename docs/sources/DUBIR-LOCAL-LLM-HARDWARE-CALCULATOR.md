# Dubir · Local LLM Hardware Calculator

## Identidad
- Fuente primaria: https://dubir.net/tools/local-llm-hardware-calculator/
- Capa: recomendación hardware + workload.
- Estado LEONES: `research-candidate`.

## Qué es
Calculadora que relaciona hardware, modelo, contexto y caso de uso para orientar sobre modelos locales adecuados.

## Qué aporta
Introduce explícitamente el **workload** como variable de selección, evitando reducir el problema a “qué modelo cabe”.

## Evidencia
Sus recomendaciones y cálculos pertenecen a la herramienta externa y deben registrarse con su fecha/metodología.

## Estimación
La selección de modelos y rendimiento esperado son estimaciones externas.

## Medición LEONES
Pendiente. El benchmark real debe medir el workload objetivo, no solo inferencia sintética.

## Valor para LEONES
Refuerza la idea de que el selector debe recibir una intención/tarea: chat, coding, razonamiento, documentos, etc., y después contrastarla con medición funcional.

## Próximo paso
Extraer las variables de workload y comprobar cuáles deben convertirse en campos de `runtime-selection.v1`.